import React, { useState } from 'react';
import {
  BookOpenIcon,
  RocketLaunchIcon,
  CpuChipIcon,
  ServerIcon,
  PuzzlePieceIcon,
  CommandLineIcon,
  CodeBracketIcon,
  KeyIcon,
  Cog6ToothIcon,
  BeakerIcon,
  GlobeAltIcon,
  ClipboardDocumentIcon,
  CheckIcon,
  ChevronRightIcon,
} from '@heroicons/react/24/outline';

/* ── Section data ──────────────────────────────────────────────────── */

interface DocSection {
  id: string;
  title: string;
  icon: React.FC<{ className?: string }>;
  content: React.ReactNode;
}

const CodeBlock: React.FC<{ children: string; language?: string }> = ({ children, language }) => {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(children.trim());
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <div className="relative group rounded-xl overflow-hidden my-3">
      {language && (
        <div className="bg-gray-800 px-4 py-1.5 text-[10px] font-mono text-gray-400 uppercase tracking-wider border-b border-gray-700/60">
          {language}
        </div>
      )}
      <pre className="bg-gray-900 text-gray-200 text-[13px] leading-relaxed p-4 overflow-x-auto font-mono">
        <code>{children.trim()}</code>
      </pre>
      <button
        onClick={copy}
        className="absolute top-2.5 right-2.5 p-1.5 rounded-lg bg-gray-700/60 text-gray-400 hover:text-white hover:bg-gray-700 opacity-0 group-hover:opacity-100 transition-all"
      >
        {copied ? <CheckIcon className="w-4 h-4 text-emerald-400" /> : <ClipboardDocumentIcon className="w-4 h-4" />}
      </button>
    </div>
  );
};

const H3: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <h3 className="text-[15px] font-bold text-gray-900 mt-6 mb-2">{children}</h3>
);

const P: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <p className="text-[13px] text-gray-600 leading-relaxed mb-3">{children}</p>
);

