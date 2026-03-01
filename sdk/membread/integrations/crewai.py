"""
CrewAI integration for Membread.

Provides a tool and callback handler that stores/recalls agent
conversations from the Membread central knowledge base.

Usage::

    from membread.integrations.crewai import MembreadCrewAITool

    tool = MembreadCrewAITool(
        api_url="http://localhost:8000",
        token="eyJ...",
    )

    # Add as a tool to your CrewAI agent
    agent = Agent(
        role="Researcher",
        tools=[tool],
    )
"""

from __future__ import annotations

from typing import Any

from membread.client import MembreadClient


class MembreadCrewAITool:
    """CrewAI-compatible tool that stores/recalls from Membread.

    Agents get two operations:
    - "store: <text>" — saves text to central knowledge base
    - "recall: <query>" — retrieves relevant context

    Can be added to any CrewAI Agent's tool list.
    """

    name: str = "membread_memory"
    description: str = (
        "Store and recall persistent memory across sessions. "
        "Use 'store: <text>' to save information, or 'recall: <query>' to search past memories."
    )

    def __init__(
        self,
        api_url: str = "http://localhost:8000",
        token: str = "",
        source: str = "crewai",
        agent_id: str = "crewai-agent",
        session_id: str | None = None,
    ):
        self.client = MembreadClient(
            api_url=api_url,
            token=token,
            source=source,
            agent_id=agent_id,
        )
        self.session_id = session_id

    def _run(self, query: str) -> str:
        """Execute the tool with a store: or recall: prefix."""
        query = query.strip()

        if query.lower().startswith("store:"):
            text = query[6:].strip()
            result = self.client.store(text, session_id=self.session_id)
            return f"Stored memory (id: {result.get('observation_id', 'unknown')})"

        if query.lower().startswith("recall:"):
            search = query[7:].strip()
            result = self.client.recall(search)
            return result.get("context", "No relevant memories found.")

        # Default to recall
        result = self.client.recall(query)
        return result.get("context", "No relevant memories found.")


class MembreadCrewAICallback:
    """Callback handler that auto-captures CrewAI agent activity.

    Attach to a Crew to automatically store all agent outputs
    in the Membread knowledge base.
    """

    def __init__(
        self,
        api_url: str = "http://localhost:8000",
        token: str = "",
        source: str = "crewai",
    ):
        self.client = MembreadClient(
            api_url=api_url,
            token=token,
            source=source,
        )

    def on_task_output(self, task_output: Any) -> None:
        """Called when a CrewAI task completes."""
        text = str(task_output)
        if len(text) > 10:
            self.client.store(
                text[:5000],
                metadata={"event": "task_output"},
            )

    def on_agent_action(self, agent_name: str, action: str) -> None:
        """Called when an agent takes an action."""
        self.client.store(
            f"Agent '{agent_name}' action: {action[:500]}",
            agent_id=agent_name,
            metadata={"event": "agent_action"},
        )
