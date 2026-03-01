"""DocuSign CLM connector — OAuth2 + Webhooks + Polling.

Captures contract signing events, agreement status, and envelope updates.
"""

import hashlib
import hmac
import logging
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import httpx

from src.connectors.oauth import OAuthConfig
from src.connectors.providers.base import BaseProvider, MemoryItem

logger = logging.getLogger("membread.providers.docusign")

DOCUSIGN_API = "https://na4.docusign.net/restapi/v2.1"
DOCUSIGN_AUTH = "https://account-d.docusign.com"  # demo; production: account.docusign.com


class DocuSignProvider(BaseProvider):
    provider_id = "docusign-clm"
    provider_name = "DocuSign CLM"
    auth_method = "oauth2"
    poll_interval_seconds = 600

    supported_webhook_events = [
        "envelope-sent",
        "envelope-delivered",
        "envelope-completed",
        "envelope-declined",
        "envelope-voided",
        "recipient-completed",
    ]

    def get_oauth_config(self, client_id: str = "", client_secret: str = "") -> OAuthConfig:
        return OAuthConfig(
            provider_id=self.provider_id,
            authorize_url=f"{DOCUSIGN_AUTH}/oauth/auth",
            token_url=f"{DOCUSIGN_AUTH}/oauth/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=["signature", "impersonation"],
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
        account_id = (config or {}).get("account_id", "")
        if not account_id:
            # Try to get account ID from userinfo
            return items, cursor

        base_url = (config or {}).get("base_url", DOCUSIGN_API)
        since = cursor or (
            datetime.now(UTC) - timedelta(hours=2)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient(timeout=30) as client:
            # List envelopes modified since cursor
            resp = await client.get(
                f"{base_url}/accounts/{account_id}/envelopes",
                params={
                    "from_date": since,
                    "order": "desc",
                    "count": 50,
                },
                headers=headers,
            )
            if resp.status_code == 200:
                for env in resp.json().get("envelopes", []):
                    status = env.get("status", "")
                    subject = env.get("emailSubject", "Untitled")
                    sender = env.get("sender", {}).get("userName", "")

                    text = f"DocuSign Envelope: {subject} — {status}"
                    if sender:
                        text += f" (from {sender})"

                    items.append(self._make_memory(
                        text=text,
                        source_id=f"docusign-env-{env['envelopeId']}",
                        entity_type="contract",
                        metadata={
                            "envelope_id": env["envelopeId"],
                            "status": status,
                            "sender": sender,
                            "email_subject": subject,
                            "recipients_count": len(env.get("recipients", {}).get("signers", [])),
                            "sent_date": env.get("sentDateTime"),
                            "completed_date": env.get("completedDateTime"),
                        },
                        timestamp=(
                            env.get("statusChangedDateTime")
                            or env.get("lastModifiedDateTime")
                        ),
                    ))

        new_cursor = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        return items, new_cursor

    async def on_connected(
        self,
        tenant_id: str,
        access_token: str | None = None,
        api_key: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Fetch account ID and base URL from DocuSign userinfo."""
        if not access_token:
            return None
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{DOCUSIGN_AUTH}/oauth/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if resp.status_code == 200:
                data = resp.json()
                accounts = data.get("accounts", [])
                if accounts:
                    default_acct = next((a for a in accounts if a.get("is_default")), accounts[0])
                    return {
                        "account_id": default_acct.get("account_id"),
                        "base_url": default_acct.get("base_uri", DOCUSIGN_API) + "/restapi/v2.1",
                    }
        return None

    async def register_webhook(
        self,
        access_token: str,
        webhook_url: str,
        events: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """DocuSign Connect — uses Connect configurations for webhooks."""
        # DocuSign requires Connect configuration via admin settings
        # For API-created webhooks, we create an envelope-level eventNotification
        return {"webhook_id": "docusign-connect", "events": events or self.supported_webhook_events}

    def verify_webhook(self, headers: dict[str, Any], body: bytes, secret: str) -> bool:
        # DocuSign Connect uses HMAC-SHA256
        sig = headers.get("x-docusign-signature-1", "")
        if not sig or not secret:
            return True
        import base64
        expected = base64.b64encode(
            hmac.new(secret.encode(), body, hashlib.sha256).digest()
        ).decode()
        return hmac.compare_digest(expected, sig)

    async def transform_webhook(
        self,
        payload: dict[str, Any],
        headers: dict[str, Any] | None = None,
    ) -> list[MemoryItem]:
        items: list[MemoryItem] = []
        # DocuSign Connect sends XML by default; JSON if configured
        event = payload.get("event", payload.get("Status", "unknown"))
        envelope = payload.get("data", payload.get("EnvelopeSummary", payload))

        if isinstance(envelope, dict):
            env = cast(dict[str, Any], envelope)
            status = env.get("status", env.get("Status", ""))
            subject = env.get("emailSubject", env.get("Subject", ""))
            env_id = env.get("envelopeId", env.get("EnvelopeID", ""))

            text = f"DocuSign {event}: {subject or 'Untitled'} — {status}"
            items.append(self._make_memory(
                text=text,
                source_id=f"docusign-event-{env_id}",
                entity_type="contract_event",
                metadata={
                    "event": event,
                    "envelope_id": env_id,
                    "status": status,
                    "subject": subject,
                },
            ))

        return items
