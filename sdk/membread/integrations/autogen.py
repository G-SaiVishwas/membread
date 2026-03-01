"""
AutoGen integration for Membread.

Provides a Teachability-compatible class that stores agent
conversations in the Membread central knowledge base.

Usage::

    from membread.integrations.autogen import MembreadAutoGenMemory

    memory = MembreadAutoGenMemory(
        api_url="http://localhost:8000",
        token="eyJ...",
    )

    # Use with AssistantAgent
    assistant = autogen.AssistantAgent("assistant", llm_config=config)
    memory.attach(assistant)
"""

from __future__ import annotations

from typing import Any

from membread.client import MembreadClient


class MembreadAutoGenMemory:
    """AutoGen-compatible memory that stores/recalls from Membread.

    Hooks into AutoGen agents via the `register_reply` mechanism
    to auto-capture all conversation turns.
    """

    def __init__(
        self,
        api_url: str = "http://localhost:8000",
        token: str = "",
        source: str = "autogen",
        agent_id: str = "autogen-agent",
        session_id: str | None = None,
    ):
        self.client = MembreadClient(
            api_url=api_url,
            token=token,
            source=source,
            agent_id=agent_id,
        )
        self.session_id = session_id

    def store(self, text: str, **kwargs: Any) -> dict:
        """Store text into Membread."""
        return self.client.store(text, session_id=self.session_id, **kwargs)

    def recall(self, query: str, **kwargs: Any) -> str:
        """Recall relevant context from Membread."""
        result = self.client.recall(query, **kwargs)
        return result.get("context", "")

    def attach(self, agent: Any) -> None:
        """Attach to an AutoGen agent to auto-capture messages.

        This uses the agent's `register_hook` or hooks into the
        `receive` method to capture all incoming messages.

        Args:
            agent: An AutoGen ConversableAgent instance.
        """
        original_receive = getattr(agent, "_process_received_message", None)

        if original_receive is None:
            # Fallback: try to hook into receive
            original_receive = getattr(agent, "receive", None)
            if original_receive is None:
                return

        memory = self

        def hooked_receive(message: Any, sender: Any, *args: Any, **kwargs: Any) -> Any:
            # Capture the message
            text = str(message) if not isinstance(message, str) else message
            if len(text) > 5:
                try:
                    memory.client.store(
                        text[:5000],
                        agent_id=getattr(agent, "name", "autogen-agent"),
                        session_id=memory.session_id,
                        metadata={
                            "sender": getattr(sender, "name", "unknown"),
                            "event": "message_received",
                        },
                    )
                except Exception:
                    pass  # Don't break the agent if memory fails

            return original_receive(message, sender, *args, **kwargs)

        if hasattr(agent, "_process_received_message"):
            agent._process_received_message = hooked_receive
        else:
            agent.receive = hooked_receive
