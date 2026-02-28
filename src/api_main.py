"""HTTP API entry point for ChronosMCP."""

import asyncio
import uvicorn
import structlog
from structlog.stdlib import LoggerFactory

from src.config import config
from src.database import db_pool
from src.memory_engine.vector_store import VectorStore
from src.memory_engine.graph_store import GraphStore
from src.memory_engine.sql_store import SQLStore
from src.memory_engine.memory_engine import MemoryEngine
from src.services.embedding_service import EmbeddingService
from src.services.context_compressor import ContextCompressor
from src.governor.governor import Governor
from src.auth.jwt_authenticator import JWTAuthenticator
from src.api.server import create_app

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
        structlog.processors.JSONRenderer() if config.log_format == "json" else structlog.dev.ConsoleRenderer(),
    ],
    context_class=dict,
    logger_factory=LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


async def initialize_system():
    """Initialize all system components."""
    logger.info("chronos_mcp_api_initializing", version="0.1.0")

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

    # Initialize memory engine
    memory_engine = MemoryEngine(
        vector_store=vector_store,
        graph_store=graph_store,
        sql_store=sql_store,
        embedding_service=embedding_service,
        governor=governor,
        context_compressor=context_compressor,
    )

    # Initialize authenticator
    authenticator = JWTAuthenticator()

    # Create FastAPI app
    app = create_app(
        memory_engine=memory_engine,
        sql_store=sql_store,
        authenticator=authenticator,
    )

    logger.info("chronos_mcp_api_initialized")

    return app


def main():
    """Main entry point."""
    global app
    # Initialize system
    app = asyncio.run(initialize_system())
    
    # Run server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )


# Create app instance for uvicorn
app = None

if __name__ == "__main__":
    main()
