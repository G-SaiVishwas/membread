import React, { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  PlusIcon,
  CheckCircleIcon,
  GlobeAltIcon,
  ChatBubbleLeftRightIcon,
  CodeBracketIcon,
  CommandLineIcon,
  CpuChipIcon,
  SparklesIcon,
  PhoneIcon,
  WrenchScrewdriverIcon,
  ArrowPathIcon,
  SignalIcon,
  ClipboardDocumentIcon,
  ExclamationTriangleIcon,
  BoltIcon,
  BuildingOfficeIcon,
  BuildingStorefrontIcon,
  ChatBubbleOvalLeftEllipsisIcon,
  CircleStackIcon,
  CloudArrowUpIcon,
  CogIcon,
  CurrencyDollarIcon,
  DocumentTextIcon,
  IdentificationIcon,
  InboxStackIcon,
  KeyIcon,
  LinkIcon,
  MegaphoneIcon,
  PresentationChartLineIcon,
  ScaleIcon,
  ServerIcon,
  ShieldCheckIcon,
  ShoppingCartIcon,
  TruckIcon,
  UserGroupIcon,
  UsersIcon,
  XMarkIcon,
  ClipboardDocumentCheckIcon,
  ArrowTopRightOnSquareIcon,
  BookOpenIcon,
} from '@heroicons/react/24/outline';
import { useApi } from '../api/client';

/* ── Types ─────────────────────────────────────────────────────────── */

interface Connector {
  id: string;
  name: string;
  description: string;
  category: string;
  method: string;
  status: 'connected' | 'disconnected' | 'pending_oauth';
  last_sync: string | null;
  memories_captured: number;
  connected_at: string | null;
  auth_method?: 'oauth' | 'api_key' | 'webhook' | 'external';
  has_provider?: boolean;
}

/* ── Icon + style maps ─────────────────────────────────────────────── */

const CONNECTOR_ICONS: Record<string, React.FC<{ className?: string }>> = {
  // Browser Extension
  chatgpt: SparklesIcon,
  'claude-web': ChatBubbleLeftRightIcon,
  gemini: SparklesIcon,
  perplexity: GlobeAltIcon,
  'ms-copilot': CpuChipIcon,
  // MCP Native
  'claude-code': CommandLineIcon,
  cursor: CommandLineIcon,
  windsurf: CommandLineIcon,
  'vscode-copilot': CodeBracketIcon,
  // Voice AI
  vapi: PhoneIcon,
  retell: PhoneIcon,
  bland: PhoneIcon,
  // SDK
  langchain: WrenchScrewdriverIcon,
  crewai: WrenchScrewdriverIcon,
  autogen: WrenchScrewdriverIcon,
  'openai-sdk': SparklesIcon,
  // Marketing
  zapier: BoltIcon,
  hubspot: MegaphoneIcon,
  marketo: PresentationChartLineIcon,
  // Sales
  salesforce: CloudArrowUpIcon,
  outreach: InboxStackIcon,
  salesloft: ChatBubbleOvalLeftEllipsisIcon,
  // Support
  intercom: ChatBubbleOvalLeftEllipsisIcon,
  zendesk: InboxStackIcon,
  freshdesk: InboxStackIcon,
  'twilio-flex': PhoneIcon,
  // Finance / RPA
  uipath: CogIcon,
  'automation-anywhere': CogIcon,
  // HR
  workday: UsersIcon,
  greenhouse: UserGroupIcon,
  lever: IdentificationIcon,
  // DevOps
  servicenow: ServerIcon,
  pagerduty: ShieldCheckIcon,
  // Supply Chain
  sap: TruckIcon,
  'oracle-scm': CircleStackIcon,
  coupa: CurrencyDollarIcon,
  // Legal
  ironclad: ScaleIcon,
  'docusign-clm': DocumentTextIcon,
  // E-commerce
  shopify: ShoppingCartIcon,
  magento: BuildingStorefrontIcon,
  // iPaaS
  n8n: LinkIcon,
  make: LinkIcon,
  workato: LinkIcon,
  // Agent Platforms
  'axiom-ai': GlobeAltIcon,
  composio: BuildingOfficeIcon,
  'relevance-ai': SparklesIcon,
  flowise: BoltIcon,
};

const CONNECTOR_COLORS: Record<string, { text: string; bg: string }> = {
  // Browser Extension
  chatgpt: { text: 'text-emerald-600', bg: 'bg-emerald-50' },
  'claude-web': { text: 'text-orange-600', bg: 'bg-orange-50' },
  gemini: { text: 'text-blue-600', bg: 'bg-blue-50' },
  perplexity: { text: 'text-cyan-600', bg: 'bg-cyan-50' },
  'ms-copilot': { text: 'text-sky-600', bg: 'bg-sky-50' },
  // MCP Native
  'claude-code': { text: 'text-orange-600', bg: 'bg-orange-50' },
  cursor: { text: 'text-violet-600', bg: 'bg-violet-50' },
  windsurf: { text: 'text-teal-600', bg: 'bg-teal-50' },
  'vscode-copilot': { text: 'text-gray-900', bg: 'bg-gray-100' },
  // Voice AI
  vapi: { text: 'text-indigo-600', bg: 'bg-indigo-50' },
  retell: { text: 'text-rose-600', bg: 'bg-rose-50' },
  bland: { text: 'text-amber-600', bg: 'bg-amber-50' },
  // SDK
  langchain: { text: 'text-green-600', bg: 'bg-green-50' },
  crewai: { text: 'text-purple-600', bg: 'bg-purple-50' },
  autogen: { text: 'text-blue-600', bg: 'bg-blue-50' },
  'openai-sdk': { text: 'text-emerald-600', bg: 'bg-emerald-50' },
  // Marketing
  zapier: { text: 'text-orange-500', bg: 'bg-orange-50' },
  hubspot: { text: 'text-orange-600', bg: 'bg-orange-50' },
  marketo: { text: 'text-purple-600', bg: 'bg-purple-50' },
  // Sales
  salesforce: { text: 'text-blue-500', bg: 'bg-blue-50' },
  outreach: { text: 'text-violet-600', bg: 'bg-violet-50' },
  salesloft: { text: 'text-blue-600', bg: 'bg-blue-50' },
  // Support
  intercom: { text: 'text-blue-500', bg: 'bg-blue-50' },
  zendesk: { text: 'text-green-600', bg: 'bg-green-50' },
  freshdesk: { text: 'text-emerald-600', bg: 'bg-emerald-50' },
  'twilio-flex': { text: 'text-red-500', bg: 'bg-red-50' },
  // Finance / RPA
  uipath: { text: 'text-orange-500', bg: 'bg-orange-50' },
  'automation-anywhere': { text: 'text-red-600', bg: 'bg-red-50' },
  // HR
  workday: { text: 'text-blue-700', bg: 'bg-blue-50' },
  greenhouse: { text: 'text-green-600', bg: 'bg-green-50' },
  lever: { text: 'text-teal-600', bg: 'bg-teal-50' },
  // DevOps
  servicenow: { text: 'text-green-700', bg: 'bg-green-50' },
  pagerduty: { text: 'text-emerald-600', bg: 'bg-emerald-50' },
  // Supply Chain
  sap: { text: 'text-sky-700', bg: 'bg-sky-50' },
  'oracle-scm': { text: 'text-red-600', bg: 'bg-red-50' },
  coupa: { text: 'text-blue-600', bg: 'bg-blue-50' },
  // Legal
  ironclad: { text: 'text-indigo-600', bg: 'bg-indigo-50' },
  'docusign-clm': { text: 'text-yellow-600', bg: 'bg-yellow-50' },
  // E-commerce
  shopify: { text: 'text-green-500', bg: 'bg-green-50' },
  magento: { text: 'text-orange-600', bg: 'bg-orange-50' },
  // iPaaS
  n8n: { text: 'text-rose-500', bg: 'bg-rose-50' },
  make: { text: 'text-violet-500', bg: 'bg-violet-50' },
  workato: { text: 'text-fuchsia-600', bg: 'bg-fuchsia-50' },
  // Agent Platforms
  'axiom-ai': { text: 'text-amber-600', bg: 'bg-amber-50' },
  composio: { text: 'text-indigo-500', bg: 'bg-indigo-50' },
  'relevance-ai': { text: 'text-cyan-600', bg: 'bg-cyan-50' },
  flowise: { text: 'text-lime-600', bg: 'bg-lime-50' },
};

