"""iPaaS and Agent Platform connectors — Inbound webhook receivers.

Contains: n8n, Make (Integromat), Workato, Axiom.ai, Flowise, Relevance AI.
These are all webhook-only: the user configures the external tool to POST to our endpoint.
"""

import logging
from typing import Any, cast

from src.connectors.providers.base import BaseProvider, MemoryItem

logger = logging.getLogger("membread.providers.ipaas")


class N8nProvider(BaseProvider):
    provider_id = "n8n"
    provider_name = "n8n"
    auth_method = "webhook"
    poll_interval_seconds = 0

    supported_webhook_events = ["workflow.execution"]

    async def poll(
        self,
        access_token: str | None = None,
        api_key: str | None = None,
        cursor: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> tuple[list[MemoryItem], str | None]:
        return [], cursor

    async def transform_webhook(
        self,
        payload: dict[str, Any],
        headers: dict[str, Any] | None = None,
    ) -> list[MemoryItem]:
        items: list[MemoryItem] = []
        workflow = payload.get("workflow", {})
        execution = payload.get("execution", payload)
        name = workflow.get("name", execution.get("workflowName", "Unknown"))
        status = execution.get("status", execution.get("finished", ""))

        text = f"n8n Workflow: {name} — {status}"
        nodes = execution.get("data", {}).get("resultData", {}).get("runData", {})
        if nodes:
            text += f" ({len(nodes)} nodes executed)"

        items.append(self._make_memory(
            text=text,
            source_id=f"n8n-exec-{execution.get('id', execution.get('executionId', ''))}",
            entity_type="workflow_execution",
            metadata={
                "workflow_name": name,
                "workflow_id": workflow.get("id", execution.get("workflowId", "")),
                "status": str(status),
                "nodes_count": len(nodes) if nodes else 0,
                "mode": execution.get("mode", ""),
            },
        ))
        return items


class MakeProvider(BaseProvider):
    provider_id = "make"
    provider_name = "Make (Integromat)"
    auth_method = "webhook"
    poll_interval_seconds = 0

    async def poll(
        self,
        access_token: str | None = None,
        api_key: str | None = None,
        cursor: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> tuple[list[MemoryItem], str | None]:
        return [], cursor

    async def transform_webhook(
        self,
        payload: dict[str, Any],
        headers: dict[str, Any] | None = None,
    ) -> list[MemoryItem]:
        items: list[MemoryItem] = []
        scenario = payload.get("scenarioName", payload.get("scenario", "Unknown"))
        status = payload.get("status", payload.get("state", ""))
        ops = payload.get("operations", payload.get("ops", 0))

        text = f"Make Scenario: {scenario} — {status}"
        if ops:
            text += f" ({ops} operations)"

        items.append(self._make_memory(
            text=text,
            source_id=f"make-exec-{payload.get('executionId', payload.get('id', ''))}",
            entity_type="scenario_execution",
            metadata={
                "scenario": scenario,
                "status": str(status),
                "operations": ops,
            },
        ))
        return items


class WorkatoProvider(BaseProvider):
    provider_id = "workato"
    provider_name = "Workato"
    auth_method = "webhook"
    poll_interval_seconds = 0

    async def poll(
        self,
        access_token: str | None = None,
        api_key: str | None = None,
        cursor: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> tuple[list[MemoryItem], str | None]:
        return [], cursor

    async def transform_webhook(
        self,
        payload: dict[str, Any],
        headers: dict[str, Any] | None = None,
    ) -> list[MemoryItem]:
        items: list[MemoryItem] = []
        recipe = payload.get("recipe_name", payload.get("recipe", "Unknown"))
        action = payload.get("action", payload.get("event", ""))

        text = f"Workato Recipe: {recipe}"
        if action:
            text += f" — {action}"

        items.append(self._make_memory(
            text=text,
            source_id=f"workato-{payload.get('id', payload.get('job_id', ''))}",
            entity_type="recipe_execution",
            metadata={
                "recipe": recipe,
                "action": action,
                "status": payload.get("status", ""),
            },
        ))
        return items


class AxiomAIProvider(BaseProvider):
    provider_id = "axiom-ai"
    provider_name = "Axiom.ai"
    auth_method = "webhook"
    poll_interval_seconds = 0

    async def poll(
        self,
        access_token: str | None = None,
        api_key: str | None = None,
        cursor: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> tuple[list[MemoryItem], str | None]:
        return [], cursor

    async def transform_webhook(
        self,
        payload: dict[str, Any],
        headers: dict[str, Any] | None = None,
    ) -> list[MemoryItem]:
        items: list[MemoryItem] = []
        bot_name = payload.get("botName", payload.get("bot", "Unknown"))
        status = payload.get("status", "completed")
        data: Any = payload.get("data", payload.get("results", {}))

        text = f"Axiom.ai Bot: {bot_name} — {status}"
        if isinstance(data, dict) and data:
            text += f" | {len(cast(dict[str, Any], data))} fields extracted"
        elif isinstance(data, list):
            text += f" | {len(cast(list[Any], data))} rows extracted"

        items.append(self._make_memory(
            text=text,
            source_id=f"axiom-{payload.get('runId', payload.get('id', ''))}",
            entity_type="browser_automation",
            metadata={
                "bot_name": bot_name,
                "status": status,
                "data_count": len(cast(list[Any], data)) if data else 0,
            },
        ))
        return items


class FlowiseProvider(BaseProvider):
    provider_id = "flowise"
    provider_name = "Flowise"
    auth_method = "webhook"
    poll_interval_seconds = 0

    async def poll(
        self,
        access_token: str | None = None,
        api_key: str | None = None,
        cursor: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> tuple[list[MemoryItem], str | None]:
        return [], cursor

    async def transform_webhook(
        self,
        payload: dict[str, Any],
        headers: dict[str, Any] | None = None,
    ) -> list[MemoryItem]:
        items: list[MemoryItem] = []
        chatflow = payload.get("chatflow", payload.get("chatflowId", "Unknown"))
        question = payload.get("question", payload.get("input", ""))
        answer = payload.get("text", payload.get("output", payload.get("answer", "")))

        text = f"Flowise Chatflow: {chatflow}"
        if question:
            text += f"\nQ: {question[:200]}"
        if answer:
            text += f"\nA: {answer[:200]}"

        items.append(self._make_memory(
            text=text,
            source_id=f"flowise-{payload.get('chatId', payload.get('id', ''))}",
            entity_type="chatflow_execution",
            metadata={
                "chatflow": chatflow,
                "has_question": bool(question),
                "has_answer": bool(answer),
                "session_id": payload.get("sessionId", ""),
            },
        ))
        return items


class RelevanceAIProvider(BaseProvider):
    provider_id = "relevance-ai"
    provider_name = "Relevance AI"
    auth_method = "webhook"
    poll_interval_seconds = 0

    async def poll(
        self,
        access_token: str | None = None,
        api_key: str | None = None,
        cursor: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> tuple[list[MemoryItem], str | None]:
        return [], cursor

    async def transform_webhook(
        self,
        payload: dict[str, Any],
        headers: dict[str, Any] | None = None,
    ) -> list[MemoryItem]:
        items: list[MemoryItem] = []
        agent = payload.get("agent_name", payload.get("agent", "Unknown"))
        task = payload.get("task", payload.get("input", ""))
        output = payload.get("output", payload.get("result", ""))
        tools_used = payload.get("tools_used", payload.get("tools", []))

        text = f"Relevance AI Agent: {agent}"
        if task:
            text += f"\nTask: {task[:200]}"
        if output:
            text += f"\nResult: {output[:200]}"
        if tools_used:
            text += f"\nTools: {', '.join(tools_used[:5])}"

        items.append(self._make_memory(
            text=text,
            source_id=f"relevance-{payload.get('execution_id', payload.get('id', ''))}",
            entity_type="agent_execution",
            metadata={
                "agent": agent,
                "tools_used": tools_used,
                "status": payload.get("status", "completed"),
            },
        ))
        return items
