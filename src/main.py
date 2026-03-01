"""Main entry point for Membread server."""

import asyncio

import structlog
from structlog.stdlib import LoggerFactory

from src.auth.jwt_authenticator import JWTAuthenticator
from src.config import config
from src.database import db_pool
from src.governor.governor import Governor
from src.mcp_server.server import MCPServer
from src.memory_engine.engines.graphiti_engine import GraphitiEngine
from src.memory_engine.graph_store import GraphStore
from src.memory_engine.memory_engine import MemoryEngine
from src.memory_engine.sql_store import SQLStore
from src.memory_engine.vector_store import VectorStore
from src.services.context_compressor import ContextCompressor
from src.services.embedding_service import EmbeddingService

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
        if config.log_format == "json"
        else structlog.dev.ConsoleRenderer(),
    ],
    context_class=dict,
    logger_factory=LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


async def initialize_system():
    """Initialize all system components."""
    logger.info("membread_initializing", version="0.1.0")

    # Validate configuration
    config.validate_required()

    # Initialize database pool
    await db_pool.initialize()

    # Execute schema
    try:
        await db_pool.execute_schema()
    except Exception as e:
        logger.warning("schema_execution_skipped", error=str(e))

    # Initialize stores
    pool = db_pool.get_pool()
    vector_store = VectorStore(pool)
    graph_store = GraphStore(pool)
    sql_store = SQLStore(pool)

    # Initialize services
    embedding_service = EmbeddingService()
    context_compressor = ContextCompressor()

    # Initialize governor
    governor = Governor(pool, graph_store)
    await governor.initialize()

    # Initialize Graphiti temporal engine (optional)
    graphiti_engine: GraphitiEngine | None = None
    if config.enable_temporal:
        graphiti_engine = GraphitiEngine(config)
        await graphiti_engine.initialize()
        logger.info("graphiti_engine_status", available=graphiti_engine.is_available)

    # Initialize memory engine
    memory_engine = MemoryEngine(
        vector_store=vector_store,
        graph_store=graph_store,
        sql_store=sql_store,
        embedding_service=embedding_service,
        governor=governor,
        context_compressor=context_compressor,
        graphiti_engine=graphiti_engine,
    )

    # Initialize authenticator
    authenticator = JWTAuthenticator()

    # Initialize MCP server
    mcp_server = MCPServer(
        memory_engine=memory_engine,
        sql_store=sql_store,
        authenticator=authenticator,
    )

    logger.info("membread_initialized")

    return mcp_server


async def main():
    """Main entry point."""
    try:
        mcp_server = await initialize_system()
        await mcp_server.run()
    except KeyboardInterrupt:
        logger.info("membread_shutting_down")
    except Exception as e:
        logger.error("membread_fatal_error", error=str(e))
        raise
    finally:
        await db_pool.close()
        logger.info("membread_stopped")


if __name__ == "__main__":
    asyncio.run(main())