const CATEGORY_LABELS: Record<string, string> = {
  'browser-extension': 'Browser Extension',
  'mcp-native': 'MCP Native',
  'voice-ai': 'Voice AI',
  sdk: 'Agent SDK',
  marketing: 'Marketing',
  sales: 'Sales',
  support: 'Support',
  finance: 'Finance & RPA',
  hr: 'HR & Recruiting',
  devops: 'DevOps & ITSM',
  'supply-chain': 'Supply Chain',
  legal: 'Legal & Compliance',
  ecommerce: 'E-commerce',
  ipaas: 'iPaaS',
  'agent-platform': 'Agent Platforms',
};

const CATEGORY_ORDER = [
  'browser-extension', 'mcp-native', 'voice-ai', 'sdk',
  'marketing', 'sales', 'support', 'finance', 'hr',
  'devops', 'supply-chain', 'legal', 'ecommerce',
  'ipaas', 'agent-platform',
];

const METHOD_LABELS: Record<string, { label: string; color: string }> = {
  'browser-extension': { label: 'Extension', color: 'bg-blue-100 text-blue-700' },
  mcp: { label: 'MCP', color: 'bg-violet-100 text-violet-700' },
  webhook: { label: 'Webhook', color: 'bg-amber-100 text-amber-700' },
  sdk: { label: 'SDK', color: 'bg-green-100 text-green-700' },
};

/* ── Setup instructions for each method ──────────────────────────── */

const SETUP_INSTRUCTIONS: Record<string, string> = {
  'browser-extension': 'Load the Membread browser extension from the browser_extension/ folder, then enable this connector.',
  mcp: 'Add the Membread MCP server to your tool\'s config. See docs for setup.',
  webhook: 'Configure the webhook URL in your app\'s settings: POST /api/webhooks/{connector_id}',
  sdk: 'pip install -e ./sdk — then wrap your agent with the Membread callback.',
};

/* ── Per-connector detailed setup config ─────────────────────────── */

interface SetupStep {
  title: string;
  description: string;
  code?: string;
  link?: { url: string; label: string };
}

interface ConnectorSetup {
  title: string;
  subtitle: string;
  steps: SetupStep[];
  docsUrl?: string;
}

