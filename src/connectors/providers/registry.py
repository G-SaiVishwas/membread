"""Provider registry — maps connector IDs to provider instances.

Central place to register and look up all 47 connector providers.
"""

from src.connectors.providers.base import BaseProvider
from src.connectors.providers.docusign import DocuSignProvider

# Tier 2: Enterprise
from src.connectors.providers.enterprise import (
    AutomationAnywhereProvider,
    CoupaProvider,
    IroncladProvider,
    MagentoProvider,
    OracleSCMProvider,
    SAPProvider,
    TwilioFlexProvider,
    UiPathProvider,
)
from src.connectors.providers.freshdesk import FreshdeskProvider
from src.connectors.providers.greenhouse import GreenhouseProvider

# Tier 1: OAuth + Webhook
from src.connectors.providers.hubspot import HubSpotProvider
from src.connectors.providers.intercom import IntercomProvider

# Tier 3: Inbound webhook only
from src.connectors.providers.ipaas import (
    AxiomAIProvider,
    FlowiseProvider,
    MakeProvider,
    N8nProvider,
    RelevanceAIProvider,
    WorkatoProvider,
)
from src.connectors.providers.lever import LeverProvider
from src.connectors.providers.marketo import MarketoProvider
from src.connectors.providers.outreach import OutreachProvider
from src.connectors.providers.pagerduty import PagerDutyProvider
from src.connectors.providers.salesforce import SalesforceProvider
from src.connectors.providers.salesloft import SalesLoftProvider
from src.connectors.providers.servicenow import ServiceNowProvider
from src.connectors.providers.shopify import ShopifyProvider
from src.connectors.providers.workday import WorkdayProvider
from src.connectors.providers.zapier import ZapierProvider

# Tier 2: OAuth/API-Key + Polling
from src.connectors.providers.zendesk import ZendeskProvider


def build_provider_registry() -> dict[str, BaseProvider]:
    """Instantiate all providers and return a {connector_id: provider} map."""
    providers: list[BaseProvider] = [
        # Tier 1
        HubSpotProvider(),
        SalesforceProvider(),
        ShopifyProvider(),
        IntercomProvider(),
        PagerDutyProvider(),
        LeverProvider(),
        DocuSignProvider(),
        ZapierProvider(),
        # Tier 2
        ZendeskProvider(),
        FreshdeskProvider(),
        OutreachProvider(),
        SalesLoftProvider(),
        GreenhouseProvider(),
        WorkdayProvider(),
        ServiceNowProvider(),
        MarketoProvider(),
        # Enterprise
        UiPathProvider(),
        AutomationAnywhereProvider(),
        SAPProvider(),
        OracleSCMProvider(),
        CoupaProvider(),
        IroncladProvider(),
        MagentoProvider(),
        TwilioFlexProvider(),
        # iPaaS / Agent platforms
        N8nProvider(),
        MakeProvider(),
        WorkatoProvider(),
        AxiomAIProvider(),
        FlowiseProvider(),
        RelevanceAIProvider(),
    ]

    registry = {}
    for p in providers:
        registry[p.provider_id] = p

    return registry


# Providers that support OAuth2 (have get_oauth_config)
OAUTH_PROVIDERS = {
    "hubspot", "salesforce", "shopify", "intercom", "pagerduty",
    "lever", "docusign-clm", "zendesk", "outreach", "salesloft",
    "workday", "servicenow",
}

# Providers that use API key auth
API_KEY_PROVIDERS = {
    "freshdesk", "greenhouse", "marketo", "uipath", "automation-anywhere",
    "sap", "oracle-scm", "coupa", "ironclad", "magento", "twilio-flex",
}

# Webhook-only providers (configure external tool to POST to us)
WEBHOOK_ONLY_PROVIDERS = {
    "zapier", "n8n", "make", "workato", "axiom-ai", "flowise", "relevance-ai",
    "vapi", "retell", "bland",
}

# Already handled by other mechanisms (browser ext, MCP, SDK)
EXTERNAL_PROVIDERS = {
    "chatgpt", "claude-web", "gemini", "perplexity", "ms-copilot",
    "claude-code", "cursor", "windsurf", "vscode-copilot",
    "langchain", "crewai", "autogen", "openai-sdk", "composio",
}