const Table: React.FC<{ headers: string[]; rows: string[][] }> = ({ headers, rows }) => (
  <div className="overflow-x-auto my-3 rounded-xl border border-gray-200">
    <table className="w-full text-[13px]">
      <thead>
        <tr className="bg-gray-50">
          {headers.map((h) => (
            <th key={h} className="text-left px-4 py-2.5 font-semibold text-gray-700 border-b border-gray-200">
              {h}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, i) => (
          <tr key={i} className="border-b border-gray-100 last:border-0">
            {row.map((cell, j) => (
              <td key={j} className="px-4 py-2.5 text-gray-600 font-mono text-[12px]">
                {cell}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);

/* ── Sections ──────────────────────────────────────────────────────── */

const sections: DocSection[] = [
  {
    id: 'overview',
    title: 'Overview',
    icon: BookOpenIcon,
    content: (
      <>
        <P>
          Membread is a persistent, bi-temporal knowledge graph memory layer for AI agents.
          It combines vector search, a bi-temporal knowledge graph, and relational storage — all behind
          a single API. Store observations, recall context with sub-200 ms latency, and time-travel
          through your agent's history.
        </P>
        <H3>Core Capabilities</H3>
        <ul className="list-none space-y-2 mb-4">
          {[
            'Bi-temporal knowledge graph — track what the system knows and when it learned it',
            'Time-travel queries — reconstruct state at any historical point with as_of',
            'Hybrid retrieval — BM25 + vector embedding + graph traversal',
            'Self-compressing long-term memory — automatic LLM-based summarisation',
            '47 connectors — browser extension, MCP, webhooks, SDK',
            'Multi-tenant — row-level security, JWT isolation, privilege layers',
            'Fully local mode — runs entirely on Ollama, no paid API keys required',
          ].map((item) => (
            <li key={item} className="flex items-start gap-2 text-[13px] text-gray-600">
              <ChevronRightIcon className="w-3.5 h-3.5 text-gray-400 mt-0.5 shrink-0" />
              {item}
            </li>
          ))}
        </ul>
        <H3>Architecture</H3>
        <CodeBlock language="text">{`
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
        `}</CodeBlock>
      </>
    ),
  },
  {
    id: 'quickstart',
    title: 'Quick Start',
    icon: RocketLaunchIcon,
    content: (
      <>
        <H3>Prerequisites</H3>
        <ul className="list-disc list-inside text-[13px] text-gray-600 mb-4 space-y-1">
          <li>Python 3.11+</li>
          <li>Node.js 18+ (for the frontend)</li>
          <li>Docker & Docker Compose (for databases)</li>
        </ul>
        <H3>1. Clone & Install</H3>
        <CodeBlock language="bash">{`
git clone https://github.com/AsmitaMallick/membread.git
cd membread

# Python dependencies
pip install -e ".[dev]"

# (Optional) Install the Python SDK
pip install -e ./sdk
        `}</CodeBlock>
        <H3>2. Start the Databases</H3>
        <CodeBlock language="bash">{`
docker compose up -d   # PostgreSQL (pgvector) + FalkorDB
        `}</CodeBlock>
        <H3>3. Configure Environment</H3>
        <CodeBlock language="bash">{`
cp .env.example .env
# Edit .env — set OPENAI_API_KEY (or use local LLM mode)
        `}</CodeBlock>
        <H3>4. Run the API Server</H3>
        <CodeBlock language="bash">{`
python server.py
# → API running on http://localhost:8000
        `}</CodeBlock>
        <H3>5. Run the Frontend</H3>
        <CodeBlock language="bash">{`
cd frontend
npm install
npm run dev
# → Dashboard on http://localhost:3000
        `}</CodeBlock>
        <H3>Fully-Local Mode (No Paid API Keys)</H3>
        <P>Run entirely on Ollama without any paid API keys:</P>
        <CodeBlock language="bash">{`
docker compose --profile local-llm up -d
ollama pull llama3 && ollama pull nomic-embed-text

export LOCAL_LLM_BASE_URL=http://localhost:11434/v1
export GRAPHITI_BACKEND=falkordb
python server.py
        `}</CodeBlock>
      </>
    ),
  },
  {
    id: 'api',
    title: 'REST API',
    icon: ServerIcon,
    content: (
      <>
        <P>
          The Membread API runs on FastAPI at port 8000. All endpoints (except <code className="text-[12px] bg-gray-100 px-1 py-0.5 rounded">/health</code> and
          <code className="text-[12px] bg-gray-100 px-1 py-0.5 rounded">/api/auth/token</code>) require a JWT Bearer token.
        </P>
        <H3>Endpoints</H3>
        <Table
          headers={['Method', 'Endpoint', 'Description']}
          rows={[
            ['POST', '/api/memory/store', 'Store an observation'],
            ['POST', '/api/memory/recall', 'Recall context (with compression)'],
            ['POST', '/api/memory/search/temporal', 'Bi-temporal time-travel search'],
            ['POST', '/api/memory/entity/history', 'Entity version history'],
            ['GET', '/api/memory/graph', 'Graph data for visualisation'],
            ['GET', '/api/memory/list', 'List recent memories'],
            ['GET', '/api/memory/count', 'Memory count'],
            ['POST', '/api/capture', 'Browser extension capture hook'],
            ['POST', '/api/auth/token', 'Generate JWT token'],
            ['GET', '/api/connectors', 'List connectors & status'],
            ['POST', '/api/connectors/{id}/connect', 'Connect a connector'],
            ['POST', '/api/connectors/{id}/disconnect', 'Disconnect a connector'],
            ['POST', '/api/webhooks/{id}', 'Webhook ingestion endpoint'],
            ['GET', '/health', 'Health check'],
          ]}
        />
        <H3>Store an Observation</H3>
        <CodeBlock language="bash">{`
curl -X POST http://localhost:8000/api/memory/store \\
  -H "Authorization: Bearer <token>" \\
  -H "Content-Type: application/json" \\
  -d '{
    "content": "User prefers dark mode",
    "source": "my-agent",
    "agent_id": "agent-1"
  }'
        `}</CodeBlock>
        <H3>Recall Context</H3>
        <CodeBlock language="bash">{`
curl -X POST http://localhost:8000/api/memory/recall \\
  -H "Authorization: Bearer <token>" \\
  -H "Content-Type: application/json" \\
  -d '{
    "query": "user preferences",
    "agent_id": "agent-1",
    "max_tokens": 2000
  }'
        `}</CodeBlock>
        <H3>Time-Travel Search</H3>
        <CodeBlock language="bash">{`
curl -X POST http://localhost:8000/api/memory/search/temporal \\
  -H "Authorization: Bearer <token>" \\
  -H "Content-Type: application/json" \\
  -d '{
    "query": "project requirements",
    "as_of": "2025-06-01T00:00:00Z",
    "temporal_type": "point_in_time"
  }'
        `}</CodeBlock>
        <H3>Generate Token</H3>
        <CodeBlock language="bash">{`
curl -X POST http://localhost:8000/api/auth/token \\
  -H "Content-Type: application/json" \\
  -d '{"user_id": "user-1", "scope": "admin"}'
        `}</CodeBlock>
      </>
    ),
  },
  {
    id: 'mcp',
    title: 'MCP Server',
    icon: CpuChipIcon,
    content: (
      <>
        <P>
          Membread includes an MCP (Model Context Protocol) server that works with Claude Code, Cursor,
          Windsurf, and VS Code Copilot. It exposes three tools for storing, recalling, and profiling
          agent memory.
        </P>
        <H3>Configuration</H3>
        <P>Add the following to your tool's MCP configuration file:</P>
        <CodeBlock language="json">{`
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
        `}</CodeBlock>
        <H3>Exposed Tools</H3>
        <Table
          headers={['Tool', 'Description']}
          rows={[
            ['membread_store_observation', 'Store an observation in the knowledge graph'],
            ['membread_recall_context', 'Recall relevant context from memory for a query'],
            ['membread_get_profile', 'Get the compiled user/agent profile from stored memories'],
          ]}
        />
        <H3>Config File Locations</H3>
        <Table
          headers={['Tool', 'Config Path']}
          rows={[
            ['Claude Code', '~/.claude/claude_desktop_config.json'],
            ['Cursor', '~/.cursor/mcp.json'],
            ['Windsurf', '~/.codeium/windsurf/mcp_config.json'],
            ['VS Code Copilot', '.vscode/mcp.json (per-project)'],
          ]}
        />
      </>
    ),
  },
  {
    id: 'sdk',
    title: 'Python SDK',
    icon: CodeBracketIcon,
    content: (
      <>
        <H3>Installation</H3>
        <CodeBlock language="bash">{`
pip install -e ./sdk
        `}</CodeBlock>
        <H3>Basic Usage</H3>
        <CodeBlock language="python">{`
from membread import MembreadClient

client = MembreadClient(
    api_url="http://localhost:8000",
    token="<your-jwt>"
)

# Store an observation
client.store("User prefers dark mode", source="my-agent")

# Recall context
result = client.recall("user preferences")
print(result["context"])

# Time-travel search
result = client.temporal_search(
    query="project requirements",
    as_of="2025-06-01T00:00:00Z"
)
        `}</CodeBlock>
        <H3>LangChain Integration</H3>
        <CodeBlock language="python">{`
from membread.integrations.langchain import MembreadLangChainMemory
from langchain.chains import ConversationChain
from langchain.chat_models import ChatOpenAI

memory = MembreadLangChainMemory(
    api_url="http://localhost:8000",
    token="<token>"
)

chain = ConversationChain(
    llm=ChatOpenAI(),
    memory=memory
)

chain.run("What did we discuss last week?")
        `}</CodeBlock>
        <H3>CrewAI Integration</H3>
        <CodeBlock language="python">{`
from membread.integrations.crewai import MembreadCrewAITool

memory_tool = MembreadCrewAITool(
    api_url="http://localhost:8000",
    token="<token>"
)

# Add to your CrewAI agent's tools list
agent = Agent(
    role="Research Assistant",
    tools=[memory_tool]
)
        `}</CodeBlock>
        <H3>AutoGen Integration</H3>
        <CodeBlock language="python">{`
from membread.integrations.autogen import MembreadAutoGenMemory

memory = MembreadAutoGenMemory(
    api_url="http://localhost:8000",
    token="<token>"
)

# Wrap your AutoGen agent
agent = autogen.AssistantAgent(
    "assistant",
    llm_config=llm_config
)
memory.attach(agent)
        `}</CodeBlock>
        <H3>OpenAI Patch</H3>
        <CodeBlock language="python">{`
from membread.integrations.openai_patch import patch_openai
import openai

# Automatically captures all OpenAI calls
patch_openai(
    api_url="http://localhost:8000",
    token="<token>"
)

# Works transparently
response = openai.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}]
)
        `}</CodeBlock>
      </>
    ),
  },
  {
    id: 'connectors',
    title: 'Connectors',
    icon: PuzzlePieceIcon,
    content: (
      <>
        <P>
          Membread ships with 47 connectors across 4 integration methods. Manage them from the
          Connectors page in the dashboard.
        </P>
        <H3>Integration Methods</H3>
        <Table
          headers={['Method', 'How It Works', 'Count']}
          rows={[
            ['Browser Extension', 'Captures conversations from AI chat interfaces (ChatGPT, Claude, Gemini, Perplexity, Microsoft Copilot). Load the extension from browser_extension/ folder.', '5'],
            ['MCP', 'Model Context Protocol integration for AI code editors. Add the MCP server config to your tool.', '4'],
            ['Webhook', 'Receive events from external services via POST /api/webhooks/{connector_id}. Configure the URL in your service settings.', '34'],
            ['SDK', 'Python SDK callbacks for LangChain, CrewAI, AutoGen, and OpenAI. Install with pip install -e ./sdk.', '4'],
          ]}
        />
        <H3>Browser Extension Setup</H3>
        <ol className="list-decimal list-inside text-[13px] text-gray-600 mb-4 space-y-1">
          <li>Open <code className="text-[12px] bg-gray-100 px-1 py-0.5 rounded">chrome://extensions</code></li>
          <li>Enable <strong>Developer Mode</strong></li>
          <li>Click <strong>Load unpacked</strong> → select the <code className="text-[12px] bg-gray-100 px-1 py-0.5 rounded">browser_extension/</code> folder</li>
          <li>Click the extension icon and set your server URL</li>
        </ol>
        <H3>Webhook Configuration</H3>
        <P>
          Each webhook connector has a unique URL:{' '}
          <code className="text-[12px] bg-gray-100 px-1.5 py-0.5 rounded">POST /api/webhooks/&#123;connector_id&#125;</code>
        </P>
        <P>
          Configure this URL in your external service's webhook settings. Membread includes built-in
          parsers for major platforms (Vapi, Retell, Bland, Zapier, HubSpot, Salesforce, Zendesk,
          Intercom, ServiceNow, and more).
        </P>
        <H3>Connector Categories</H3>
        <Table
          headers={['Category', 'Connectors']}
          rows={[
            ['Browser Extension', 'ChatGPT, Claude, Gemini, Perplexity, Microsoft Copilot'],
            ['MCP Native', 'Claude Code, Cursor, Windsurf, VS Code Copilot'],
            ['Voice AI', 'Vapi, Retell, Bland'],
            ['Agent SDK', 'LangChain, CrewAI, AutoGen, OpenAI SDK'],
            ['Marketing', 'Zapier, HubSpot, Marketo'],
            ['Sales', 'Salesforce, Outreach, SalesLoft'],
            ['Support', 'Intercom, Zendesk, Freshdesk, Twilio Flex'],
            ['Finance & RPA', 'UiPath, Automation Anywhere'],
            ['HR & Recruiting', 'Workday, Greenhouse, Lever'],
            ['DevOps & ITSM', 'ServiceNow, PagerDuty'],
            ['Supply Chain', 'SAP, Oracle SCM, Coupa'],
            ['Legal', 'Ironclad, DocuSign CLM'],
            ['E-commerce', 'Shopify, Magento'],
            ['iPaaS', 'n8n, Make, Workato'],
            ['Agent Platforms', 'Axiom AI, Composio, Relevance AI, Flowise'],
          ]}
        />
      </>
    ),
  },
  {
    id: 'browser-ext',
    title: 'Browser Extension',
    icon: GlobeAltIcon,
    content: (
      <>
        <P>
          The Membread browser extension captures conversations from AI chat interfaces and stores
          them in the knowledge graph automatically.
        </P>
        <H3>Supported Platforms</H3>
        <ul className="list-disc list-inside text-[13px] text-gray-600 mb-4 space-y-1">
          <li>ChatGPT (chat.openai.com)</li>
          <li>Claude (claude.ai)</li>
          <li>Gemini (gemini.google.com)</li>
          <li>Perplexity (perplexity.ai)</li>
          <li>Microsoft Copilot (copilot.microsoft.com)</li>
        </ul>
        <H3>Installation</H3>
        <CodeBlock language="text">{`
1. Open chrome://extensions in your browser
2. Toggle "Developer Mode" ON (top right)
3. Click "Load unpacked"
4. Select the browser_extension/ folder from the Membread repo
5. Click the extension icon in the toolbar
6. Set your Membread server URL (default: http://localhost:8000)
7. Enter your JWT token
        `}</CodeBlock>
        <H3>How It Works</H3>
        <P>
          The extension monitors supported AI chat pages using content scripts. When a conversation
          exchange is detected, it extracts the messages and submits them to the Membread API via
          <code className="text-[12px] bg-gray-100 px-1 py-0.5 rounded"> POST /api/capture</code>.
          Each captured exchange is stored as a memory node in the knowledge graph with full
          provenance (source, timestamp, agent identity).
        </P>
      </>
    ),
  },
  {
    id: 'auth',
    title: 'Authentication',
    icon: KeyIcon,
    content: (
      <>
        <P>
          Membread uses JWT-based authentication. All API endpoints except{' '}
          <code className="text-[12px] bg-gray-100 px-1 py-0.5 rounded">/health</code> and{' '}
          <code className="text-[12px] bg-gray-100 px-1 py-0.5 rounded">/api/auth/token</code>{' '}
          require a Bearer token.
        </P>
        <H3>Generate a Token</H3>
        <CodeBlock language="bash">{`
# Via API
curl -X POST http://localhost:8000/api/auth/token \\
  -H "Content-Type: application/json" \\
  -d '{"user_id": "user-1", "scope": "admin"}'

# Via script
python scripts/generate_token.py
        `}</CodeBlock>
        <H3>Using the Token</H3>
        <CodeBlock language="bash">{`
# Set as environment variable
export MEMBREAD_TOKEN="<your-jwt>"

# Or pass in the Authorization header
curl -H "Authorization: Bearer <token>" \\
  http://localhost:8000/api/memory/list
        `}</CodeBlock>
        <H3>Environment Variables</H3>
        <Table
          headers={['Variable', 'Description']}
          rows={[
            ['MEMBREAD_TOKEN', 'JWT token for API authentication'],
            ['MEMBREAD_API_KEY', 'API key for MCP server / SDK'],
            ['JWT_SECRET', 'Secret key for signing JWTs (default: dev-secret-key)'],
          ]}
        />
      </>
    ),
  },
  {
    id: 'config',
    title: 'Configuration',
    icon: Cog6ToothIcon,
    content: (
      <>
        <P>Membread is configured via environment variables. Copy <code className="text-[12px] bg-gray-100 px-1 py-0.5 rounded">.env.example</code> to <code className="text-[12px] bg-gray-100 px-1 py-0.5 rounded">.env</code> and customise.</P>
        <H3>Environment Variables</H3>
        <Table
          headers={['Variable', 'Description', 'Default']}
          rows={[
            ['OPENAI_API_KEY', 'OpenAI API key for embeddings & LLM', '—'],
            ['LOCAL_LLM_BASE_URL', 'Ollama / local LLM endpoint', '—'],
            ['LOCAL_LLM_MODEL', 'Local LLM model name', 'llama3'],
            ['LOCAL_EMBEDDING_MODEL', 'Local embedding model', 'nomic-embed-text'],
            ['GRAPHITI_BACKEND', 'Graph DB backend', 'memory'],
            ['GRAPHITI_URI', 'Graph DB connection URI', 'bolt://localhost:7687'],
            ['ENABLE_TEMPORAL', 'Enable bi-temporal knowledge graph', 'true'],
            ['DATABASE_URL', 'PostgreSQL connection string', 'postgresql://...'],
            ['JWT_SECRET', 'JWT signing secret', 'dev-secret-key'],
            ['MAX_CONTEXT_TOKENS', 'Token limit for context compression', '2000'],
            ['MEMBREAD_API_URL', 'API URL for SDK / MCP', 'http://localhost:8000'],
            ['MEMBREAD_API_KEY', 'API key for SDK / MCP', '—'],
          ]}
        />
        <H3>Docker Compose</H3>
        <CodeBlock language="bash">{`
# Default: PostgreSQL + FalkorDB
docker compose up -d

# With local LLM (Ollama)
docker compose --profile local-llm up -d

# Watch logs
docker compose logs -f membread
        `}</CodeBlock>
        <H3>Graph Backend Options</H3>
        <Table
          headers={['Backend', 'GRAPHITI_BACKEND', 'Notes']}
          rows={[
            ['In-memory', 'memory', 'Default. No external DB needed. Data lost on restart.'],
            ['FalkorDB', 'falkordb', 'Production-ready. Included in docker-compose.'],
            ['Neo4j', 'neo4j', 'Requires separate Neo4j instance.'],
            ['Kùzu', 'kuzu', 'Embedded graph DB. No separate server needed.'],
          ]}
        />
      </>
    ),
  },
  {
    id: 'testing',
    title: 'Testing',
    icon: BeakerIcon,
    content: (
      <>
        <CodeBlock language="bash">{`
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# With coverage report
pytest --cov=src --cov-report=html

# Individual test suites
pytest tests/test_graphiti_engine.py -v
pytest tests/test_endpoints.py -v
pytest tests/test_benchmark.py -v
        `}</CodeBlock>
        <H3>Benchmark</H3>
        <P>
          LoCoMo benchmark evaluating temporal, multi-hop, point-in-time, and factual reasoning:
        </P>
        <CodeBlock language="bash">{`
python -m benchmarks.run
python -m benchmarks.run --markdown   # GitHub-flavoured output
        `}</CodeBlock>
      </>
    ),
  },
  {
    id: 'contributing',
    title: 'Contributing',
    icon: CommandLineIcon,
    content: (
      <>
        <P>Contributions are welcome! Here's how to get started:</P>
        <H3>Development Setup</H3>
        <CodeBlock language="bash">{`
# Fork and clone
git clone https://github.com/<your-username>/membread.git
cd membread

# Install with dev dependencies
pip install -e ".[dev]"

# Frontend
cd frontend && npm install && cd ..

# Run tests to verify
pytest
        `}</CodeBlock>
        <H3>Workflow</H3>
        <ol className="list-decimal list-inside text-[13px] text-gray-600 mb-4 space-y-1">
          <li>Create a feature branch: <code className="text-[12px] bg-gray-100 px-1 py-0.5 rounded">git checkout -b feat/my-feature</code></li>
          <li>Make your changes with tests</li>
          <li>Run <code className="text-[12px] bg-gray-100 px-1 py-0.5 rounded">pytest</code> and ensure all tests pass</li>
          <li>Commit with conventional commit messages</li>
          <li>Open a Pull Request against <code className="text-[12px] bg-gray-100 px-1 py-0.5 rounded">main</code></li>
        </ol>
        <H3>Adding a New Connector</H3>
        <ol className="list-decimal list-inside text-[13px] text-gray-600 mb-4 space-y-1">
          <li>Add the connector entry in <code className="text-[12px] bg-gray-100 px-1 py-0.5 rounded">server.py</code> CONNECTORS list</li>
          <li>If webhook-based, add a parser function</li>
          <li>Add an icon mapping in ConnectorsPage.tsx CONNECTOR_ICONS</li>
          <li>Add a color mapping in ConnectorsPage.tsx CONNECTOR_COLORS</li>
          <li>Submit a PR with a description of the new connector</li>
        </ol>
        <H3>Code Style</H3>
        <ul className="list-disc list-inside text-[13px] text-gray-600 mb-4 space-y-1">
          <li>Python: Follow PEP 8, type hints everywhere</li>
          <li>TypeScript: Strict mode, functional components with hooks</li>
          <li>Commit format: <code className="text-[12px] bg-gray-100 px-1 py-0.5 rounded">feat:</code>, <code className="text-[12px] bg-gray-100 px-1 py-0.5 rounded">fix:</code>, <code className="text-[12px] bg-gray-100 px-1 py-0.5 rounded">docs:</code>, <code className="text-[12px] bg-gray-100 px-1 py-0.5 rounded">refactor:</code></li>
        </ul>
      </>
    ),
  },
];

/* ── Page Component ────────────────────────────────────────────────── */

const DocsPage: React.FC = () => {
  const [activeSection, setActiveSection] = useState('overview');

  const currentSection = sections.find((s) => s.id === activeSection) || sections[0];

  return (
    <div className="max-w-6xl mx-auto">
      {/* Page header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Documentation</h1>
        <p className="text-sm text-gray-500 mt-1">
          Everything you need to set up, configure, and extend Membread.
        </p>
      </div>

      <div className="flex gap-8">
        {/* Sidebar navigation */}
        <nav className="w-52 shrink-0">
          <div className="sticky top-24 space-y-0.5">
            {sections.map((section) => {
              const active = section.id === activeSection;
              return (
                <button
                  key={section.id}
                  onClick={() => setActiveSection(section.id)}
                  className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium transition-all duration-150 text-left ${
                    active
                      ? 'bg-gray-900 text-white'
                      : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  <section.icon className={`w-4 h-4 shrink-0 ${active ? 'text-gray-300' : 'text-gray-400'}`} />
                  {section.title}
                </button>
              );
            })}
          </div>
        </nav>

        {/* Content */}
        <article className="flex-1 min-w-0 bg-white border border-gray-200/80 rounded-2xl p-8">
          <div className="flex items-center gap-3 mb-6 pb-4 border-b border-gray-100">
            <div className="w-10 h-10 rounded-xl bg-gray-900 flex items-center justify-center">
              <currentSection.icon className="w-5 h-5 text-white" />
            </div>
            <h2 className="text-xl font-bold text-gray-900">{currentSection.title}</h2>
          </div>
          {currentSection.content}
        </article>
      </div>
    </div>
  );
};

export default DocsPage;