const CONNECTOR_SETUP: Record<string, ConnectorSetup> = {
  // ── Browser Extensions ──────────────────────────────────────────
  chatgpt: {
    title: 'Connect ChatGPT',
    subtitle: 'Capture your ChatGPT conversations automatically via the browser extension.',
    steps: [
      { title: 'Load the extension', description: 'Open chrome://extensions, enable Developer Mode, click "Load unpacked" and select the browser_extension/ folder from this project.' },
      { title: 'Configure the server URL', description: 'Click the extension icon and set your Membread server URL (default: http://localhost:8000).' },
      { title: 'Enable ChatGPT capture', description: 'Toggle on "ChatGPT" in the extension settings. Conversations will be captured automatically.' },
      { title: 'Verify', description: 'Start a ChatGPT conversation — you should see it appear in your Membread timeline within a few seconds.' },
    ],
  },
  'claude-web': {
    title: 'Connect Claude',
    subtitle: 'Capture your Claude conversations automatically via the browser extension.',
    steps: [
      { title: 'Load the extension', description: 'Open chrome://extensions, enable Developer Mode, click "Load unpacked" and select the browser_extension/ folder.' },
      { title: 'Configure the server URL', description: 'Click the extension icon and set your Membread server URL (default: http://localhost:8000).' },
      { title: 'Enable Claude capture', description: 'Toggle on "Claude" in the extension settings.' },
      { title: 'Verify', description: 'Start a Claude conversation and check your Membread timeline.' },
    ],
  },
  gemini: {
    title: 'Connect Gemini',
    subtitle: 'Capture your Google Gemini conversations via browser extension.',
    steps: [
      { title: 'Load the extension', description: 'Open chrome://extensions, enable Developer Mode, click "Load unpacked" and select the browser_extension/ folder.' },
      { title: 'Enable Gemini capture', description: 'Toggle on "Gemini" in the extension settings.' },
    ],
  },
  perplexity: {
    title: 'Connect Perplexity',
    subtitle: 'Capture your Perplexity research queries and answers via browser extension.',
    steps: [
      { title: 'Load the extension', description: 'Open chrome://extensions, enable Developer Mode, click "Load unpacked" and select the browser_extension/ folder.' },
      { title: 'Enable Perplexity capture', description: 'Toggle on "Perplexity" in the extension settings.' },
    ],
  },
  'ms-copilot': {
    title: 'Connect Microsoft Copilot',
    subtitle: 'Capture your Microsoft Copilot conversations via browser extension.',
    steps: [
      { title: 'Load the extension', description: 'Open chrome://extensions, enable Developer Mode, click "Load unpacked" and select the browser_extension/ folder.' },
      { title: 'Enable Copilot capture', description: 'Toggle on "Microsoft Copilot" in the extension settings.' },
    ],
  },
  // ── MCP Native ──────────────────────────────────────────────────
  'claude-code': {
    title: 'Connect Claude Code',
    subtitle: 'Add Membread as an MCP server to give Claude Code persistent memory across sessions.',
    steps: [
      { title: 'Open your Claude Code MCP config', description: 'Edit your Claude Code MCP configuration file (usually ~/.claude/mcp_servers.json).' },
      { title: 'Add the Membread MCP server', description: 'Add the following entry to your MCP servers configuration:', code: `{
  "membread": {
    "command": "python",
    "args": ["-m", "src.mcp_server.server"],
    "cwd": "<path-to-membread>",
    "env": {
      "MEMBREAD_API_URL": "http://localhost:8000",
      "MEMBREAD_API_KEY": "<your-api-key>"
    }
  }
}` },
      { title: 'Restart Claude Code', description: 'Restart your Claude Code session. You should see "membread" listed as an available MCP server.' },
      { title: 'Test it', description: 'Ask Claude Code to "remember" something, then start a new session and ask it to recall.' },
    ],
    docsUrl: '/docs/mcp-setup',
  },
  cursor: {
    title: 'Connect Cursor',
    subtitle: 'Add Membread as an MCP server to give Cursor persistent memory.',
    steps: [
      { title: 'Open Cursor Settings', description: 'Go to Cursor → Settings → MCP Servers.' },
      { title: 'Add Membread MCP server', description: 'Click "Add MCP Server" and enter the following configuration:', code: `{
  "name": "membread",
  "command": "python",
  "args": ["-m", "src.mcp_server.server"],
  "cwd": "<path-to-membread>",
  "env": {
    "MEMBREAD_API_URL": "http://localhost:8000",
    "MEMBREAD_API_KEY": "<your-api-key>"
  }
}` },
      { title: 'Verify', description: 'Open a new Cursor chat — Membread should appear as an available tool.' },
    ],
    docsUrl: '/docs/mcp-setup',
  },
  windsurf: {
    title: 'Connect Windsurf',
    subtitle: 'Add Membread as an MCP server to give Windsurf persistent memory.',
    steps: [
      { title: 'Open Windsurf MCP config', description: 'Edit your Windsurf MCP configuration file.' },
      { title: 'Add Membread', description: 'Add the Membread MCP server entry:', code: `{
  "membread": {
    "command": "python",
    "args": ["-m", "src.mcp_server.server"],
    "cwd": "<path-to-membread>",
    "env": {
      "MEMBREAD_API_URL": "http://localhost:8000",
      "MEMBREAD_API_KEY": "<your-api-key>"
    }
  }
}` },
      { title: 'Restart Windsurf', description: 'Restart your Windsurf session to load the MCP server.' },
    ],
    docsUrl: '/docs/mcp-setup',
  },
  'vscode-copilot': {
    title: 'Connect VS Code + Copilot',
    subtitle: 'Add Membread as an MCP server in VS Code to give GitHub Copilot persistent memory.',
    steps: [
      { title: 'Open VS Code Settings', description: 'Open your VS Code settings.json (Ctrl+Shift+P → "Open User Settings JSON").' },
      { title: 'Add MCP server config', description: 'Add the following to your settings.json:', code: `"mcp": {
  "servers": {
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
}` },
      { title: 'Verify', description: 'Open Copilot Chat in VS Code — Membread tools should be available.' },
    ],
    docsUrl: '/docs/mcp-setup',
  },
  // ── Voice AI (Webhook) ──────────────────────────────────────────
  vapi: {
    title: 'Connect Vapi',
    subtitle: 'Capture voice call transcripts from Vapi via webhook.',
    steps: [
      { title: 'Go to Vapi Dashboard', description: 'Open your Vapi dashboard and navigate to Settings → Webhooks.', link: { url: 'https://dashboard.vapi.ai', label: 'Vapi Dashboard' } },
      { title: 'Add webhook URL', description: 'Set your webhook endpoint URL to:', code: `${window.location.protocol}//${window.location.hostname}:8000/api/webhooks/vapi` },
      { title: 'Select events', description: 'Enable the "call.completed" and "transcript.ready" event types.' },
      { title: 'Save & test', description: 'Save the webhook config, then make a test call. The transcript should appear in your Membread timeline.' },
    ],
  },
  retell: {
    title: 'Connect Retell AI',
    subtitle: 'Capture voice agent transcripts from Retell via webhook.',
    steps: [
      { title: 'Go to Retell Dashboard', description: 'Open Retell AI dashboard → Settings → Webhooks.', link: { url: 'https://app.retellai.com', label: 'Retell Dashboard' } },
      { title: 'Add webhook URL', description: 'Set webhook endpoint to:', code: `${window.location.protocol}//${window.location.hostname}:8000/api/webhooks/retell` },
      { title: 'Save & test', description: 'Make a test call and verify the transcript appears in Membread.' },
    ],
  },
  bland: {
    title: 'Connect Bland AI',
    subtitle: 'Capture voice call data from Bland AI via webhook.',
    steps: [
      { title: 'Go to Bland Dashboard', description: 'Open your Bland AI dashboard → Webhooks.', link: { url: 'https://app.bland.ai', label: 'Bland Dashboard' } },
      { title: 'Add webhook URL', description: 'Set webhook endpoint to:', code: `${window.location.protocol}//${window.location.hostname}:8000/api/webhooks/bland` },
      { title: 'Save & test', description: 'Make a test call and verify it appears in Membread.' },
    ],
  },
  // ── SDK ─────────────────────────────────────────────────────────
  langchain: {
    title: 'Connect LangChain',
    subtitle: 'Add Membread memory to your LangChain agents.',
    steps: [
      { title: 'Install the SDK', description: 'Install the Membread Python SDK:', code: 'pip install -e ./sdk' },
      { title: 'Add to your agent', description: 'Wrap your LangChain agent with the Membread callback:', code: `from membread import MembreadCallback

callback = MembreadCallback(
    api_url="http://localhost:8000",
    api_key="<your-api-key>"
)

agent = initialize_agent(
    tools, llm,
    callbacks=[callback]
)` },
      { title: 'Run your agent', description: 'Run your agent — all tool calls, observations, and outputs will be captured automatically.' },
    ],
    docsUrl: '/docs/sdk-python',
  },
  crewai: {
    title: 'Connect CrewAI',
    subtitle: 'Add Membread memory to your CrewAI agents.',
    steps: [
      { title: 'Install the SDK', description: 'Install the Membread Python SDK:', code: 'pip install -e ./sdk' },
      { title: 'Add to your crew', description: 'Add the Membread memory layer to your CrewAI setup:', code: `from membread import MembreadMemory

memory = MembreadMemory(
    api_url="http://localhost:8000",
    api_key="<your-api-key>"
)

crew = Crew(
    agents=[...],
    tasks=[...],
    memory=memory
)` },
    ],
    docsUrl: '/docs/sdk-python',
  },
  autogen: {
    title: 'Connect AutoGen',
    subtitle: 'Add Membread memory to your AutoGen agents.',
    steps: [
      { title: 'Install the SDK', description: 'Install the Membread Python SDK:', code: 'pip install -e ./sdk' },
      { title: 'Add the callback', description: 'Register Membread as a callback on your AutoGen agents:', code: `from membread import MembreadCallback

callback = MembreadCallback(
    api_url="http://localhost:8000",
    api_key="<your-api-key>"
)
# Register on your agents` },
    ],
    docsUrl: '/docs/sdk-python',
  },
  'openai-sdk': {
    title: 'Connect OpenAI SDK',
    subtitle: 'Capture OpenAI API calls and responses via the Membread SDK.',
    steps: [
      { title: 'Install the SDK', description: 'Install the Membread Python SDK:', code: 'pip install -e ./sdk' },
      { title: 'Wrap your client', description: 'Wrap the OpenAI client with Membread:', code: `from membread import wrap_openai
import openai

client = wrap_openai(
    openai.OpenAI(),
    api_url="http://localhost:8000",
    api_key="<your-api-key>"
)

# Use client as normal — all calls are captured
response = client.chat.completions.create(...)` },
    ],
    docsUrl: '/docs/sdk-python',
  },
  // ── Webhook-only enterprise connectors ──────────────────────────
  zapier: {
    title: 'Connect Zapier',
    subtitle: 'Send data from any Zapier workflow to Membread via webhook.',
    steps: [
      { title: 'Create a Zap', description: 'In Zapier, create a new Zap with your trigger app of choice.', link: { url: 'https://zapier.com/app/zaps', label: 'Zapier Dashboard' } },
      { title: 'Add Webhooks action', description: 'Add a "Webhooks by Zapier" action step. Choose "POST" as the method.' },
      { title: 'Configure the webhook', description: 'Set the webhook URL to:', code: `${window.location.protocol}//${window.location.hostname}:8000/api/webhooks/zapier` },
      { title: 'Set payload', description: 'Set the payload type to JSON and map your trigger data fields.' },
      { title: 'Test & enable', description: 'Test the Zap and turn it on. Data will flow into Membread automatically.' },
    ],
  },
};

/* ── Component ──────────────────────────────────────────────────── */

const ConnectorsPage: React.FC = () => {
  const api = useApi();
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>('all');
  const [togglingId, setTogglingId] = useState<string | null>(null);
  const [copiedWebhook, setCopiedWebhook] = useState<string | null>(null);

  // API Key modal state
  const [apiKeyModal, setApiKeyModal] = useState<{ connectorId: string; name: string } | null>(null);
  const [apiKeyValue, setApiKeyValue] = useState('');
  const [apiKeyConfig, setApiKeyConfig] = useState<Record<string, string>>({});
  const [apiKeySubmitting, setApiKeySubmitting] = useState(false);

  // OAuth credentials modal state
  const [credentialsModal, setCredentialsModal] = useState<{ providerId: string; name: string } | null>(null);
  const [credClientId, setCredClientId] = useState('');
  const [credClientSecret, setCredClientSecret] = useState('');
  const [credSubmitting, setCredSubmitting] = useState(false);

  // Polling state
  const [pollingId, setPollingId] = useState<string | null>(null);

  // Setup instructions modal state
  const [setupModal, setSetupModal] = useState<{
    connectorId: string;
    name: string;
    method: string;
    webhookUrl?: string;
  } | null>(null);
  const [setupConfirming, setSetupConfirming] = useState(false);
  const [copiedSetup, setCopiedSetup] = useState<string | null>(null);

  const oauthPopupRef = useRef<Window | null>(null);

  const fetchConnectors = useCallback(async () => {
    try {
      const res = await api.get('/api/connectors');
      setConnectors(res.data.connectors || []);
      setError(null);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load connectors');
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => {
    fetchConnectors();
  }, []);

  // Listen for OAuth callback redirect (popup posts message or URL has query param)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const connected = params.get('connected');
    if (connected) {
      // Remove query param and refresh
      window.history.replaceState({}, '', window.location.pathname);
      fetchConnectors();
    }

    const handleMessage = (ev: MessageEvent) => {
      if (ev.data?.type === 'oauth_complete') {
        fetchConnectors();
      }
    };
    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [fetchConnectors]);

  const handleConnect = async (connector: Connector) => {
    setTogglingId(connector.id);
    setError(null);
    try {
      const res = await api.post('/api/connectors/connect', { connector_id: connector.id });
      const data = res.data;

      if (data.status === 'requires_oauth') {
        // Start OAuth flow — get authorize URL
        try {
          const authRes = await api.get(`/api/oauth/${connector.id}/authorize`);
          const authorizeUrl = authRes.data.authorize_url;
          // Open OAuth popup
          const w = 600, h = 700;
          const left = window.screenX + (window.outerWidth - w) / 2;
          const top = window.screenY + (window.outerHeight - h) / 2;
          oauthPopupRef.current = window.open(
            authorizeUrl,
            `oauth_${connector.id}`,
            `width=${w},height=${h},left=${left},top=${top},toolbar=no,menubar=no`
          );
          // Poll for popup close
          const pollTimer = setInterval(() => {
            if (oauthPopupRef.current?.closed) {
              clearInterval(pollTimer);
              oauthPopupRef.current = null;
              fetchConnectors();
            }
          }, 1000);
        } catch (authErr: any) {
          const detail = authErr?.response?.data?.detail || '';
          if (detail.includes('credentials not configured')) {
            // Need to set up OAuth credentials first
            setCredentialsModal({ providerId: connector.id, name: connector.name });
          } else {
            setError(detail || 'Failed to start OAuth flow');
          }
        }
      } else if (data.status === 'requires_api_key') {
        // Show API key input modal
        setApiKeyModal({ connectorId: connector.id, name: connector.name });
        setApiKeyValue('');
        setApiKeyConfig({});
      } else if (data.status === 'requires_setup') {
        // Show setup instructions modal
        setSetupModal({
          connectorId: connector.id,
          name: connector.name,
          method: data.method || connector.method,
          webhookUrl: data.webhook_url,
        });
      } else {
        // Immediate activation
        await fetchConnectors();
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Connection failed');
    } finally {
      setTogglingId(null);
    }
  };

  const handleDisconnect = async (connector: Connector) => {
    setTogglingId(connector.id);
    try {
      await api.post('/api/connectors/disconnect', { connector_id: connector.id });
      await fetchConnectors();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Disconnect failed');
    } finally {
      setTogglingId(null);
    }
  };

  const handleToggle = async (connector: Connector) => {
    if (connector.status === 'connected') {
      await handleDisconnect(connector);
    } else {
      await handleConnect(connector);
    }
  };

  const handleApiKeySubmit = async () => {
    if (!apiKeyModal || !apiKeyValue.trim()) return;
    setApiKeySubmitting(true);
    try {
      await api.post('/api/connectors/api-key', {
        connector_id: apiKeyModal.connectorId,
        api_key: apiKeyValue.trim(),
        config: apiKeyConfig,
      });
      setApiKeyModal(null);
      setApiKeyValue('');
      setApiKeyConfig({});
      await fetchConnectors();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'API key connection failed');
    } finally {
      setApiKeySubmitting(false);
    }
  };

  const handleCredentialsSubmit = async () => {
    if (!credentialsModal || !credClientId.trim() || !credClientSecret.trim()) return;
    setCredSubmitting(true);
    try {
      await api.post('/api/connectors/credentials', {
        provider_id: credentialsModal.providerId,
        client_id: credClientId.trim(),
        client_secret: credClientSecret.trim(),
      });
      setCredentialsModal(null);
      setCredClientId('');
      setCredClientSecret('');
      // Now retry the OAuth flow
      const connector = connectors.find(c => c.id === credentialsModal.providerId);
      if (connector) {
        await handleConnect(connector);
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to save credentials');
    } finally {
      setCredSubmitting(false);
    }
  };

  const handleManualPoll = async (connectorId: string) => {
    setPollingId(connectorId);
    try {
      const res = await api.post(`/api/connectors/${connectorId}/poll`);
      const count = res.data.memories_captured || 0;
      if (count > 0) {
        setError(null);
      }
      await fetchConnectors();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Poll failed');
    } finally {
      setPollingId(null);
    }
  };

  const handleSetupConfirm = async () => {
    if (!setupModal) return;
    setSetupConfirming(true);
    try {
      await api.post('/api/connectors/confirm', { connector_id: setupModal.connectorId });
      setSetupModal(null);
      await fetchConnectors();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to confirm setup');
    } finally {
      setSetupConfirming(false);
    }
  };

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedSetup(key);
    setTimeout(() => setCopiedSetup(null), 2000);
  };

  const copyWebhookUrl = (connectorId: string) => {
    const url = `${window.location.protocol}//${window.location.hostname}:8000/api/webhooks/${connectorId}`;
    navigator.clipboard.writeText(url);
    setCopiedWebhook(connectorId);
    setTimeout(() => setCopiedWebhook(null), 2000);
  };

  const filtered = filter === 'all'
    ? connectors
    : connectors.filter((c) => c.category === filter);

  const categories = CATEGORY_ORDER.filter((cat) =>
    filtered.some((c) => c.category === cat)
  );

  const connectedCount = connectors.filter((c) => c.status === 'connected').length;
  const totalMemories = connectors.reduce((sum, c) => sum + c.memories_captured, 0);

  const formatTime = (ts: string | null) => {
    if (!ts) return null;
    const d = new Date(ts);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return 'just now';
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHr = Math.floor(diffMin / 60);
    if (diffHr < 24) return `${diffHr}h ago`;
    return `${Math.floor(diffHr / 24)}d ago`;
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto flex items-center justify-center h-64">
        <ArrowPathIcon className="w-6 h-6 text-gray-400 animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-6"
      >
        <div className="flex items-center gap-3 mb-1">
          <GlobeAltIcon className="w-6 h-6 text-gray-900" />
          <h1 className="text-2xl font-extrabold text-gray-900 tracking-tight">
            Connectors
          </h1>
        </div>
        <p className="text-sm text-gray-400 ml-9">
          Connect AI tools to{' '}
          <strong className="text-gray-600">capture memory into one central knowledge base</strong>{' '}
          accessible from everywhere.
        </p>
      </motion.div>

      {/* Filter tabs */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.05 }}
        className="flex gap-1 p-1 bg-black/[0.03] border border-black/[0.06] rounded-xl mb-6 overflow-x-auto scrollbar-hide"
      >
        {[
          { id: 'all', label: 'All' },
          { id: 'browser-extension', label: 'Extensions' },
          { id: 'mcp-native', label: 'MCP' },
          { id: 'voice-ai', label: 'Voice AI' },
          { id: 'sdk', label: 'SDK' },
          { id: 'marketing', label: 'Marketing' },
          { id: 'sales', label: 'Sales' },
          { id: 'support', label: 'Support' },
          { id: 'finance', label: 'Finance' },
          { id: 'hr', label: 'HR' },
          { id: 'devops', label: 'DevOps' },
          { id: 'supply-chain', label: 'Supply Chain' },
          { id: 'legal', label: 'Legal' },
          { id: 'ecommerce', label: 'E-commerce' },
          { id: 'ipaas', label: 'iPaaS' },
          { id: 'agent-platform', label: 'Agents' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setFilter(tab.id)}
            className={`px-4 py-1.5 rounded-lg text-[12px] font-semibold whitespace-nowrap shrink-0 transition-all duration-200 ${
              filter === tab.id
                ? 'bg-black text-white shadow-sm'
                : 'text-gray-500 hover:text-gray-900'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </motion.div>

      {/* Error banner */}
      {error && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="mb-4 flex items-center gap-2 px-3 py-2 bg-red-50 border border-red-200 rounded-xl"
        >
          <ExclamationTriangleIcon className="w-4 h-4 text-red-500" />
          <span className="text-sm text-red-700 font-medium">{error}</span>
          <button
            onClick={() => setError(null)}
            className="ml-auto text-xs text-red-400 hover:text-red-600"
          >
            Dismiss
          </button>
        </motion.div>
      )}

      {/* Summary stats */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.1 }}
        className="mb-6 flex items-center gap-4"
      >
        <div className={`flex items-center gap-2 px-3 py-2 rounded-xl border ${connectedCount > 0 ? 'bg-emerald-50 border-emerald-200' : 'bg-black/[0.02] border-black/[0.06]'}`}>
          {connectedCount > 0 ? (
            <SignalIcon className="w-4 h-4 text-emerald-500 animate-pulse" />
          ) : (
            <SignalIcon className="w-4 h-4 text-gray-400" />
          )}
          <span className={`text-sm font-semibold ${connectedCount > 0 ? 'text-emerald-700' : 'text-gray-500'}`}>
            {connectedCount} active
          </span>
        </div>
        {totalMemories > 0 && (
          <div className="flex items-center gap-2 px-3 py-2 bg-black/[0.02] border border-black/[0.06] rounded-xl">
            <span className="text-sm text-gray-500">{totalMemories.toLocaleString()} memories captured</span>
          </div>
        )}
        <button
          onClick={fetchConnectors}
          className="ml-auto flex items-center gap-1 px-3 py-2 text-[12px] font-medium text-gray-500 hover:text-gray-900 transition-colors"
        >
          <ArrowPathIcon className="w-3.5 h-3.5" />
          Refresh
        </button>
      </motion.div>

      {/* Connector list grouped by category */}
      <div className="space-y-6">
        {categories.map((cat, ci) => (
          <motion.div
            key={cat}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.08 * ci }}
          >
            <div className="flex items-center gap-2 mb-3 ml-1">
              <h2 className="text-[11px] font-bold text-gray-400 uppercase tracking-wider">
                {CATEGORY_LABELS[cat]}
              </h2>
              <span className="text-[10px] text-gray-300 font-medium">
                {SETUP_INSTRUCTIONS[filtered.find((c) => c.category === cat)?.method || ''] || ''}
              </span>
            </div>
            <div className="bg-white border border-black/[0.06] rounded-2xl overflow-hidden divide-y divide-black/[0.04]">
              {filtered
                .filter((c) => c.category === cat)
                .map((connector) => {
                  const isConnected = connector.status === 'connected';
                  const isPending = connector.status === 'pending_oauth';
                  const isToggling = togglingId === connector.id;
                  const isPolling = pollingId === connector.id;
                  const Icon = CONNECTOR_ICONS[connector.id] || CpuChipIcon;
                  const colors = CONNECTOR_COLORS[connector.id] || { text: 'text-gray-600', bg: 'bg-gray-100' };
                  const methodInfo = METHOD_LABELS[connector.method];
                  const lastSync = formatTime(connector.last_sync);

                  // Auth method badge
                  const authBadge = connector.auth_method === 'oauth'
                    ? { label: 'OAuth', color: 'bg-blue-100 text-blue-700' }
                    : connector.auth_method === 'api_key'
                    ? { label: 'API Key', color: 'bg-yellow-100 text-yellow-700' }
                    : null;

                  return (
                    <div
                      key={connector.id}
                      className="flex items-center gap-4 px-5 py-4 hover:bg-black/[0.015] transition-colors group"
                    >
                      {/* Icon */}
                      <div className={`w-10 h-10 rounded-xl ${colors.bg} border border-black/[0.04] flex items-center justify-center shrink-0 shadow-sm`}>
                        <Icon className={`w-5 h-5 ${colors.text}`} />
                      </div>

                      {/* Info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-[14px] font-semibold text-gray-900">
                            {connector.name}
                          </span>
                          {methodInfo && (
                            <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase ${methodInfo.color}`}>
                              {methodInfo.label}
                            </span>
                          )}
                          {authBadge && (
                            <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase ${authBadge.color}`}>
                              {authBadge.label}
                            </span>
                          )}
                        </div>
                        <p className="text-[12px] text-gray-400 mt-0.5 truncate">
                          {isPending
                            ? 'Waiting for OAuth authorization...'
                            : isConnected
                            ? `${connector.memories_captured} memories captured${lastSync ? ` · Last sync ${lastSync}` : ''}`
                            : connector.description}
                        </p>
                      </div>

                      {/* Webhook copy for voice-ai */}
                      {connector.method === 'webhook' && (
                        <button
                          onClick={() => copyWebhookUrl(connector.id)}
                          className="shrink-0 flex items-center gap-1 px-2 py-1.5 text-[10px] font-medium text-gray-400 hover:text-gray-700 bg-black/[0.03] rounded-lg transition-colors"
                          title="Copy webhook URL"
                        >
                          <ClipboardDocumentIcon className="w-3.5 h-3.5" />
                          {copiedWebhook === connector.id ? 'Copied!' : 'Webhook URL'}
                        </button>
                      )}

                      {/* Manual poll button for connected providers */}
                      {isConnected && connector.has_provider && (
                        <button
                          onClick={() => handleManualPoll(connector.id)}
                          disabled={isPolling}
                          className="shrink-0 flex items-center gap-1 px-2 py-1.5 text-[10px] font-medium text-gray-400 hover:text-gray-700 bg-black/[0.03] rounded-lg transition-colors disabled:opacity-50"
                          title="Poll now"
                        >
                          <ArrowPathIcon className={`w-3.5 h-3.5 ${isPolling ? 'animate-spin' : ''}`} />
                          {isPolling ? 'Polling...' : 'Sync'}
                        </button>
                      )}

                      {/* Connect / Disconnect */}
                      <div className="shrink-0">
                        <AnimatePresence mode="wait">
                          {isConnected ? (
                            <motion.button
                              key="connected"
                              initial={{ scale: 0.9, opacity: 0 }}
                              animate={{ scale: 1, opacity: 1 }}
                              exit={{ scale: 0.9, opacity: 0 }}
                              onClick={() => handleToggle(connector)}
                              disabled={isToggling}
                              className="flex items-center gap-1.5 px-4 py-2 text-[12px] font-semibold text-emerald-600 bg-emerald-50 border border-emerald-200 rounded-xl hover:bg-red-50 hover:text-red-600 hover:border-red-200 transition-colors disabled:opacity-50"
                            >
                              {isToggling ? (
                                <ArrowPathIcon className="w-4 h-4 animate-spin" />
                              ) : (
                                <CheckCircleIcon className="w-4 h-4" />
                              )}
                              {isToggling ? 'Disconnecting...' : 'Connected'}
                            </motion.button>
                          ) : isPending ? (
                            <motion.button
                              key="pending"
                              initial={{ scale: 0.9, opacity: 0 }}
                              animate={{ scale: 1, opacity: 1 }}
                              exit={{ scale: 0.9, opacity: 0 }}
                              onClick={() => handleConnect(connector)}
                              className="flex items-center gap-1.5 px-4 py-2 text-[12px] font-semibold text-amber-600 bg-amber-50 border border-amber-200 rounded-xl hover:bg-amber-100 transition-colors"
                            >
                              <ArrowPathIcon className="w-3.5 h-3.5 animate-spin" />
                              Authorizing...
                            </motion.button>
                          ) : (
                            <motion.button
                              key="disconnected"
                              initial={{ scale: 0.9, opacity: 0 }}
                              animate={{ scale: 1, opacity: 1 }}
                              exit={{ scale: 0.9, opacity: 0 }}
                              onClick={() => handleToggle(connector)}
                              disabled={isToggling}
                              className="flex items-center gap-1.5 px-4 py-2 text-[12px] font-semibold text-gray-700 bg-white border border-black/[0.10] rounded-xl hover:bg-black hover:text-white hover:border-black transition-all duration-200 disabled:opacity-50"
                            >
                              {isToggling ? (
                                <ArrowPathIcon className="w-3.5 h-3.5 animate-spin" />
                              ) : (
                                <PlusIcon className="w-3.5 h-3.5" />
                              )}
                              {isToggling ? 'Connecting...' : 'Connect'}
                            </motion.button>
                          )}
                        </AnimatePresence>
                      </div>
                    </div>
                  );
                })}
            </div>
          </motion.div>
        ))}
      </div>

      {/* Bottom hint */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
        className="mt-8 text-center"
      >
        <p className="text-[11px] text-gray-400">
          All connectors feed into one central knowledge base.{' '}
          <a
            href="/demo"
            className="font-semibold text-gray-600 hover:text-gray-900 underline underline-offset-2"
          >
            View API docs
          </a>{' '}
          to build a custom connector.
        </p>
      </motion.div>

      {/* ── API Key Modal ─────────────────────────────────────────── */}
      <AnimatePresence>
        {apiKeyModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
            onClick={() => setApiKeyModal(null)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="bg-white rounded-2xl p-6 w-full max-w-md shadow-xl border border-black/[0.06]"
            >
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <KeyIcon className="w-5 h-5 text-gray-900" />
                  <h3 className="text-lg font-bold text-gray-900">Connect {apiKeyModal.name}</h3>
                </div>
                <button onClick={() => setApiKeyModal(null)} className="p-1 hover:bg-gray-100 rounded-lg">
                  <XMarkIcon className="w-5 h-5 text-gray-400" />
                </button>
              </div>
              <p className="text-sm text-gray-500 mb-4">
                Enter your API key to connect {apiKeyModal.name}. Your key is encrypted at rest.
              </p>
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-600 mb-1">API Key</label>
                  <input
                    type="password"
                    value={apiKeyValue}
                    onChange={(e) => setApiKeyValue(e.target.value)}
                    placeholder="Enter your API key..."
                    className="w-full px-3 py-2 text-sm border border-black/[0.10] rounded-xl focus:outline-none focus:ring-2 focus:ring-black/20"
                    autoFocus
                  />
                </div>
                {/* Optional config fields based on connector */}
                {['zendesk', 'servicenow', 'workday', 'freshdesk'].includes(apiKeyModal.connectorId) && (
                  <div>
                    <label className="block text-xs font-semibold text-gray-600 mb-1">
                      {apiKeyModal.connectorId === 'freshdesk' ? 'Domain' : 'Subdomain / Instance URL'}
                    </label>
                    <input
                      type="text"
                      value={apiKeyConfig.subdomain || ''}
                      onChange={(e) => setApiKeyConfig({ ...apiKeyConfig, subdomain: e.target.value })}
                      placeholder="e.g., yourcompany.zendesk.com"
                      className="w-full px-3 py-2 text-sm border border-black/[0.10] rounded-xl focus:outline-none focus:ring-2 focus:ring-black/20"
                    />
                  </div>
                )}
              </div>
              <div className="flex justify-end gap-2 mt-6">
                <button
                  onClick={() => setApiKeyModal(null)}
                  className="px-4 py-2 text-sm font-medium text-gray-500 hover:text-gray-700"
                >
                  Cancel
                </button>
                <button
                  onClick={handleApiKeySubmit}
                  disabled={!apiKeyValue.trim() || apiKeySubmitting}
                  className="px-5 py-2 text-sm font-semibold text-white bg-black rounded-xl hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {apiKeySubmitting ? 'Connecting...' : 'Connect'}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── OAuth Credentials Modal ───────────────────────────────── */}
      <AnimatePresence>
        {credentialsModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
            onClick={() => setCredentialsModal(null)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="bg-white rounded-2xl p-6 w-full max-w-md shadow-xl border border-black/[0.06]"
            >
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <ShieldCheckIcon className="w-5 h-5 text-gray-900" />
                  <h3 className="text-lg font-bold text-gray-900">Setup {credentialsModal.name}</h3>
                </div>
                <button onClick={() => setCredentialsModal(null)} className="p-1 hover:bg-gray-100 rounded-lg">
                  <XMarkIcon className="w-5 h-5 text-gray-400" />
                </button>
              </div>
              <p className="text-sm text-gray-500 mb-4">
                Enter your OAuth app credentials from the {credentialsModal.name} developer portal.
                These are saved securely and used to authenticate users.
              </p>
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-600 mb-1">Client ID</label>
                  <input
                    type="text"
                    value={credClientId}
                    onChange={(e) => setCredClientId(e.target.value)}
                    placeholder="OAuth Client ID"
                    className="w-full px-3 py-2 text-sm border border-black/[0.10] rounded-xl focus:outline-none focus:ring-2 focus:ring-black/20"
                    autoFocus
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-600 mb-1">Client Secret</label>
                  <input
                    type="password"
                    value={credClientSecret}
                    onChange={(e) => setCredClientSecret(e.target.value)}
                    placeholder="OAuth Client Secret"
                    className="w-full px-3 py-2 text-sm border border-black/[0.10] rounded-xl focus:outline-none focus:ring-2 focus:ring-black/20"
                  />
                </div>
              </div>
              <div className="flex justify-end gap-2 mt-6">
                <button
                  onClick={() => setCredentialsModal(null)}
                  className="px-4 py-2 text-sm font-medium text-gray-500 hover:text-gray-700"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCredentialsSubmit}
                  disabled={!credClientId.trim() || !credClientSecret.trim() || credSubmitting}
                  className="px-5 py-2 text-sm font-semibold text-white bg-black rounded-xl hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {credSubmitting ? 'Saving...' : 'Save & Connect'}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Setup Instructions Modal ──────────────────────────────── */}
      <AnimatePresence>
        {setupModal && (() => {
          const setup = CONNECTOR_SETUP[setupModal.connectorId];
          const fallbackSteps: SetupStep[] = setupModal.method === 'webhook'
            ? [
                { title: 'Configure webhook', description: `Add this webhook URL to your ${setupModal.name} settings:`, code: `${window.location.protocol}//${window.location.hostname}:8000${setupModal.webhookUrl || `/api/webhooks/${setupModal.connectorId}`}` },
                { title: 'Test it', description: `Trigger an event in ${setupModal.name} and verify it appears in your Membread timeline.` },
              ]
            : setupModal.method === 'mcp'
            ? [
                { title: 'Add MCP server config', description: `Add the Membread MCP server to your ${setupModal.name} configuration:`, code: `{
  "membread": {
    "command": "python",
    "args": ["-m", "src.mcp_server.server"],
    "cwd": "<path-to-membread>",
    "env": {
      "MEMBREAD_API_URL": "http://localhost:8000",
      "MEMBREAD_API_KEY": "<your-api-key>"
    }
  }
}` },
                { title: 'Restart your tool', description: `Restart ${setupModal.name} to load the MCP server.` },
              ]
            : setupModal.method === 'browser-extension'
            ? [
                { title: 'Load extension', description: 'Open chrome://extensions, enable Developer Mode, click "Load unpacked" and select the browser_extension/ folder from this project.' },
                { title: 'Enable connector', description: `Configure your server URL and toggle on "${setupModal.name}" in the extension settings.` },
              ]
            : setupModal.method === 'sdk'
            ? [
                { title: 'Install the SDK', description: 'Install the Membread Python SDK:', code: 'pip install -e ./sdk' },
                { title: 'Add to your code', description: `Wrap your ${setupModal.name} agent with the Membread callback. See docs for examples.` },
              ]
            : [
                { title: 'Follow setup docs', description: `Visit the Membread documentation for ${setupModal.name} setup instructions.` },
              ];

          const activeSetup = setup || {
            title: `Connect ${setupModal.name}`,
            subtitle: `Follow these steps to connect ${setupModal.name} to Membread.`,
            steps: fallbackSteps,
          };

          return (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4"
              onClick={() => setSetupModal(null)}
            >
              <motion.div
                initial={{ scale: 0.95, opacity: 0, y: 10 }}
                animate={{ scale: 1, opacity: 1, y: 0 }}
                exit={{ scale: 0.95, opacity: 0, y: 10 }}
                onClick={(e) => e.stopPropagation()}
                className="bg-white rounded-2xl w-full max-w-lg shadow-2xl border border-black/[0.06] max-h-[85vh] flex flex-col"
              >
                {/* Header */}
                <div className="px-6 pt-6 pb-4 border-b border-black/[0.06]">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      {(() => {
                        const Icon = CONNECTOR_ICONS[setupModal.connectorId] || CpuChipIcon;
                        const colors = CONNECTOR_COLORS[setupModal.connectorId] || { text: 'text-gray-600', bg: 'bg-gray-100' };
                        return (
                          <div className={`w-10 h-10 rounded-xl ${colors.bg} flex items-center justify-center`}>
                            <Icon className={`w-5 h-5 ${colors.text}`} />
                          </div>
                        );
                      })()}
                      <div>
                        <h3 className="text-lg font-bold text-gray-900">{activeSetup.title}</h3>
                        <p className="text-xs text-gray-400 mt-0.5">{activeSetup.subtitle}</p>
                      </div>
                    </div>
                    <button onClick={() => setSetupModal(null)} className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors">
                      <XMarkIcon className="w-5 h-5 text-gray-400" />
                    </button>
                  </div>
                </div>

                {/* Steps */}
                <div className="px-6 py-4 overflow-y-auto flex-1">
                  <div className="space-y-4">
                    {activeSetup.steps.map((step, idx) => (
                      <div key={idx} className="flex gap-3">
                        {/* Step number */}
                        <div className="shrink-0 w-7 h-7 rounded-full bg-black text-white flex items-center justify-center text-xs font-bold mt-0.5">
                          {idx + 1}
                        </div>
                        <div className="flex-1 min-w-0">
                          <h4 className="text-sm font-semibold text-gray-900">{step.title}</h4>
                          <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">{step.description}</p>
                          {step.code && (
                            <div className="mt-2 relative group">
                              <pre className="bg-gray-900 text-gray-100 text-[11px] p-3 rounded-xl overflow-x-auto font-mono leading-relaxed">
                                {step.code}
                              </pre>
                              <button
                                onClick={() => copyToClipboard(step.code!, `step-${idx}`)}
                                className="absolute top-2 right-2 p-1.5 bg-gray-700 hover:bg-gray-600 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity"
                                title="Copy to clipboard"
                              >
                                {copiedSetup === `step-${idx}` ? (
                                  <ClipboardDocumentCheckIcon className="w-3.5 h-3.5 text-emerald-400" />
                                ) : (
                                  <ClipboardDocumentIcon className="w-3.5 h-3.5 text-gray-300" />
                                )}
                              </button>
                            </div>
                          )}
                          {step.link && (
                            <a
                              href={step.link.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 mt-2 text-xs font-medium text-blue-600 hover:text-blue-800 transition-colors"
                            >
                              <ArrowTopRightOnSquareIcon className="w-3.5 h-3.5" />
                              {step.link.label}
                            </a>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Footer */}
                <div className="px-6 py-4 border-t border-black/[0.06] flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {activeSetup.docsUrl && (
                      <a
                        href={activeSetup.docsUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-gray-500 hover:text-gray-700 transition-colors"
                      >
                        <BookOpenIcon className="w-3.5 h-3.5" />
                        Full docs
                      </a>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setSetupModal(null)}
                      className="px-4 py-2 text-sm font-medium text-gray-500 hover:text-gray-700"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleSetupConfirm}
                      disabled={setupConfirming}
                      className="flex items-center gap-1.5 px-5 py-2 text-sm font-semibold text-white bg-black rounded-xl hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      {setupConfirming ? (
                        <ArrowPathIcon className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <CheckCircleIcon className="w-4 h-4" />
                      )}
                      {setupConfirming ? 'Confirming...' : "I've completed setup"}
                    </button>
                  </div>
                </div>
              </motion.div>
            </motion.div>
          );
        })()}
      </AnimatePresence>
    </div>
  );
};

export default ConnectorsPage;