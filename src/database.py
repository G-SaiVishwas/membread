"""Database connection pool and initialization."""


import asyncpg
import structlog

from src.config import config

logger = structlog.get_logger()


class DatabasePool:
    """Async PostgreSQL connection pool manager."""

    def __init__(self) -> None:
        self.pool: asyncpg.Pool | None = None

    async def initialize(self) -> None:
        """Initialize the database connection pool."""
        try:
            self.pool = await asyncpg.create_pool(
                dsn=config.database_url,
                min_size=config.database_pool_min_size,
                max_size=config.database_pool_max_size,
                command_timeout=60,
            )
            logger.info(
                "database_pool_initialized",
                min_size=config.database_pool_min_size,
                max_size=config.database_pool_max_size,
            )

            # Test connection
            async with self.pool.acquire() as conn:
                version = await conn.fetchval("SELECT version()")
                logger.info("database_connected", version=version)

        except Exception as e:
            logger.error("database_pool_initialization_failed", error=str(e))
            raise

    async def close(self) -> None:
        """Close the database connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("database_pool_closed")

    async def execute_schema(self, schema_path: str = "schema.sql") -> None:
        """Execute schema.sql to initialize database."""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")

        try:
            with open(schema_path) as f:
                schema_sql = f.read()

            # Split schema into individual statements and execute them
            async with self.pool.acquire() as conn:
                # Split by semicolon but be careful with function definitions
                statements = []
                current_stmt = []
                in_function = False

                for line in schema_sql.split('\n'):
                    current_stmt.append(line)

                    # Track if we're inside a function definition
                    if 'CREATE OR REPLACE FUNCTION' in line or 'CREATE FUNCTION' in line:
                        in_function = True
                    elif in_function and '$$ LANGUAGE' in line:
                        in_function = False

                    # If we hit a semicolon and we're not in a function, that's a statement boundary
                    if line.strip().endswith(';') and not in_function:
                        stmt = '\n'.join(current_stmt).strip()
                        if stmt and not stmt.startswith('--'):
                            statements.append(stmt)
                        current_stmt = []

                # Execute each statement
                for stmt in statements:
                    if stmt.strip():
                        try:
                            await conn.execute(stmt)
                        except Exception as e:
                            # Log but don't fail on "already exists" errors
                            if 'already exists' not in str(e).lower():
                                logger.warning(
                    "schema_statement_failed",
                    error=str(e),
                    statement=stmt[:100],
                )

                logger.info("database_schema_executed", schema_path=schema_path)

        except FileNotFoundError:
            logger.warning("schema_file_not_found", schema_path=schema_path)
        except Exception as e:
            logger.error("schema_execution_skipped", error=str(e))

    def get_pool(self) -> asyncpg.Pool:
        """Get the connection pool."""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        return self.pool


# Global database pool instance
db_pool = DatabasePool()
