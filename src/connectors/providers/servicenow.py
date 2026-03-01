"""ServiceNow connector — OAuth2 + Polling.

Captures ITSM incidents, change requests, and CMDB updates.
"""

import logging
from datetime import datetime, timedelta, timezone

import httpx

from typing import Any

from src.connectors.oauth import OAuthConfig
from typing import Any

from src.connectors.providers.base import BaseProvider, MemoryItem

logger = logging.getLogger("membread.providers.servicenow")


class ServiceNowProvider(BaseProvider):
    provider_id = "servicenow"
    provider_name = "ServiceNow"
    auth_method = "oauth2"
    poll_interval_seconds = 300

    def get_oauth_config(self, client_id: str = "", client_secret: str = "") -> OAuthConfig:
        return OAuthConfig(
            provider_id=self.provider_id,
            authorize_url="https://{instance}.service-now.com/oauth_auth.do",
            token_url="https://{instance}.service-now.com/oauth_token.do",
            client_id=client_id,
            client_secret=client_secret,
            scopes=["useraccount"],
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
        instance = (config or {}).get("instance", "")
        if not instance:
            return items, cursor
        since = cursor or (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        base = f"https://{instance}.service-now.com/api/now"
        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}

        async with httpx.AsyncClient(timeout=30) as client:
            # Incidents
            resp = await client.get(
                f"{base}/table/incident",
                params={
                    "sysparm_query": f"sys_updated_on>{since}^ORDERBYDESCsys_updated_on",
                    "sysparm_limit": 50,
                    "sysparm_fields": "sys_id,number,short_description,state,priority,category,assigned_to,sys_updated_on",
                },
                headers=headers,
            )
            if resp.status_code == 200:
                for inc in resp.json().get("result", []):
                    states = {1: "New", 2: "In Progress", 3: "On Hold", 6: "Resolved", 7: "Closed"}
                    state_name = states.get(int(inc.get("state", 0)), str(inc.get("state")))
                    text = f"Incident {inc.get('number', '')}: {inc.get('short_description', '')} — {state_name}"
                    items.append(self._make_memory(
                        text=text,
                        source_id=f"snow-inc-{inc['sys_id']}",
                        entity_type="incident",
                        metadata={
                            "sys_id": inc["sys_id"],
                            "number": inc.get("number"),
                            "state": state_name,
                            "priority": inc.get("priority"),
                            "category": inc.get("category"),
                        },
                        timestamp=inc.get("sys_updated_on"),
                    ))

            # Change requests
            resp = await client.get(
                f"{base}/table/change_request",
                params={
                    "sysparm_query": f"sys_updated_on>{since}",
                    "sysparm_limit": 25,
                    "sysparm_fields": "sys_id,number,short_description,state,type,risk,sys_updated_on",
                },
                headers=headers,
            )
            if resp.status_code == 200:
                for cr in resp.json().get("result", []):
                    text = f"Change Request {cr.get('number', '')}: {cr.get('short_description', '')}"
                    items.append(self._make_memory(
                        text=text,
                        source_id=f"snow-cr-{cr['sys_id']}",
                        entity_type="change_request",
                        metadata={
                            "sys_id": cr["sys_id"],
                            "number": cr.get("number"),
                            "type": cr.get("type"),
                            "risk": cr.get("risk"),
                        },
                        timestamp=cr.get("sys_updated_on"),
                    ))

        return items, datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    async def transform_webhook(
        self,
        payload: dict[str, Any],
        headers: dict[str, Any] | None = None,
    ) -> list[MemoryItem]:
        items: list[MemoryItem] = []
        record = payload.get("record", payload)
        items.append(self._make_memory(
            text=f"ServiceNow event: {record.get('number', '')} — {record.get('short_description', '')}",
            source_id=f"snow-wh-{record.get('sys_id', '')}",
            entity_type="itsm_event",
            metadata=record,
        ))
        return items
