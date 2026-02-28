"""MCP Server implementation."""

import asyncio
from datetime import datetime
from typing import Any, Optional
import structlog
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from src.memory_engine.memory_engine import MemoryEngine
from src.memory_engine.sql_store import SQLStore
from src.auth.jwt_authenticator import JWTAuthenticator
from src.models import AuthenticationError, ProfileResult

logger = structlog.get_logger()


class MCPServer:
    """
    MCP protocol server exposing memory operations.
    Implements Anthropic MCP SDK specification.
    """

    def __init__(
        self,
        memory_engine: MemoryEngine,
        sql_store: SQLStore,
        authenticator: JWTAuthenticator,
    ):
        self.memory_engine = memory_engine
        self.sql_store = sql_store
        self.authenticator = authenticator
        self.server = Server("chronos-mcp")

        # Register tools
        self._register_tools()

    def _register_tools(self) -> None:
        """Register MCP tools."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            return [
                Tool(
                    name="chronos_store_observation",
                    description="Store an unstructured observation with temporal metadata",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "observation": {
                                "type": "string",
                                "description": "Raw text observation to store",
                            },
                            "metadata": {
                                "type": "object",
                                "description": "Additional context (tags, source, etc.)",
                            },
                            "token": {
                                "type": "string",
                                "description": "JWT authentication token",
                            },
                        },
                        "required": ["observation", "token"],
                    },
                ),
                Tool(
                    name="chronos_recall_context",
                    description="Retrieve relevant context with optional time-travel",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Semantic query string",
                            },
                            "token": {
                                "type": "string",
                                "description": "JWT authentication token",
                            },
                            "time_travel_ts": {
                                "type": "string",
                                "description": "Optional ISO-8601 timestamp for historical queries",
                            },
                            "max_tokens": {
                                "type": "integer",
                                "description": "Maximum context size (triggers compression)",
                                "default": 2000,
                            },
                        },
                        "required": ["query", "token"],
                    },
                ),
                Tool(
                    name="chronos_get_profile",
                    description="Return structured user profile data",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "token": {
                                "type": "string",
                                "description": "JWT authentication token",
                            },
                        },
                        "required": ["token"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> list[TextContent]:
            """Handle tool calls."""
            try:
                if name == "chronos_store_observation":
                    return await self._handle_store_observation(arguments)
                elif name == "chronos_recall_context":
                    return await self._handle_recall_context(arguments)
                elif name == "chronos_get_profile":
                    return await self._handle_get_profile(arguments)
                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]

            except Exception as e:
                logger.error("tool_call_failed", tool=name, error=str(e))
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_store_observation(self, arguments: dict) -> list[TextContent]:
        """Handle chronos_store_observation tool call."""
        observation = arguments.get("observation", "")
        metadata = arguments.get("metadata", {})
        token = arguments.get("token", "")

        # Authenticate
        claims = self.authenticator.validate_token(token)
        tenant_id = claims["tenant_id"]
        user_id = claims["user_id"]

        # Store observation
        result = await self.memory_engine.store_with_conflict_resolution(
            observation=observation,
            metadata=metadata,
            tenant_id=tenant_id,
            user_id=user_id,
        )

        response = f"""Observation stored successfully!

Observation ID: {result.observation_id}
Provenance Hash: {result.provenance_hash[:16]}...
Nodes Created: {result.nodes_created}
Conflicts Resolved: {result.conflicts_resolved}
"""

        return [TextContent(type="text", text=response)]

    async def _handle_recall_context(self, arguments: dict) -> list[TextContent]:
        """Handle chronos_recall_context tool call."""
        query = arguments.get("query", "")
        token = arguments.get("token", "")
        time_travel_ts_str = arguments.get("time_travel_ts")
        max_tokens = arguments.get("max_tokens", 2000)

        # Authenticate
        claims = self.authenticator.validate_token(token)
        tenant_id = claims["tenant_id"]
        user_id = claims["user_id"]

        # Parse time travel timestamp
        time_travel_ts = None
        if time_travel_ts_str:
            time_travel_ts = datetime.fromisoformat(time_travel_ts_str)

        # Recall context
        result = await self.memory_engine.recall_with_compression(
            query=query,
            tenant_id=tenant_id,
            user_id=user_id,
            time_travel_ts=time_travel_ts,
            max_tokens=max_tokens,
        )

        response = f"""Context Retrieved:

{result.context}

---
Sources: {len(result.sources)} observations
Token Count: {result.token_count}
Compressed: {result.compressed}
"""

        return [TextContent(type="text", text=response)]

    async def _handle_get_profile(self, arguments: dict) -> list[TextContent]:
        """Handle chronos_get_profile tool call."""
        token = arguments.get("token", "")

        # Authenticate
        claims = self.authenticator.validate_token(token)
        tenant_id = claims["tenant_id"]
        user_id = claims["user_id"]

        # Get profile
        profile = await self.sql_store.get_profile(tenant_id, user_id)

        if not profile:
            # Create default profile
            profile = await self.sql_store.create_profile(
                tenant_id=tenant_id,
                user_id=user_id,
                display_name="User",
                preferences={},
            )

        response = f"""User Profile:

Display Name: {profile.display_name}
Tenant ID: {profile.tenant_id}
User ID: {profile.user_id}
Preferences: {profile.preferences}
Created: {profile.created_at.isoformat()}
Updated: {profile.updated_at.isoformat()}
"""

        return [TextContent(type="text", text=response)]

    async def run(self) -> None:
        """Run the MCP server."""
        logger.info("mcp_server_starting")

        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )
