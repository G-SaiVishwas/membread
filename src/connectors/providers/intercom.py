"""Intercom connector — OAuth2 + Webhooks + Polling.

Captures customer conversations, contacts, and support events.
"""

import hashlib
import hmac
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from src.connectors.oauth import OAuthConfig
from src.connectors.providers.base import BaseProvider, MemoryItem

logger = logging.getLogger("membread.providers.intercom")

INTERCOM_API = "https://api.intercom.io"


class IntercomProvider(BaseProvider):
    provider_id = "intercom"
    provider_name = "Intercom"
    auth_method = "oauth2"
    poll_interval_seconds = 300

    supported_webhook_events = [
        "conversation.created",
        "conversation.closed",
        "conversation.admin.replied",
        "conversation.user.replied",
        "contact.created",
        "contact.updated",
    ]

    def get_oauth_config(self, client_id: str = "", client_secret: str = "") -> OAuthConfig:
        return OAuthConfig(
            provider_id=self.provider_id,
            authorize_url="https://app.intercom.com/oauth",
            token_url="https://api.intercom.io/auth/eagle/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=[],
            token_endpoint_auth="client_secret_post",
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
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Intercom-Version": "2.10",
        }

        # Cursor is a unix timestamp
        since_ts = int(cursor) if cursor else int(
            (datetime.now(UTC) - timedelta(hours=1)).timestamp()
        )

        async with httpx.AsyncClient(timeout=30) as client:
            # Poll recent conversations
            resp = await client.post(
                f"{INTERCOM_API}/conversations/search",
                json={
                    "query": {
                        "field": "updated_at",
                        "operator": ">",
                        "value": since_ts,
                    },
                    "pagination": {"per_page": 50},
                },
                headers=headers,
            )
            if resp.status_code == 200:
                data = resp.json()
                for conv in data.get("conversations", []):
                    source = conv.get("source", {})
                    subject = source.get("subject", "No subject")
                    body = source.get("body", "")[:200]
                    state = conv.get("state", "")
                    text = f"Conversation: {subject} — {state}"
                    if body:
                        text += f"\n{body}"

                    items.append(self._make_memory(
                        text=text,
                        source_id=f"intercom-conv-{conv['id']}",
                        entity_type="conversation",
                        metadata={
                            "intercom_id": conv["id"],
                            "state": state,
                            "priority": conv.get("priority", ""),
                            "assignee_type": conv.get("assignee", {}).get("type", ""),
                            "tags": [
                                t.get("name", "")
                                for t in conv.get("tags", {}).get("tags", [])
                            ],
                            "statistics": conv.get("statistics", {}),
                        },
                        timestamp=datetime.fromtimestamp(
                            conv.get("updated_at", 0),
                        ).isoformat(),
                    ))

            # Poll contacts
            resp = await client.post(
                f"{INTERCOM_API}/contacts/search",
                json={
                    "query": {
                        "field": "updated_at",
                        "operator": ">",
                        "value": since_ts,
                    },
                    "pagination": {"per_page": 50},
                },
                headers=headers,
            )
            if resp.status_code == 200:
                data = resp.json()
                for contact in data.get("data", []):
                    name = contact.get("name", "Unknown")
                    email = contact.get("email", "")
                    role = contact.get("role", "")
                    text = f"Contact: {name}"
                    if email:
                        text += f" ({email})"
                    text += f" — Role: {role}"

                    items.append(self._make_memory(
                        text=text,
                        source_id=f"intercom-contact-{contact['id']}",
                        entity_type="contact",
                        metadata={
                            "intercom_id": contact["id"],
                            "email": email,
                            "role": role,
                            "custom_attributes": contact.get("custom_attributes", {}),
                        },
                        timestamp=datetime.fromtimestamp(contact.get("updated_at", 0)).isoformat(),
                    ))

        new_cursor = str(int(datetime.now(UTC).timestamp()))
        return items, new_cursor

    async def register_webhook(
        self,
        access_token: str,
        webhook_url: str,
        events: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Register Intercom webhook subscription."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{INTERCOM_API}/subscriptions",
                json={
                    "service_type": "web",
                    "url": webhook_url,
                    "topics": events or self.supported_webhook_events,
                },
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                    "Intercom-Version": "2.10",
                },
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                return {"webhook_id": data.get("id", ""), "events": events}
            logger.error("Intercom webhook registration failed: %s", resp.text[:200])
            return None

    async def unregister_webhook(self, access_token: str, webhook_id: str) -> bool:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.delete(
                f"{INTERCOM_API}/subscriptions/{webhook_id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Intercom-Version": "2.10",
                },
            )
            return resp.status_code in (200, 204)

    def verify_webhook(self, headers: dict[str, Any], body: bytes, secret: str) -> bool:
        sig = headers.get("x-hub-signature", "")
        if not sig:
            return True
        return hmac.compare_digest(
            "sha1=" + hmac.new(secret.encode(), body, hashlib.sha1).hexdigest(),
            sig,
        )

    async def transform_webhook(
        self,
        payload: dict[str, Any],
        headers: dict[str, Any] | None = None,
    ) -> list[MemoryItem]:
        items: list[MemoryItem] = []
        topic = payload.get("topic", "unknown")
        data = payload.get("data", {}).get("item", payload.get("data", {}))

        if "conversation" in topic:
            source = data.get("source", {})
            subject = source.get("subject", "No subject")
            text = f"Intercom {topic}: {subject}"
            items.append(self._make_memory(
                text=text,
                source_id=f"intercom-event-{data.get('id', '')}",
                entity_type="conversation_event",
                metadata={"topic": topic, "conversation_id": data.get("id", "")},
            ))
        elif "contact" in topic:
            name = data.get("name", "Unknown")
            email = data.get("email", "")
            items.append(self._make_memory(
                text=f"Intercom {topic}: {name} ({email})",
                source_id=f"intercom-contact-event-{data.get('id', '')}",
                entity_type="contact_event",
                metadata={"topic": topic, "email": email},
            ))
        else:
            items.append(self._make_memory(
                text=f"Intercom event: {topic}",
                source_id=f"intercom-event-{payload.get('id', '')}",
                entity_type="intercom_event",
                metadata={"topic": topic},
            ))

        return items
