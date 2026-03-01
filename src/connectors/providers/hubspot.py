"""HubSpot connector — OAuth2 + Webhooks + Polling.

Captures CRM contacts, deals, companies, and engagement events.
"""

import hashlib
import logging
from datetime import datetime
from typing import Any, cast

import httpx

from src.connectors.oauth import OAuthConfig
from src.connectors.providers.base import BaseProvider, MemoryItem

logger = logging.getLogger("membread.providers.hubspot")

HUBSPOT_API = "https://api.hubapi.com"


class HubSpotProvider(BaseProvider):
    provider_id = "hubspot"
    provider_name = "HubSpot"
    auth_method = "oauth2"
    poll_interval_seconds = 300

    supported_webhook_events = [
        "contact.creation",
        "contact.propertyChange",
        "deal.creation",
        "deal.propertyChange",
        "company.creation",
        "company.propertyChange",
    ]

    def get_oauth_config(self, client_id: str = "", client_secret: str = "") -> OAuthConfig:
        return OAuthConfig(
            provider_id=self.provider_id,
            authorize_url="https://app.hubspot.com/oauth/authorize",
            token_url="https://api.hubapi.com/oauth/v1/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=[
                "crm.objects.contacts.read",
                "crm.objects.deals.read",
                "crm.objects.companies.read",
            ],
            token_endpoint_auth="client_secret_post",
            revoke_url="https://api.hubapi.com/oauth/v1/refresh-tokens",
        )

    async def poll(
        self,
        access_token: str | None = None,
        api_key: str | None = None,
        cursor: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> tuple[list[MemoryItem], str | None]:
        items: list[MemoryItem] = []
        after = cursor or ""
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

        async with httpx.AsyncClient(timeout=30) as client:
            # Poll recently modified contacts
            params: dict[str, Any] = {"limit": 50, "sorts": ["-hs_lastmodifieddate"]}
            if after:
                params["after"] = after

            resp = await client.post(
                f"{HUBSPOT_API}/crm/v3/objects/contacts/search",
                json={
                    "filterGroups": [],
                    "sorts": [{"propertyName": "hs_lastmodifieddate", "direction": "DESCENDING"}],
                    "limit": 50,
                    **({"after": after} if after else {}),
                },
                headers=headers,
            )
            if resp.status_code == 200:
                data = resp.json()
                for contact in data.get("results", []):
                    props = contact.get("properties", {})
                    name = f"{props.get('firstname', '')} {props.get('lastname', '')}".strip()
                    email = props.get("email", "")
                    company = props.get("company", "")
                    text = f"Contact: {name}"
                    if email:
                        text += f" ({email})"
                    if company:
                        text += f" at {company}"
                    items.append(self._make_memory(
                        text=text,
                        source_id=f"hubspot-contact-{contact['id']}",
                        entity_type="contact",
                        metadata={
                            "hubspot_id": contact["id"],
                            "email": email,
                            "company": company,
                            "lifecycle_stage": props.get("lifecyclestage", ""),
                        },
                        timestamp=props.get("hs_lastmodifieddate"),
                    ))
                new_cursor = data.get("paging", {}).get("next", {}).get("after")
            else:
                new_cursor = cursor

            # Poll recently modified deals
            resp = await client.post(
                f"{HUBSPOT_API}/crm/v3/objects/deals/search",
                json={
                    "filterGroups": [],
                    "sorts": [{"propertyName": "hs_lastmodifieddate", "direction": "DESCENDING"}],
                    "limit": 50,
                },
                headers=headers,
            )
            if resp.status_code == 200:
                data = resp.json()
                for deal in data.get("results", []):
                    props = deal.get("properties", {})
                    text = f"Deal: {props.get('dealname', 'Untitled')}"
                    stage = props.get("dealstage", "")
                    amount = props.get("amount", "")
                    if stage:
                        text += f" — Stage: {stage}"
                    if amount:
                        text += f" — ${amount}"
                    items.append(self._make_memory(
                        text=text,
                        source_id=f"hubspot-deal-{deal['id']}",
                        entity_type="deal",
                        metadata={
                            "hubspot_id": deal["id"],
                            "stage": stage,
                            "amount": amount,
                            "pipeline": props.get("pipeline", ""),
                            "close_date": props.get("closedate", ""),
                        },
                        timestamp=props.get("hs_lastmodifieddate"),
                    ))

        return items, new_cursor

    async def register_webhook(
        self,
        access_token: str,
        webhook_url: str,
        events: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """HubSpot uses app-level webhooks configured in developer portal.
        We register a subscription via API.
        """
        async with httpx.AsyncClient(timeout=30) as client:
            # Get app ID from token info
            resp = await client.get(
                f"{HUBSPOT_API}/oauth/v1/access-tokens/{access_token}",
            )
            if resp.status_code != 200:
                logger.error("Failed to get HubSpot token info")
                return None
            app_id = resp.json().get("app_id")
            if not app_id:
                return None

            # Update webhook target URL
            resp = await client.put(
                f"{HUBSPOT_API}/webhooks/v3/{app_id}/settings",
                json={
                    "targetUrl": webhook_url,
                    "throttling": {
                        "maxConcurrentRequests": 10,
                        "period": "SECONDLY",
                    },
                },
                headers={"Authorization": f"Bearer {access_token}"},
            )

            # Create subscriptions for each event
            for event in (events or self.supported_webhook_events):
                _object_type, _property_name = event.split(".")
                await client.post(
                    f"{HUBSPOT_API}/webhooks/v3/{app_id}/subscriptions",
                    json={
                        "eventType": event,
                        "active": True,
                    },
                    headers={"Authorization": f"Bearer {access_token}"},
                )

            return {"webhook_id": str(app_id), "events": events or self.supported_webhook_events}

    async def unregister_webhook(self, access_token: str, webhook_id: str) -> bool:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.delete(
                f"{HUBSPOT_API}/webhooks/v3/{webhook_id}/settings",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            return resp.status_code in (200, 204)

    def verify_webhook(self, headers: dict[str, Any], body: bytes, secret: str) -> bool:
        signature = headers.get("x-hubspot-signature-v3", "")
        if not signature:
            return True  # No signature header = dev mode
        expected = hashlib.sha256(f"{secret}{body.decode()}".encode()).hexdigest()
        return signature == expected

    async def transform_webhook(
        self,
        payload: dict[str, Any],
        headers: dict[str, Any] | None = None,
    ) -> list[MemoryItem]:
        items: list[MemoryItem] = []
        # HubSpot sends webhook payloads as a JSON array
        raw: Any = payload
        event_list = cast(list[dict[str, Any]], raw if isinstance(raw, list) else [raw])
        for event in event_list:
            event_type = event.get("subscriptionType", "")
            object_id = event.get("objectId", "")
            property_name = event.get("propertyName", "")
            property_value = event.get("propertyValue", "")

            text = f"HubSpot {event_type}: Object {object_id}"
            if property_name:
                text += f" — {property_name} changed to '{property_value}'"

            items.append(self._make_memory(
                text=text,
                source_id=f"hubspot-webhook-{object_id}-{event.get('eventId', '')}",
                entity_type="crm_event",
                metadata={
                    "event_type": event_type,
                    "object_id": str(object_id),
                    "property_name": property_name,
                    "property_value": property_value,
                    "portal_id": str(event.get("portalId", "")),
                },
                timestamp=datetime.fromtimestamp(
                    event.get("occurredAt", 0) / 1000
                ).isoformat() if event.get("occurredAt") else None,
            ))
        return items
