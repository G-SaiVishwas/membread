"""Zendesk connector — OAuth2/API-Key + Polling.

Captures tickets, comments, and customer interactions.
"""

import logging
from datetime import datetime, timedelta, timezone

import httpx

from typing import Any

from src.connectors.oauth import OAuthConfig
from typing import Any

from src.connectors.providers.base import BaseProvider, MemoryItem

logger = logging.getLogger("membread.providers.zendesk")


class ZendeskProvider(BaseProvider):
    provider_id = "zendesk"
    provider_name = "Zendesk"
    auth_method = "oauth2"
    poll_interval_seconds = 300

    supported_webhook_events = ["ticket.created", "ticket.updated", "ticket.solved"]

    def get_oauth_config(self, client_id: str = "", client_secret: str = "") -> OAuthConfig:
        return OAuthConfig(
            provider_id=self.provider_id,
            authorize_url="https://{subdomain}.zendesk.com/oauth/authorizations/new",
            token_url="https://{subdomain}.zendesk.com/oauth/tokens",
            client_id=client_id,
            client_secret=client_secret,
            scopes=["read", "tickets:read"],
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
        subdomain = (config or {}).get("subdomain", "")
        if not subdomain:
            return items, cursor
        token = access_token or api_key
        base = f"https://{subdomain}.zendesk.com/api/v2"
        headers = {"Authorization": f"Bearer {token}"} if access_token else {"Authorization": f"Basic {api_key}"}

        start_time = cursor or str(int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()))
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{base}/incremental/tickets.json",
                params={"start_time": start_time},
                headers=headers,
            )
            if resp.status_code == 200:
                data = resp.json()
                for ticket in data.get("tickets", []):
                    text = f"Ticket #{ticket.get('id')}: {ticket.get('subject', 'No subject')} — {ticket.get('status', '')}"
                    if ticket.get("priority"):
                        text += f" [{ticket['priority']}]"
                    items.append(self._make_memory(
                        text=text,
                        source_id=f"zendesk-ticket-{ticket['id']}",
                        entity_type="ticket",
                        metadata={
                            "zendesk_id": ticket["id"],
                            "status": ticket.get("status"),
                            "priority": ticket.get("priority"),
                            "type": ticket.get("type"),
                            "tags": ticket.get("tags", []),
                            "requester_id": ticket.get("requester_id"),
                        },
                        timestamp=ticket.get("updated_at"),
                    ))
                new_cursor = str(data.get("end_time", start_time))
            else:
                new_cursor = cursor
        return items, new_cursor

    async def transform_webhook(
        self,
        payload: dict[str, Any],
        headers: dict[str, Any] | None = None,
    ) -> list[MemoryItem]:
        items: list[MemoryItem] = []
        ticket = payload.get("ticket", payload)
        text = f"Zendesk: Ticket #{ticket.get('id', '')} — {ticket.get('subject', '')} [{ticket.get('status', '')}]"
        items.append(self._make_memory(
            text=text,
            source_id=f"zendesk-wh-{ticket.get('id', '')}",
            entity_type="ticket_event",
            metadata={"status": ticket.get("status"), "priority": ticket.get("priority")},
        ))
        return items
