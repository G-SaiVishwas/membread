"""PagerDuty connector — OAuth2 + Webhooks + Polling.

Captures incidents, escalations, and resolution events.
"""

import hashlib
import hmac
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from src.connectors.oauth import OAuthConfig
from src.connectors.providers.base import BaseProvider, MemoryItem  # noqa: F401

logger = logging.getLogger("membread.providers.pagerduty")

PD_API = "https://api.pagerduty.com"


class PagerDutyProvider(BaseProvider):
    provider_id = "pagerduty"
    provider_name = "PagerDuty"
    auth_method = "oauth2"
    poll_interval_seconds = 120

    supported_webhook_events = [
        "incident.triggered",
        "incident.acknowledged",
        "incident.resolved",
        "incident.escalated",
    ]

    def get_oauth_config(self, client_id: str = "", client_secret: str = "") -> OAuthConfig:
        return OAuthConfig(
            provider_id=self.provider_id,
            authorize_url="https://identity.pagerduty.com/oauth/authorize",
            token_url="https://identity.pagerduty.com/oauth/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=["read", "write"],
            use_pkce=True,
            token_endpoint_auth="client_secret_post",
            revoke_url="https://identity.pagerduty.com/oauth/revoke",
        )

    async def poll(
        self,
        access_token: str | None = None,
        api_key: str | None = None,
        cursor: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> tuple[list[MemoryItem], str | None]:
        items: list[MemoryItem] = []
        token = access_token or api_key
        since = cursor or (datetime.now(UTC) - timedelta(hours=2)).isoformat()
        headers = {
            "Authorization": f"Bearer {token}" if access_token else f"Token token={api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            # Recent incidents
            resp = await client.get(
                f"{PD_API}/incidents",
                params={
                    "since": since,
                    "sort_by": "created_at:desc",
                    "limit": 50,
                },
                headers=headers,
            )
            if resp.status_code == 200:
                for inc in resp.json().get("incidents", []):
                    urgency = inc.get("urgency", "")
                    status = inc.get("status", "")
                    title = inc.get("title", "No title")
                    service = inc.get("service", {}).get("summary", "")

                    text = f"Incident [{urgency.upper()}]: {title} — {status}"
                    if service:
                        text += f" (Service: {service})"

                    items.append(self._make_memory(
                        text=text,
                        source_id=f"pd-incident-{inc['id']}",
                        entity_type="incident",
                        metadata={
                            "pd_id": inc["id"],
                            "incident_number": inc.get("incident_number"),
                            "urgency": urgency,
                            "status": status,
                            "service": service,
                            "escalation_policy": (
                                inc.get("escalation_policy", {})
                                .get("summary", "")
                            ),
                            "assignments": [
                                a.get("assignee", {}).get("summary", "")
                                for a in inc.get("assignments", [])
                            ],
                        },
                        timestamp=inc.get("created_at"),
                    ))

            # Recent log entries for context
            resp = await client.get(
                f"{PD_API}/log_entries",
                params={"since": since, "limit": 50, "is_overview": True},
                headers=headers,
            )
            if resp.status_code == 200:
                for entry in resp.json().get("log_entries", []):
                    entry_type = entry.get("type", "")
                    if entry_type in (
                        "acknowledge_log_entry",
                        "resolve_log_entry",
                        "escalate_log_entry",
                    ):
                        incident = entry.get("incident", {})
                        agent = entry.get("agent", {}).get(
                            "summary", "System",
                        )
                        text = (
                            f"PD {entry_type.replace('_log_entry', '')}: "
                            f"{incident.get('summary', '')} by {agent}"
                        )
                        items.append(self._make_memory(
                            text=text,
                            source_id=f"pd-log-{entry['id']}",
                            entity_type="incident_action",
                            metadata={
                                "action": entry_type,
                                "incident_id": incident.get("id", ""),
                                "agent": agent,
                            },
                            timestamp=entry.get("created_at"),
                        ))

        new_cursor = datetime.now(UTC).isoformat()
        return items, new_cursor

    async def register_webhook(
        self,
        access_token: str,
        webhook_url: str,
        events: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Register PagerDuty webhook v3 subscription."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{PD_API}/webhook_subscriptions",
                json={
                    "webhook_subscription": {
                        "type": "webhook_subscription",
                        "delivery_method": {
                            "type": "http_delivery_method",
                            "url": webhook_url,
                        },
                        "events": events or self.supported_webhook_events,
                        "filter": {"type": "account_reference"},
                    }
                },
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code in (200, 201):
                data = resp.json().get("webhook_subscription", {})
                return {
                    "webhook_id": data.get("id", ""),
                    "events": events,
                    "secret": data.get("delivery_method", {}).get("secret", ""),
                }
            logger.error("PagerDuty webhook registration failed: %s", resp.text[:200])
            return None

    async def unregister_webhook(self, access_token: str, webhook_id: str) -> bool:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.delete(
                f"{PD_API}/webhook_subscriptions/{webhook_id}",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            return resp.status_code in (200, 204)

    def verify_webhook(self, headers: dict[str, Any], body: bytes, secret: str) -> bool:
        signatures = headers.get("x-pagerduty-signature", "")
        if not signatures or not secret:
            return True
        for sig in signatures.split(","):
            sig = sig.strip()
            if sig.startswith("v1="):
                expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
                if hmac.compare_digest(sig[3:], expected):
                    return True
        return False

    async def transform_webhook(
        self,
        payload: dict[str, Any],
        headers: dict[str, Any] | None = None,
    ) -> list[MemoryItem]:
        items: list[MemoryItem] = []
        event = payload.get("event", {})
        event_type = event.get("event_type", "")
        data = event.get("data", {})

        title = data.get("title", data.get("summary", "Incident"))
        status = data.get("status", "")
        urgency = data.get("urgency", "")
        service = data.get("service", {}).get("summary", "")

        text = f"PagerDuty {event_type}: {title}"
        if status:
            text += f" [{status}]"
        if service:
            text += f" (Service: {service})"

        items.append(self._make_memory(
            text=text,
            source_id=f"pd-webhook-{data.get('id', event.get('id', ''))}",
            entity_type="incident_event",
            metadata={
                "event_type": event_type,
                "incident_id": data.get("id", ""),
                "status": status,
                "urgency": urgency,
                "service": service,
            },
        ))
        return items
