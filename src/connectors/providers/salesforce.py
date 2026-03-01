"""Salesforce connector — OAuth2 + Streaming API + Polling.

Captures leads, opportunities, cases, accounts, and platform events.
"""

import logging
from datetime import datetime, timedelta, timezone

import httpx

from typing import Any

from src.connectors.oauth import OAuthConfig
from typing import Any

from src.connectors.providers.base import BaseProvider, MemoryItem

logger = logging.getLogger("membread.providers.salesforce")


class SalesforceProvider(BaseProvider):
    provider_id = "salesforce"
    provider_name = "Salesforce"
    auth_method = "oauth2"
    poll_interval_seconds = 300

    supported_webhook_events = [
        "Opportunity",
        "Lead",
        "Case",
        "Account",
        "Contact",
    ]

    def get_oauth_config(self, client_id: str = "", client_secret: str = "") -> OAuthConfig:
        return OAuthConfig(
            provider_id=self.provider_id,
            authorize_url="https://login.salesforce.com/services/oauth2/authorize",
            token_url="https://login.salesforce.com/services/oauth2/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=["api", "refresh_token", "offline_access"],
            token_endpoint_auth="client_secret_post",
            revoke_url="https://login.salesforce.com/services/oauth2/revoke",
        )

    async def poll(
        self,
        access_token: str | None = None,
        api_key: str | None = None,
        cursor: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> tuple[list[MemoryItem], str | None]:
        items: list[MemoryItem] = []
        # cursor is the last modified timestamp ISO string
        since = cursor or (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Get instance URL from token (stored in config after OAuth)
        instance_url = (config or {}).get("instance_url", "https://na1.salesforce.com")
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

        async with httpx.AsyncClient(timeout=30) as client:
            # Query recently modified opportunities
            soql = (
                f"SELECT Id, Name, StageName, Amount, CloseDate, AccountId, OwnerId, LastModifiedDate "
                f"FROM Opportunity WHERE LastModifiedDate > {since} ORDER BY LastModifiedDate DESC LIMIT 100"
            )
            resp = await client.get(
                f"{instance_url}/services/data/v59.0/query",
                params={"q": soql},
                headers=headers,
            )
            if resp.status_code == 200:
                for record in resp.json().get("records", []):
                    text = f"Opportunity: {record.get('Name', 'Untitled')}"
                    stage = record.get("StageName", "")
                    amount = record.get("Amount")
                    if stage:
                        text += f" — {stage}"
                    if amount:
                        text += f" — ${amount:,.2f}"
                    items.append(self._make_memory(
                        text=text,
                        source_id=f"sf-opp-{record['Id']}",
                        entity_type="opportunity",
                        metadata={
                            "sf_id": record["Id"],
                            "stage": stage,
                            "amount": amount,
                            "close_date": record.get("CloseDate"),
                            "account_id": record.get("AccountId"),
                            "owner_id": record.get("OwnerId"),
                        },
                        timestamp=record.get("LastModifiedDate"),
                    ))

            # Query recently modified leads
            soql = (
                f"SELECT Id, Name, Email, Company, Status, LeadSource, LastModifiedDate "
                f"FROM Lead WHERE LastModifiedDate > {since} ORDER BY LastModifiedDate DESC LIMIT 100"
            )
            resp = await client.get(
                f"{instance_url}/services/data/v59.0/query",
                params={"q": soql},
                headers=headers,
            )
            if resp.status_code == 200:
                for record in resp.json().get("records", []):
                    text = f"Lead: {record.get('Name', '')} ({record.get('Email', '')})"
                    if record.get("Company"):
                        text += f" at {record['Company']}"
                    text += f" — Status: {record.get('Status', '')}"
                    items.append(self._make_memory(
                        text=text,
                        source_id=f"sf-lead-{record['Id']}",
                        entity_type="lead",
                        metadata={
                            "sf_id": record["Id"],
                            "email": record.get("Email"),
                            "company": record.get("Company"),
                            "status": record.get("Status"),
                            "source": record.get("LeadSource"),
                        },
                        timestamp=record.get("LastModifiedDate"),
                    ))

            # Query recent cases
            soql = (
                f"SELECT Id, Subject, Status, Priority, CaseNumber, LastModifiedDate "
                f"FROM Case WHERE LastModifiedDate > {since} ORDER BY LastModifiedDate DESC LIMIT 100"
            )
            resp = await client.get(
                f"{instance_url}/services/data/v59.0/query",
                params={"q": soql},
                headers=headers,
            )
            if resp.status_code == 200:
                for record in resp.json().get("records", []):
                    text = f"Case #{record.get('CaseNumber', '')}: {record.get('Subject', 'No subject')}"
                    text += f" — {record.get('Status', '')} ({record.get('Priority', '')})"
                    items.append(self._make_memory(
                        text=text,
                        source_id=f"sf-case-{record['Id']}",
                        entity_type="case",
                        metadata={
                            "sf_id": record["Id"],
                            "status": record.get("Status"),
                            "priority": record.get("Priority"),
                            "case_number": record.get("CaseNumber"),
                        },
                        timestamp=record.get("LastModifiedDate"),
                    ))

        new_cursor = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return items, new_cursor

    async def on_connected(self, tenant_id: str, access_token: str | None = None, api_key: str | None = None, config: dict[str, Any] | None = None) -> dict[str, Any] | None:
        """Fetch instance_url from Salesforce identity endpoint."""
        if not access_token:
            return None
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://login.salesforce.com/services/oauth2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if resp.status_code == 200:
                data = resp.json()
                return {"instance_url": data.get("urls", {}).get("custom_domain", "https://na1.salesforce.com")}
        return None

    async def transform_webhook(
        self,
        payload: dict[str, Any],
        headers: dict[str, Any] | None = None,
    ) -> list[MemoryItem]:
        """Salesforce Outbound Messages or Platform Events."""
        items: list[MemoryItem] = []
        # Handle Salesforce outbound message XML (simplified)
        # In production, parse SOAP XML; here we handle JSON platform events
        if payload:
            event_type = payload.get("type", payload.get("eventType", "unknown"))
            record = payload.get("data", payload)
            text = f"Salesforce Event: {event_type}"
            if "Name" in record:
                text += f" — {record['Name']}"
            items.append(self._make_memory(
                text=text,
                source_id=f"sf-event-{record.get('Id', record.get('replayId', ''))}",
                entity_type="sf_event",
                metadata=record,
            ))
        return items
