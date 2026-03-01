-- ============================================================================
-- CONNECTOR INFRASTRUCTURE SCHEMA
-- Extends the main Membread schema with tables for OAuth connections,
-- sync cursors, provider credentials, and webhook registrations.
-- All tables use RLS for tenant isolation and bi-temporal indexing.
-- ============================================================================

-- Provider credentials (admin-level, encrypted client secrets)
CREATE TABLE IF NOT EXISTS provider_credentials (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    provider_id TEXT NOT NULL,                -- e.g. 'hubspot', 'salesforce'
    client_id TEXT NOT NULL,
    client_secret_encrypted TEXT NOT NULL,     -- Fernet-encrypted
    scopes TEXT DEFAULT '',
    extra_config JSONB DEFAULT '{}',           -- provider-specific settings
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, provider_id)
);

CREATE INDEX IF NOT EXISTS idx_prov_creds_tenant ON provider_credentials(tenant_id);
ALTER TABLE provider_credentials ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'provider_credentials' AND policyname = 'tenant_isolation_provider_credentials'
    ) THEN
        CREATE POLICY tenant_isolation_provider_credentials ON provider_credentials
            FOR ALL USING (tenant_id = current_setting('app.tenant_id', true)::UUID);
    END IF;
END $$;


-- OAuth connections (per-tenant, per-connector token storage)
CREATE TABLE IF NOT EXISTS connector_connections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    connector_id TEXT NOT NULL,               -- e.g. 'hubspot', 'shopify'
    status TEXT NOT NULL DEFAULT 'disconnected',  -- connected | disconnected | error | pending_oauth
    auth_method TEXT NOT NULL DEFAULT 'webhook',  -- oauth2 | api_key | webhook | sdk | browser-extension | mcp
    access_token_encrypted TEXT,               -- Fernet-encrypted OAuth access token
    refresh_token_encrypted TEXT,              -- Fernet-encrypted OAuth refresh token
    api_key_encrypted TEXT,                    -- Fernet-encrypted API key (for api_key auth)
    token_expires_at TIMESTAMPTZ,
    oauth_state TEXT,                          -- CSRF state for in-flight OAuth
    webhook_id TEXT,                           -- ID of registered webhook on provider side
    webhook_secret TEXT,                       -- HMAC secret for verifying inbound webhooks
    config JSONB DEFAULT '{}',                 -- provider-specific connection config
    error_message TEXT,
    memories_captured BIGINT DEFAULT 0,
    last_sync_at TIMESTAMPTZ,
    last_error_at TIMESTAMPTZ,
    connected_at TIMESTAMPTZ,
    valid_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),    -- bi-temporal: when this state became true
    invalid_at TIMESTAMPTZ,                         -- bi-temporal: when this state was superseded
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, connector_id) WHERE invalid_at IS NULL  -- only one active connection per connector
);

CREATE INDEX IF NOT EXISTS idx_conn_tenant ON connector_connections(tenant_id);
CREATE INDEX IF NOT EXISTS idx_conn_status ON connector_connections(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_conn_connector ON connector_connections(connector_id);
CREATE INDEX IF NOT EXISTS idx_conn_oauth_state ON connector_connections(oauth_state) WHERE oauth_state IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_conn_valid ON connector_connections(valid_at, invalid_at);
CREATE INDEX IF NOT EXISTS idx_conn_active ON connector_connections(tenant_id, connector_id) WHERE invalid_at IS NULL;

ALTER TABLE connector_connections ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'connector_connections' AND policyname = 'tenant_isolation_connector_connections'
    ) THEN
        CREATE POLICY tenant_isolation_connector_connections ON connector_connections
            FOR ALL USING (tenant_id = current_setting('app.tenant_id', true)::UUID);
    END IF;
END $$;


-- Sync cursors (track polling checkpoint per connector per tenant)
CREATE TABLE IF NOT EXISTS sync_cursors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    connector_id TEXT NOT NULL,
    cursor_type TEXT NOT NULL DEFAULT 'timestamp',  -- timestamp | offset | page_token
    cursor_value TEXT NOT NULL DEFAULT '',           -- ISO timestamp, numeric offset, or opaque token
    last_poll_at TIMESTAMPTZ,
    next_poll_at TIMESTAMPTZ,
    poll_interval_seconds INT DEFAULT 60,
    items_fetched_total BIGINT DEFAULT 0,
    consecutive_errors INT DEFAULT 0,
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, connector_id)
);

CREATE INDEX IF NOT EXISTS idx_sync_cursor_tenant ON sync_cursors(tenant_id);
CREATE INDEX IF NOT EXISTS idx_sync_cursor_next_poll ON sync_cursors(next_poll_at) WHERE next_poll_at IS NOT NULL;

ALTER TABLE sync_cursors ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'sync_cursors' AND policyname = 'tenant_isolation_sync_cursors'
    ) THEN
        CREATE POLICY tenant_isolation_sync_cursors ON sync_cursors
            FOR ALL USING (tenant_id = current_setting('app.tenant_id', true)::UUID);
    END IF;
END $$;


-- Webhook registrations (track webhooks we registered on provider side)
CREATE TABLE IF NOT EXISTS webhook_registrations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    connector_id TEXT NOT NULL,
    provider_webhook_id TEXT,                  -- ID returned by provider when we registered
    webhook_url TEXT NOT NULL,                 -- our endpoint URL
    events TEXT[] DEFAULT '{}',                -- list of event types subscribed
    verification_secret TEXT,                  -- HMAC key for signature verification
    status TEXT DEFAULT 'active',              -- active | inactive | failed
    last_delivery_at TIMESTAMPTZ,
    deliveries_total BIGINT DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_wh_reg_tenant ON webhook_registrations(tenant_id, connector_id);

ALTER TABLE webhook_registrations ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'webhook_registrations' AND policyname = 'tenant_isolation_webhook_registrations'
    ) THEN
        CREATE POLICY tenant_isolation_webhook_registrations ON webhook_registrations
            FOR ALL USING (tenant_id = current_setting('app.tenant_id', true)::UUID);
    END IF;
END $$;


-- Connector activity log (detailed per-connector sync history)
CREATE TABLE IF NOT EXISTS connector_activity (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    connector_id TEXT NOT NULL,
    activity_type TEXT NOT NULL,               -- poll | webhook_received | oauth_refresh | error | connected | disconnected
    details JSONB DEFAULT '{}',
    items_count INT DEFAULT 0,
    duration_ms INT,
    error_message TEXT,
    valid_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),  -- bi-temporal tracking
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conn_act_tenant ON connector_activity(tenant_id, connector_id);
CREATE INDEX IF NOT EXISTS idx_conn_act_type ON connector_activity(activity_type);
CREATE INDEX IF NOT EXISTS idx_conn_act_valid ON connector_activity(valid_at);
CREATE INDEX IF NOT EXISTS idx_conn_act_created ON connector_activity(created_at);

ALTER TABLE connector_activity ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'connector_activity' AND policyname = 'tenant_isolation_connector_activity'
    ) THEN
        CREATE POLICY tenant_isolation_connector_activity ON connector_activity
            FOR ALL USING (tenant_id = current_setting('app.tenant_id', true)::UUID);
    END IF;
END $$;


-- Trigger to update updated_at columns
CREATE TRIGGER update_provider_credentials_updated_at BEFORE UPDATE ON provider_credentials
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_connector_connections_updated_at BEFORE UPDATE ON connector_connections
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sync_cursors_updated_at BEFORE UPDATE ON sync_cursors
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_webhook_registrations_updated_at BEFORE UPDATE ON webhook_registrations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
