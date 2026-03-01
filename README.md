# Membread

> **Persistent, bi-temporal knowledge graph memory for AI agents.**

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)]()

Membread gives AI agents long-term memory that understands *when* facts changed. It combines vector search, a bi-temporal knowledge graph, and relational storage — all behind a single API. Store observations, recall context with sub-200 ms latency, and time-travel through your agent's history.

Built on [Graphiti-core](https://github.com/getzep/graphiti) + pgvector + FalkorDB.

---

## Features

- **Bi-temporal knowledge graph** — track what the system knows *and* when it learned it
- **Time-travel queries** — reconstruct state at any historical point with `as_of`
- **Hybrid retrieval** — BM25 + vector embedding + graph traversal
- **Self-compressing long-term memory** — automatic LLM-based summarisation
- **MCP server** — works with Claude Code, Cursor, Windsurf, VS Code Copilot
- **REST API** — FastAPI on port 8000 with JWT auth
- **47 connectors** — browser extension capture, OAuth integrations, webhooks, SDK callbacks
- **React dashboard** — full-featured SPA for browsing and managing memories
- **Streamlit dashboard** — interactive knowledge graph visualisation
- **Fully local mode** — runs entirely on Ollama, no paid API keys required
- **Multi-tenant** — row-level security, JWT isolation, privilege layers

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ (for the frontend)
- Docker & Docker Compose (for databases)

### 1. Clone & install

```bash
git clone https://github.com/AsmitaMallick/membread.git
cd membread

# Python dependencies
pip install -e ".[dev]"

# (Optional) Install the Python SDK
pip install -e ./sdk
```

### 2. Start the databases

```bash
docker compose up -d   # PostgreSQL (pgvector) + FalkorDB
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env — set OPENAI_API_KEY (or use local LLM mode below)
```

### 4. Run the API server

```bash
python server.py
# → API running on http://localhost:8000
```

### 5. Run the frontend

```bash
cd frontend
npm install
npm run dev
# → Dashboard on http://localhost:3000
```

### Fully-local mode (no paid API keys)

```bash
docker compose --profile local-llm up -d
ollama pull llama3 && ollama pull nomic-embed-text

export LOCAL_LLM_BASE_URL=http://localhost:11434/v1
export GRAPHITI_BACKEND=falkordb
python server.py
```

---

## Project Structure

```
membread/
├── server.py                   # Main API server (FastAPI)
├── src/
│   ├── api/                    # REST API routes
│   ├── auth/                   # JWT authentication
│   ├── governor/               # Conflict resolution, routing, provenance
│   ├── memory_engine/          # Core memory engine + graph store
│   ├── mcp_server/             # MCP protocol server
│   ├── services/               # Circuit breaker, compression, embeddings
│   └── connectors/             # 47 connectors (OAuth, webhook, polling)
├── frontend/                   # React + Vite + Tailwind dashboard
├── browser_extension/          # Chrome extension for capturing conversations
├── sdk/                        # Python SDK with LangChain/CrewAI/AutoGen/OpenAI integrations
├── ui/                         # Streamlit dashboard
├── benchmarks/                 # LoCoMo benchmark runner
├── tests/                      # Test suite
└── scripts/                    # Token generation, demo seeding, examples
```

---

## Architecture

```
┌───────────────────────────────────────────────────────┐
│                     Clients                           │
│  MCP (Claude/Cursor)  ·  REST API  ·  Browser Ext    │
│  React Dashboard  ·  Streamlit  ·  SDK callbacks      │
└────────────────────────┬──────────────────────────────┘
                         ↓
┌───────────────────────────────────────────────────────┐
│  Governor Layer                                       │
│  Conflict resolver · Constraint enforcer · Routing    │
│  Provenance tracker · Multi-hop traversal             │
└────────────────────────┬──────────────────────────────┘
                         ↓
┌───────────────────────────────────────────────────────┐
│  Memory Engine                                        │
│  Circuit breakers · Context compression               │
│  Concurrency control · Performance logging            │
└────────────────────────┬──────────────────────────────┘
                         ↓
┌───────────────────────────────────────────────────────┐
│  Storage Layer                                        │
│  pgvector (embeddings) · FalkorDB (graph) · SQL (RLS) │
└───────────────────────────────────────────────────────┘
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/memory/store` | Store an observation |
| `POST` | `/api/memory/recall` | Recall context (with compression) |
| `POST` | `/api/memory/search/temporal` | Bi-temporal time-travel search |
| `POST` | `/api/memory/entity/history` | Entity version history |
| `GET` | `/api/memory/graph` | Graph data for visualisation |
| `GET` | `/api/memory/list` | List recent memories |
| `GET` | `/api/memory/count` | Memory count |
| `POST` | `/api/capture` | Browser extension capture hook |
| `POST` | `/api/auth/token` | Generate JWT token |
| `GET` | `/api/connectors` | List connectors & status |
| `POST` | `/api/webhooks/{id}` | Webhook ingestion endpoint |

---

## MCP Server

Add Membread to any MCP-compatible tool:

```json
{
  "membread": {
    "command": "python",
    "args": ["-m", "src.mcp_server.server"],
    "cwd": "<path-to-membread>",
    "env": {
      "MEMBREAD_API_URL": "http://localhost:8000",
      "MEMBREAD_API_KEY": "<your-api-key>"
    }
  }
}
```

**Exposed tools:** `membread_store_observation`, `membread_recall_context`, `membread_get_profile`

---

## Browser Extension

The extension captures conversations from ChatGPT, Claude, Gemini, Perplexity, and Microsoft Copilot.

1. Open `chrome://extensions`
2. Enable **Developer Mode**
3. Click **Load unpacked** → select the `browser_extension/` folder
4. Click the extension icon and set your server URL

---

## Python SDK

```bash
pip install -e ./sdk
```

```python
from membread import MembreadClient

client = MembreadClient(
    api_url="http://localhost:8000",
    token="<your-jwt>"
)

# Store
client.store("User prefers dark mode", source="my-agent")

# Recall
result = client.recall("user preferences")
```

Integrations included: **LangChain**, **CrewAI**, **AutoGen**, **OpenAI** — see [sdk/README.md](sdk/README.md).

---

## Connectors

Membread ships with 47 connectors across 4 methods:

| Method | Connectors |
|--------|-----------|
| **Browser Extension** | ChatGPT, Claude, Gemini, Perplexity, Microsoft Copilot |
| **MCP** | Claude Code, Cursor, Windsurf, VS Code Copilot |
| **Webhook** | Vapi, Retell, Bland, Zapier, HubSpot, Salesforce, Zendesk, and more |
| **SDK** | LangChain, CrewAI, AutoGen, OpenAI SDK |

Connect any of them from the dashboard's **Connectors** page.

---

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | — |
| `LOCAL_LLM_BASE_URL` | Ollama / local LLM endpoint | — |
| `LOCAL_LLM_MODEL` | Local LLM model name | `llama3` |
| `LOCAL_EMBEDDING_MODEL` | Local embedding model | `nomic-embed-text` |
| `GRAPHITI_BACKEND` | `falkordb`, `neo4j`, `kuzu`, `memory` | `memory` |
| `GRAPHITI_URI` | Graph DB connection URI | `bolt://localhost:7687` |
| `ENABLE_TEMPORAL` | Enable bi-temporal KG | `true` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://...` |
| `JWT_SECRET` | JWT signing secret | `dev-secret-key` |
| `MAX_CONTEXT_TOKENS` | Token limit for compression | `2000` |

---

## Testing

```bash
pip install -e ".[dev]"

# All tests
pytest

# With coverage
pytest --cov=src --cov-report=html

# Individual suites
pytest tests/test_graphiti_engine.py -v
pytest tests/test_endpoints.py -v
pytest tests/test_benchmark.py -v
```

---

## Benchmark

LoCoMo benchmark evaluating temporal, multi-hop, point-in-time, and factual reasoning:

```bash
python -m benchmarks.run
python -m benchmarks.run --markdown   # GitHub-flavoured output
```

---

## Docker Compose

```bash
docker compose up -d                          # PostgreSQL + FalkorDB
docker compose --profile local-llm up -d      # + Ollama
docker compose logs -f membread               # Watch logs
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

[Apache 2.0](LICENSE)
