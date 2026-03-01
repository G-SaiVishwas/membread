"""
Membread SDK — Persistent memory layer for AI agents.

Usage:
    from membread import MembreadClient

    client = MembreadClient(api_url="http://localhost:8000", token="your-jwt-token")
    client.store("User prefers dark mode", source="my-agent", session_id="sess-1")
    context = client.recall("What are the user preferences?")
"""

from membread.client import MembreadClient
from membread.integrations.langchain import MembreadLangChainMemory
from membread.integrations.openai_patch import patch_openai

__version__ = "0.2.0"
__all__ = [
    "MembreadClient",
    "MembreadLangChainMemory",
    "patch_openai",
]
