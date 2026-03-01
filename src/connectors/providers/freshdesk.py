"""Freshdesk connector — API-Key + Polling.

Captures helpdesk tickets and customer interactions.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from src.connectors.providers.base import BaseProvider, MemoryItem

logger = logging.getLogger("membread.providers.freshdesk")


class FreshdeskProvider(BaseProvider):
    provider_id = "freshdesk"
    provider_name = "Freshdesk"
    auth_method = "api_key"
    poll_interval_seconds = 300

    async def poll(
        self,
        access_token: str | None = None,
        api_key: str | None = None,
        cursor: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> tuple[list[MemoryItem], str | None]:
        items: list[MemoryItem] = []
        domain = (config or {}).get("domain", "")
        if not domain or not api_key:
            return items, cursor

        since = cursor or (
            datetime.now(UTC) - timedelta(hours=1)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        base = f"https://{domain}.freshdesk.com/api/v2"
        auth = (api_key, "X")  # Freshdesk uses API key as username

        async with httpx.AsyncClient(timeout=30, auth=auth) as client:
            resp = await client.get(
                f"{base}/tickets",
                params={
                    "updated_since": since,
                    "per_page": 50,
                    "order_by": "updated_at",
                    "order_type": "desc",
                },
            )
            if resp.status_code == 200:
                for ticket in resp.json():
                    text = (
                        f"Freshdesk #{ticket.get('id')}: "
                        f"{ticket.get('subject', '')} — "
                        f"Status: {ticket.get('status')}"
                    )
                    if ticket.get("priority"):
                        priorities = {1: "Low", 2: "Medium", 3: "High", 4: "Urgent"}
                        text += f" [{priorities.get(ticket['priority'], ticket['priority'])}]"
                    items.append(self._make_memory(
                        text=text,
                        source_id=f"freshdesk-{ticket['id']}",
                        entity_type="ticket",
                        metadata={
                            "freshdesk_id": ticket["id"],
                            "status": ticket.get("status"),
                            "priority": ticket.get("priority"),
                            "type": ticket.get("type"),
                            "source": ticket.get("source"),
                            "requester_id": ticket.get("requester_id"),
                            "tags": ticket.get("tags", []),
                        },
                        timestamp=ticket.get("updated_at"),
                    ))

        new_cursor = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        return items, new_cursor

    async def validate_api_key(self, api_key: str, config: dict[str, Any] | None = None) -> bool:
        domain = (config or {}).get("domain", "")
        if not domain:
            return True  # Can't validate without domain, accept the key
        async with httpx.AsyncClient(timeout=10, auth=(api_key, "X")) as client:
            resp = await client.get(f"https://{domain}.freshdesk.com/api/v2/tickets?per_page=1")
            return resp.status_code == 200

    async def transform_webhook(
        self,
        payload: dict[str, Any],
        headers: dict[str, Any] | None = None,
    ) -> list[MemoryItem]:
        items: list[MemoryItem] = []
        ticket = payload.get("ticket", payload)
        items.append(self._make_memory(
            text=f"Freshdesk: #{ticket.get('id', '')} — {ticket.get('subject', '')}",
            source_id=f"freshdesk-wh-{ticket.get('id', '')}",
            entity_type="ticket_event",
            metadata=payload,
        ))
        return items
