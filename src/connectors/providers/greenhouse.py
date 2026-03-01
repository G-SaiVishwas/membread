"""Greenhouse connector — API-Key + Polling + Webhooks.

Captures candidates, applications, and hiring events.
"""

import hashlib
import hmac
import logging
from datetime import datetime, timedelta, timezone

import httpx

from typing import Any

from src.connectors.providers.base import BaseProvider, MemoryItem

logger = logging.getLogger("membread.providers.greenhouse")

GH_API = "https://harvest.greenhouse.io/v1"


class GreenhouseProvider(BaseProvider):
    provider_id = "greenhouse"
    provider_name = "Greenhouse"
    auth_method = "api_key"
    poll_interval_seconds = 600

    supported_webhook_events = [
        "candidate_hired",
        "candidate_stage_change",
        "application_updated",
        "offer_updated",
    ]

    async def poll(
        self,
        access_token: str | None = None,
        api_key: str | None = None,
        cursor: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> tuple[list[MemoryItem], str | None]:
        items: list[MemoryItem] = []
        if not api_key:
            return items, cursor

        since = cursor or (datetime.now(timezone.utc) - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        auth = (api_key, "")  # Basic auth with API key as username

        async with httpx.AsyncClient(timeout=30, auth=auth) as client:
            # Recent candidates
            resp = await client.get(
                f"{GH_API}/candidates",
                params={"updated_after": since, "per_page": 50},
            )
            if resp.status_code == 200:
                for cand in resp.json():
                    name = f"{cand.get('first_name', '')} {cand.get('last_name', '')}".strip()
                    emails = cand.get("email_addresses", [])
                    email = emails[0].get("value", "") if emails else ""
                    text = f"Candidate: {name}"
                    if email:
                        text += f" ({email})"
                    apps = cand.get("applications", [])
                    if apps:
                        text += f" — {len(apps)} application(s)"
                    items.append(self._make_memory(
                        text=text,
                        source_id=f"greenhouse-cand-{cand['id']}",
                        entity_type="candidate",
                        metadata={
                            "greenhouse_id": cand["id"],
                            "email": email,
                            "company": cand.get("company", ""),
                            "title": cand.get("title", ""),
                            "application_ids": [a.get("id") for a in apps],
                        },
                        timestamp=cand.get("updated_at"),
                    ))

            # Recent applications
            resp = await client.get(
                f"{GH_API}/applications",
                params={"last_activity_after": since, "per_page": 50},
            )
            if resp.status_code == 200:
                for app in resp.json():
                    status = app.get("status", "")
                    stage = app.get("current_stage", {}).get("name", "")
                    text = f"Application: {status}"
                    if stage:
                        text += f" — Stage: {stage}"
                    jobs = app.get("jobs", [])
                    if jobs:
                        text += f" for {jobs[0].get('name', '')}"
                    items.append(self._make_memory(
                        text=text,
                        source_id=f"greenhouse-app-{app['id']}",
                        entity_type="application",
                        metadata={
                            "greenhouse_id": app["id"],
                            "status": status,
                            "stage": stage,
                            "candidate_id": app.get("candidate_id"),
                            "job_names": [j.get("name", "") for j in jobs],
                        },
                        timestamp=app.get("last_activity_at"),
                    ))

        return items, datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def verify_webhook(self, headers: dict[str, Any], body: bytes, secret: str) -> bool:
        sig = headers.get("signature", "")
        if not sig or not secret:
            return True
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, sig)

    async def transform_webhook(
        self,
        payload: dict[str, Any],
        headers: dict[str, Any] | None = None,
    ) -> list[MemoryItem]:
        items: list[MemoryItem] = []
        action = payload.get("action", "unknown")
        data = payload.get("payload", {})

        if "candidate" in action:
            candidate = data.get("candidate", data)
            name = f"{candidate.get('first_name', '')} {candidate.get('last_name', '')}".strip()
            text = f"Greenhouse {action}: {name}"
            items.append(self._make_memory(
                text=text,
                source_id=f"greenhouse-event-{candidate.get('id', '')}",
                entity_type="recruiting_event",
                metadata={"action": action, "candidate_name": name},
            ))
        elif "application" in action:
            app = data.get("application", data)
            text = f"Greenhouse {action}: Application {app.get('id', '')}"
            items.append(self._make_memory(
                text=text,
                source_id=f"greenhouse-app-event-{app.get('id', '')}",
                entity_type="application_event",
                metadata={"action": action},
            ))
        elif "offer" in action:
            items.append(self._make_memory(
                text=f"Greenhouse {action}: Offer update",
                source_id=f"greenhouse-offer-{data.get('id', '')}",
                entity_type="offer_event",
                metadata={"action": action},
            ))

        return items
