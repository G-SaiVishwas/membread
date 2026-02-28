"""Setup script for ChronosMCP."""

from setuptools import setup, find_packages

setup(
    name="chronos-mcp",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "asyncpg>=0.29.0",
        "pgvector>=0.2.4",
        "mcp>=0.9.0",
        "pydantic>=2.5.0",
        "openai>=1.10.0",
        "pyjwt>=2.8.0",
        "cryptography>=41.0.0",
        "aiosqlite>=0.19.0",
        "tiktoken>=0.5.2",
        "python-dotenv>=1.0.0",
        "structlog>=24.1.0",
    ],
)
