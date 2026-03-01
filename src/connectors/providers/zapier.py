"""Zapier connector — Webhook-based inbound data capture.

Receives Zap trigger/action data via Zapier webhook integration.
Users configure Zapier to POST to our webhook URL.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from src.connectors.providers.base import BaseProvider, MemoryItem

logger = logging.getLogger("membread.providers.zapier")


class ZapierProvider(BaseProvider):
    provider_id = "zapier"
    provider_name = "Zapier"
    auth_method = "webhook"
    poll_interval_seconds = 0  # Webhook-only, no polling

    supported_webhook_events = ["zap.execution"]

    async def poll(
        self,
        access_token: str | None = None,
        api_key: str | None = None,
        cursor: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> tuple[list[MemoryItem], str | None]:
        # Zapier is webhook-only — no polling
        return [], cursor

    async def transform_webhook(
        self,
        payload: dict[str, Any],
        headers: dict[str, Any] | None = None,
    ) -> list[MemoryItem]:
        items: list[MemoryItem] = []

        # Zapier sends arbitrary JSON data depending on the Zap
        zap_name = payload.get("zap_name", payload.get("zap", "Unknown Zap"))
        trigger_app = payload.get("trigger_app", payload.get("source", "unknown"))
        action = payload.get("action", payload.get("event", ""))

        # Build a descriptive memory for the Zap execution
        text_parts = [f"Zapier: {zap_name}"]
        if trigger_app:
            text_parts.append(f"Trigger: {trigger_app}")
        if action:
            text_parts.append(f"Action: {action}")

        # Include key data fields
        data_fields = {k: v for k, v in payload.items()
                       if k not in ("zap_name", "zap", "trigger_app", "source", "action", "event")
                       and isinstance(v, str | int | float | bool)}
        if data_fields:
            text_parts.append(
                "Data: " + ", ".join(
                    f"{k}={v}"
                    for k, v in list(data_fields.items())[:10]
                )
            )

        text = " | ".join(text_parts)

        items.append(self._make_memory(
            text=text,
            source_id=f"zapier-{payload.get('id', datetime.now(UTC).timestamp())}",
            entity_type="automation_event",
            metadata={
                "zap_name": zap_name,
                "trigger_app": trigger_app,
                "action": action,
                **data_fields,
            },
        ))
        return items
