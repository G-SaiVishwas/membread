"""Enterprise connectors — API-Key/Webhook based providers.

Contains providers for: UiPath, Automation Anywhere, SAP, Oracle SCM,
Coupa, Ironclad, Magento, Twilio Flex.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx

from src.connectors.providers.base import BaseProvider, MemoryItem

logger = logging.getLogger("membread.providers.enterprise")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  UiPath — RPA bot execution logs
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class UiPathProvider(BaseProvider):
    provider_id = "uipath"
    provider_name = "UiPath"
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
        base_url = (config or {}).get("orchestrator_url", "https://cloud.uipath.com")
        tenant = (config or {}).get("tenant_name", "")
        folder_id = (config or {}).get("folder_id", "")
        if not api_key:
            return items, cursor

        headers = {
            "Authorization": f"Bearer {api_key}",
            "X-UIPATH-TenantName": tenant,
            "X-UIPATH-OrganizationUnitId": str(folder_id),
        }

        async with httpx.AsyncClient(timeout=30) as client:
            # Recent jobs
            since = cursor or (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
            resp = await client.get(
                f"{base_url}/odata/Jobs",
                params={
                    "$filter": f"EndTime gt {since}",
                    "$top": 50,
                    "$orderby": "EndTime desc",
                },
                headers=headers,
            )
            if resp.status_code == 200:
                for job in resp.json().get("value", []):
                    state = job.get("State", "")
                    process = job.get("ReleaseName", "Unknown")
                    text = f"UiPath Job: {process} — {state}"
                    if job.get("Info"):
                        text += f" | {job['Info'][:100]}"
                    items.append(self._make_memory(
                        text=text,
                        source_id=f"uipath-job-{job.get('Id', '')}",
                        entity_type="rpa_job",
                        metadata={
                            "job_id": str(job.get("Id")),
                            "state": state,
                            "process": process,
                            "robot_name": job.get("HostMachineName", ""),
                            "start_time": job.get("StartTime"),
                            "end_time": job.get("EndTime"),
                        },
                        timestamp=job.get("EndTime"),
                    ))

        return items, datetime.now(timezone.utc).isoformat()

    async def transform_webhook(
        self,
        payload: dict[str, Any],
        headers: dict[str, Any] | None = None,
    ) -> list[MemoryItem]:
        items: list[MemoryItem] = []
        event_type = payload.get("Type", payload.get("type", "unknown"))
        job = payload.get("Job", payload.get("job", payload))
        items.append(self._make_memory(
            text=f"UiPath {event_type}: {job.get('ReleaseName', job.get('name', 'Unknown'))}",
            source_id=f"uipath-wh-{job.get('Id', job.get('id', ''))}",
            entity_type="rpa_event",
            metadata={"event_type": event_type, "state": job.get("State", "")},
        ))
        return items


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Automation Anywhere — Bot runner activity
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class AutomationAnywhereProvider(BaseProvider):
    provider_id = "automation-anywhere"
    provider_name = "Automation Anywhere"
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
        base_url = (config or {}).get("control_room_url", "")
        if not base_url or not api_key:
            return items, cursor

        headers = {"X-Authorization": api_key}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{base_url}/v3/activity/list",
                json={"sort": [{"field": "modifiedOn", "direction": "desc"}], "page": {"length": 50}},
                headers=headers,
            )
            if resp.status_code == 200:
                for activity in resp.json().get("list", []):
                    status = activity.get("status", "")
                    bot_name = activity.get("botName", activity.get("fileName", "Unknown"))
                    text = f"AA Bot: {bot_name} — {status}"
                    items.append(self._make_memory(
                        text=text,
                        source_id=f"aa-activity-{activity.get('id', '')}",
                        entity_type="rpa_activity",
                        metadata={
                            "status": status,
                            "bot_name": bot_name,
                            "device": activity.get("deviceName", ""),
                        },
                        timestamp=activity.get("modifiedOn"),
                    ))

        return items, datetime.now(timezone.utc).isoformat()

    async def transform_webhook(
        self,
        payload: dict[str, Any],
        headers: dict[str, Any] | None = None,
    ) -> list[MemoryItem]:
        items: list[MemoryItem] = []
        items.append(self._make_memory(
            text=f"Automation Anywhere event: {payload.get('event', 'unknown')}",
            source_id=f"aa-wh-{payload.get('id', '')}",
            entity_type="rpa_event",
            metadata=payload,
        ))
        return items


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SAP — ERP events, purchase orders, material movements
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class SAPProvider(BaseProvider):
    provider_id = "sap"
    provider_name = "SAP"
    auth_method = "api_key"
    poll_interval_seconds = 900

    async def poll(
        self,
        access_token: str | None = None,
        api_key: str | None = None,
        cursor: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> tuple[list[MemoryItem], str | None]:
        items: list[MemoryItem] = []
        base_url = (config or {}).get("sap_url", "")
        if not base_url:
            return items, cursor

        headers = {"Authorization": f"Bearer {api_key or access_token}", "Accept": "application/json"}
        async with httpx.AsyncClient(timeout=30) as client:
            # Purchase orders via OData
            resp = await client.get(
                f"{base_url}/sap/opu/odata/sap/API_PURCHASEORDER_PROCESS_SRV/A_PurchaseOrder",
                params={"$top": 50, "$orderby": "LastChangeDateTime desc", "$format": "json"},
                headers=headers,
            )
            if resp.status_code == 200:
                for po in resp.json().get("d", {}).get("results", []):
                    text = f"SAP PO {po.get('PurchaseOrder', '')}: {po.get('CompanyCode', '')} — {po.get('PurchasingOrganization', '')}"
                    items.append(self._make_memory(
                        text=text,
                        source_id=f"sap-po-{po.get('PurchaseOrder', '')}",
                        entity_type="purchase_order",
                        metadata={
                            "po_number": po.get("PurchaseOrder"),
                            "company_code": po.get("CompanyCode"),
                            "supplier": po.get("Supplier"),
                        },
                        timestamp=po.get("LastChangeDateTime"),
                    ))

        return items, datetime.now(timezone.utc).isoformat()

    async def transform_webhook(
        self,
        payload: dict[str, Any],
        headers: dict[str, Any] | None = None,
    ) -> list[MemoryItem]:
        items: list[MemoryItem] = []
        event = payload.get("event", payload.get("type", "unknown"))
        items.append(self._make_memory(
            text=f"SAP event: {event}",
            source_id=f"sap-wh-{payload.get('id', '')}",
            entity_type="erp_event",
            metadata=payload,
        ))
        return items


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Oracle SCM — Supply chain planning and procurement
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class OracleSCMProvider(BaseProvider):
    provider_id = "oracle-scm"
    provider_name = "Oracle SCM"
    auth_method = "api_key"
    poll_interval_seconds = 900

    async def poll(
        self,
        access_token: str | None = None,
        api_key: str | None = None,
        cursor: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> tuple[list[MemoryItem], str | None]:
        items: list[MemoryItem] = []
        base_url = (config or {}).get("oracle_url", "")
        if not base_url:
            return items, cursor

        headers = {"Authorization": f"Bearer {api_key or access_token}", "Accept": "application/json"}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{base_url}/fscmRestApi/resources/latest/purchaseOrders",
                params={"limit": 50, "orderBy": "LastUpdateDate:desc"},
                headers=headers,
            )
            if resp.status_code == 200:
                for po in resp.json().get("items", []):
                    text = f"Oracle PO {po.get('OrderNumber', '')}: {po.get('Description', '')}"
                    items.append(self._make_memory(
                        text=text,
                        source_id=f"oracle-po-{po.get('POHeaderId', '')}",
                        entity_type="purchase_order",
                        metadata={"order_number": po.get("OrderNumber"), "status": po.get("Status")},
                        timestamp=po.get("LastUpdateDate"),
                    ))

        return items, datetime.now(timezone.utc).isoformat()

    async def transform_webhook(
        self,
        payload: dict[str, Any],
        headers: dict[str, Any] | None = None,
    ) -> list[MemoryItem]:
        items: list[MemoryItem] = []
        items.append(self._make_memory(
            text=f"Oracle SCM event: {payload.get('event', 'unknown')}",
            source_id=f"oracle-wh-{payload.get('id', '')}",
            entity_type="scm_event",
            metadata=payload,
        ))
        return items


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Coupa — Procurement, invoicing, spend management
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class CoupaProvider(BaseProvider):
    provider_id = "coupa"
    provider_name = "Coupa"
    auth_method = "api_key"
    poll_interval_seconds = 600

    async def poll(
        self,
        access_token: str | None = None,
        api_key: str | None = None,
        cursor: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> tuple[list[MemoryItem], str | None]:
        items: list[MemoryItem] = []
        base_url = (config or {}).get("coupa_url", "")
        if not base_url or not api_key:
            return items, cursor

        headers = {"X-COUPA-API-KEY": api_key, "Accept": "application/json"}
        async with httpx.AsyncClient(timeout=30) as client:
            since = cursor or (datetime.now(timezone.utc) - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
            resp = await client.get(
                f"{base_url}/api/purchase_orders",
                params={"updated_at[gt]": since, "limit": 50, "order_by": "updated_at", "dir": "desc"},
                headers=headers,
            )
            if resp.status_code == 200:
                for po in resp.json():
                    text = f"Coupa PO #{po.get('po_number', '')}: {po.get('status', '')} — ${po.get('total', 0)}"
                    items.append(self._make_memory(
                        text=text,
                        source_id=f"coupa-po-{po.get('id', '')}",
                        entity_type="purchase_order",
                        metadata={
                            "po_number": po.get("po_number"),
                            "status": po.get("status"),
                            "total": po.get("total"),
                            "supplier": po.get("supplier", {}).get("name", ""),
                        },
                        timestamp=po.get("updated_at"),
                    ))

        return items, datetime.now(timezone.utc).isoformat()

    async def transform_webhook(
        self,
        payload: dict[str, Any],
        headers: dict[str, Any] | None = None,
    ) -> list[MemoryItem]:
        items: list[MemoryItem] = []
        items.append(self._make_memory(
            text=f"Coupa event: {payload.get('event', 'unknown')}",
            source_id=f"coupa-wh-{payload.get('id', '')}",
            entity_type="procurement_event",
            metadata=payload,
        ))
        return items


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Ironclad — Contract lifecycle management
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class IroncladProvider(BaseProvider):
    provider_id = "ironclad"
    provider_name = "Ironclad"
    auth_method = "api_key"
    poll_interval_seconds = 600

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

        headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
        async with httpx.AsyncClient(timeout=30) as client:
            params = {"page": 0, "pageSize": 50}
            if cursor:
                params["lastUpdated"] = cursor
            resp = await client.get("https://ironcladapp.com/public/api/v1/workflows", params=params, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                for wf in data.get("list", data.get("records", [])):
                    status = wf.get("status", "")
                    title = wf.get("title", wf.get("name", "Untitled"))
                    text = f"Ironclad Workflow: {title} — {status}"
                    items.append(self._make_memory(
                        text=text,
                        source_id=f"ironclad-wf-{wf.get('id', '')}",
                        entity_type="contract_workflow",
                        metadata={
                            "workflow_id": wf.get("id"),
                            "status": status,
                            "template": wf.get("template", {}).get("name", ""),
                        },
                        timestamp=wf.get("lastUpdated"),
                    ))

        return items, datetime.now(timezone.utc).isoformat()

    async def transform_webhook(
        self,
        payload: dict[str, Any],
        headers: dict[str, Any] | None = None,
    ) -> list[MemoryItem]:
        items: list[MemoryItem] = []
        event = payload.get("event", "unknown")
        workflow = payload.get("workflow", payload)
        items.append(self._make_memory(
            text=f"Ironclad {event}: {workflow.get('title', '')}",
            source_id=f"ironclad-wh-{workflow.get('id', '')}",
            entity_type="contract_event",
            metadata={"event": event, "workflow_id": workflow.get("id")},
        ))
        return items


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Magento — E-commerce orders, catalog, customers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class MagentoProvider(BaseProvider):
    provider_id = "magento"
    provider_name = "Magento"
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
        base_url = (config or {}).get("magento_url", "")
        if not base_url or not api_key:
            return items, cursor

        since = cursor or (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{base_url}/rest/V1/orders",
                params={
                    "searchCriteria[filter_groups][0][filters][0][field]": "updated_at",
                    "searchCriteria[filter_groups][0][filters][0][value]": since,
                    "searchCriteria[filter_groups][0][filters][0][condition_type]": "gt",
                    "searchCriteria[sortOrders][0][field]": "updated_at",
                    "searchCriteria[sortOrders][0][direction]": "DESC",
                    "searchCriteria[pageSize]": 50,
                },
                headers=headers,
            )
            if resp.status_code == 200:
                for order in resp.json().get("items", []):
                    text = f"Magento Order #{order.get('increment_id', '')}: {order.get('status', '')} — ${order.get('grand_total', 0)}"
                    customer = order.get("customer_email", "")
                    if customer:
                        text += f" ({customer})"
                    items.append(self._make_memory(
                        text=text,
                        source_id=f"magento-order-{order.get('entity_id', '')}",
                        entity_type="order",
                        metadata={
                            "order_id": order.get("entity_id"),
                            "increment_id": order.get("increment_id"),
                            "status": order.get("status"),
                            "grand_total": order.get("grand_total"),
                            "customer_email": customer,
                            "items_count": len(order.get("items", [])),
                        },
                        timestamp=order.get("updated_at"),
                    ))

        return items, datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    async def transform_webhook(
        self,
        payload: dict[str, Any],
        headers: dict[str, Any] | None = None,
    ) -> list[MemoryItem]:
        items: list[MemoryItem] = []
        event = payload.get("event", "unknown")
        items.append(self._make_memory(
            text=f"Magento event: {event}",
            source_id=f"magento-wh-{payload.get('id', payload.get('entity_id', ''))}",
            entity_type="ecommerce_event",
            metadata=payload,
        ))
        return items


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Twilio Flex — Contact center interactions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TwilioFlexProvider(BaseProvider):
    provider_id = "twilio-flex"
    provider_name = "Twilio Flex"
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
        account_sid = (config or {}).get("account_sid", "")
        auth_token = (config or {}).get("auth_token", "")
        if not account_sid or not auth_token:
            return items, cursor

        auth = (account_sid, auth_token)
        async with httpx.AsyncClient(timeout=30, auth=auth) as client:
            since = cursor or (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
            resp = await client.get(
                f"https://flex-api.twilio.com/v1/interactions",
                params={"DateCreatedAfter": since, "PageSize": 50},
            )
            if resp.status_code == 200:
                for interaction in resp.json().get("interactions", []):
                    channel = interaction.get("channel", {}).get("type", "")
                    text = f"Twilio Flex Interaction: {channel} — {interaction.get('status', '')}"
                    items.append(self._make_memory(
                        text=text,
                        source_id=f"flex-{interaction.get('sid', '')}",
                        entity_type="interaction",
                        metadata={
                            "sid": interaction.get("sid"),
                            "channel": channel,
                            "status": interaction.get("status"),
                        },
                        timestamp=interaction.get("date_created"),
                    ))

        return items, datetime.now(timezone.utc).isoformat()

    async def transform_webhook(
        self,
        payload: dict[str, Any],
        headers: dict[str, Any] | None = None,
    ) -> list[MemoryItem]:
        items: list[MemoryItem] = []
        event_type = payload.get("EventType", payload.get("event", "unknown"))
        items.append(self._make_memory(
            text=f"Twilio Flex event: {event_type}",
            source_id=f"flex-wh-{payload.get('Sid', payload.get('sid', ''))}",
            entity_type="contact_center_event",
            metadata={"event_type": event_type, "sid": payload.get("Sid", "")},
        ))
        return items
