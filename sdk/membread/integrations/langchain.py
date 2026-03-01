# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""
LangChain / LangGraph integration for Membread.

Provides a BaseMemory-compatible class that stores and recalls
from the Membread central knowledge base.

Usage::

    from membread.integrations.langchain import MembreadLangChainMemory

    memory = MembreadLangChainMemory(
        api_url="http://localhost:8000",
        token="eyJ...",
        source="langchain",
    )

    # Use with any LangChain chain or agent
    from langchain.chains import ConversationChain
    chain = ConversationChain(llm=llm, memory=memory)
"""

from __future__ import annotations

from typing import Any, Dict, List

from membread.client import MembreadClient


class MembreadLangChainMemory:
    """LangChain-compatible memory backed by Membread.

    Implements the BaseChatMemory interface pattern so it can be used
    with ConversationChain, AgentExecutor, LangGraph, etc.

    All messages are stored in the central knowledge base. On recall,
    context is fetched from Membread's cross-tool memory search.
    """

    memory_key: str = "history"
    input_key: str = "input"
    output_key: str = "output"

    def __init__(
        self,
        api_url: str = "http://localhost:8000",
        token: str = "",
        source: str = "langchain",
        session_id: str | None = None,
        agent_id: str = "langchain-agent",
        return_messages: bool = False,
    ):
        self.client = MembreadClient(
            api_url=api_url,
            token=token,
            source=source,
            agent_id=agent_id,
        )
        self.source = source
        self.session_id = session_id
        self.agent_id = agent_id
        self.return_messages = return_messages
        self._buffer: List[Dict[str, str]] = []

    @property
    def memory_variables(self) -> list[str]:
        return [self.memory_key]

    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Load relevant context from Membread for the current input."""
        query = inputs.get(self.input_key, "")
        if not query:
            return {self.memory_key: "" if not self.return_messages else []}

        result = self.client.recall(query)
        context = result.get("context", "")

        if self.return_messages:
            # Return as message-like dicts for chat models
            return {self.memory_key: [{"role": "system", "content": f"Relevant context:\n{context}"}]}

        return {self.memory_key: context}

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        """Store the input/output pair in Membread."""
        user_input = inputs.get(self.input_key, "")
        ai_output = outputs.get(self.output_key, "")

        if user_input:
            self.client.store(
                f"User: {user_input}",
                source=self.source,
                agent_id=self.agent_id,
                session_id=self.session_id,
                metadata={"role": "user"},
            )

        if ai_output:
            self.client.store(
                f"Assistant: {ai_output}",
                source=self.source,
                agent_id=self.agent_id,
                session_id=self.session_id,
                metadata={"role": "assistant"},
            )

    def clear(self) -> None:
        """Clear local buffer (Membread memories are immutable)."""
        self._buffer.clear()
