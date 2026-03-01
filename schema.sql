-- Membread Database Schema
-- Universal Temporal-Aware Memory Layer
-- PostgreSQL with pgvector extension

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ============================================================================
-- TENANTS AND USERS
-- ============================================================================

-- Tenants table: Multi-tenant isolation root
CREATE TABLE IF NOT EXISTS tenants (
    tenant_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tenants_created ON tenants(created_at);

-- Users table with Row-Level Security
CREATE TABLE IF NOT EXISTS users (
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    user_id UUID NOT NULL DEFAULT uuid_generate_v4(),
    display_name TEXT NOT NULL,
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (tenant_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_users_tenant ON users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_users_created ON users(created_at);

-- Enable Row-Level Security on users
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Users can only see their own tenant's data
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'users' AND policyname = 'tenant_isolation_users'
    ) THEN
        CREATE POLICY tenant_isolation_users ON users
            FOR ALL
            USING (tenant_id = current_setting('app.tenant_id', true)::UUID);
    END IF;
END $$;

-- ============================================================================
-- VECTOR EMBEDDINGS STORE
-- ============================================================================

-- Embeddings table: Semantic vector storage with pgvector
CREATE TABLE IF NOT EXISTS embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    embedding vector(1536) NOT NULL,  -- OpenAI ada-002 dimension
    text TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for efficient vector similarity search
CREATE INDEX IF NOT EXISTS idx_embeddings_vector ON embeddings 
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_embeddings_tenant ON embeddings(tenant_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_user ON embeddings(tenant_id, user_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_created ON embeddings(created_at);
CREATE INDEX IF NOT EXISTS idx_embeddings_metadata ON embeddings USING gin(metadata);

-- Enable Row-Level Security on embeddings
ALTER TABLE embeddings ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'embeddings' AND policyname = 'tenant_isolation_embeddings'
    ) THEN
        CREATE POLICY tenant_isolation_embeddings ON embeddings
            FOR ALL
            USING (tenant_id = current_setting('app.tenant_id', true)::UUID);
    END IF;
END $$;

-- ============================================================================
-- TEMPORAL GRAPH STORE
-- ============================================================================

-- Graph nodes: Entities with temporal validity
CREATE TABLE IF NOT EXISTS graph_nodes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    entity_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    properties JSONB NOT NULL DEFAULT '{}',
    valid_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    invalid_at TIMESTAMPTZ,  -- NULL means currently valid
    source_observation_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for temporal queries and graph traversal
CREATE INDEX IF NOT EXISTS idx_graph_nodes_tenant_entity ON graph_nodes(tenant_id, entity_id);
CREATE INDEX IF NOT EXISTS idx_graph_nodes_entity_type ON graph_nodes(entity_type);
CREATE INDEX IF NOT EXISTS idx_graph_nodes_validity ON graph_nodes(valid_at, invalid_at);
CREATE INDEX IF NOT EXISTS idx_graph_nodes_valid_current ON graph_nodes(tenant_id, entity_id) 
    WHERE invalid_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_graph_nodes_properties ON graph_nodes USING gin(properties);

-- Enable Row-Level Security on graph_nodes
ALTER TABLE graph_nodes ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'graph_nodes' AND policyname = 'tenant_isolation_graph_nodes'
    ) THEN
        CREATE POLICY tenant_isolation_graph_nodes ON graph_nodes
            FOR ALL
            USING (tenant_id = current_setting('app.tenant_id', true)::UUID);
    END IF;
END $$;

-- Graph relationships: Temporal edges between nodes
CREATE TABLE IF NOT EXISTS graph_relationships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    from_node_id UUID NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,
    to_node_id UUID NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,
    relationship_type TEXT NOT NULL,
    properties JSONB NOT NULL DEFAULT '{}',
    valid_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    invalid_at TIMESTAMPTZ,  -- NULL means currently valid
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for relationship traversal
CREATE INDEX IF NOT EXISTS idx_graph_rels_from ON graph_relationships(from_node_id);
CREATE INDEX IF NOT EXISTS idx_graph_rels_to ON graph_relationships(to_node_id);
CREATE INDEX IF NOT EXISTS idx_graph_rels_type ON graph_relationships(relationship_type);
CREATE INDEX IF NOT EXISTS idx_graph_rels_validity ON graph_relationships(valid_at, invalid_at);
CREATE INDEX IF NOT EXISTS idx_graph_rels_valid_current ON graph_relationships(from_node_id) 
    WHERE invalid_at IS NULL;

-- ============================================================================
-- OBSERVATIONS STORE
-- ============================================================================

-- Observations: Raw unstructured data with provenance
CREATE TABLE IF NOT EXISTS observations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    text TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    provenance_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_observations_tenant ON observations(tenant_id);
CREATE INDEX IF NOT EXISTS idx_observations_user ON observations(tenant_id, user_id);
CREATE INDEX IF NOT EXISTS idx_observations_created ON observations(created_at);
CREATE INDEX IF NOT EXISTS idx_observations_hash ON observations(provenance_hash);

-- Enable Row-Level Security on observations
ALTER TABLE observations ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'observations' AND policyname = 'tenant_isolation_observations'
    ) THEN
        CREATE POLICY tenant_isolation_observations ON observations
            FOR ALL
            USING (tenant_id = current_setting('app.tenant_id', true)::UUID);
    END IF;
END $$;

-- ============================================================================
-- AUDIT LOGS
-- ============================================================================

-- Audit logs: Track Layer 1 privilege operations
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    operation TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_tenant ON audit_logs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(tenant_id, user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_operation ON audit_logs(operation);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON audit_logs(created_at);

-- Enable Row-Level Security on audit_logs
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'audit_logs' AND policyname = 'tenant_isolation_audit_logs'
    ) THEN
        CREATE POLICY tenant_isolation_audit_logs ON audit_logs
            FOR ALL
            USING (tenant_id = current_setting('app.tenant_id', true)::UUID);
    END IF;
END $$;

-- ============================================================================
-- CONSTRAINTS (Layer 0 Immutable Rules)
-- ============================================================================

-- Constraints: Global immutable rules (no RLS)
CREATE TABLE IF NOT EXISTS constraints (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    constraint_type TEXT NOT NULL,
    rule JSONB NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_constraints_type ON constraints(constraint_type);

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to set tenant context for RLS
CREATE OR REPLACE FUNCTION set_tenant_context(p_tenant_id UUID)
RETURNS void AS $$
BEGIN
    PERFORM set_config('app.tenant_id', p_tenant_id::text, false);
END;
$$ LANGUAGE plpgsql;

-- Function to get current tenant context
CREATE OR REPLACE FUNCTION get_tenant_context()
RETURNS UUID AS $$
BEGIN
    RETURN current_setting('app.tenant_id', true)::UUID;
EXCEPTION
    WHEN OTHERS THEN
        RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
CREATE TRIGGER update_tenants_updated_at BEFORE UPDATE ON tenants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- RECURSIVE CTE HELPER FOR GRAPH TRAVERSAL
-- ============================================================================

-- Function to get causal chain for an entity
CREATE OR REPLACE FUNCTION get_causal_chain(
    p_tenant_id UUID,
    p_entity_id TEXT
)
RETURNS TABLE (
    node_id UUID,
    entity_id TEXT,
    entity_type TEXT,
    properties JSONB,
    valid_at TIMESTAMPTZ,
    invalid_at TIMESTAMPTZ,
    depth INT
) AS $$
BEGIN
    RETURN QUERY
    WITH RECURSIVE causal_chain AS (
        -- Base case: Get earliest version
        SELECT 
            gn.id,
            gn.entity_id,
            gn.entity_type,
            gn.properties,
            gn.valid_at,
            gn.invalid_at,
            0 as depth
        FROM graph_nodes gn
        WHERE gn.tenant_id = p_tenant_id
          AND gn.entity_id = p_entity_id
          AND gn.valid_at = (
              SELECT MIN(valid_at) 
              FROM graph_nodes 
              WHERE tenant_id = p_tenant_id AND entity_id = p_entity_id
          )
        
        UNION ALL
        
        -- Recursive case: Follow SUPERSEDED_BY relationships
        SELECT 
            gn.id,
            gn.entity_id,
            gn.entity_type,
            gn.properties,
            gn.valid_at,
            gn.invalid_at,
            cc.depth + 1
        FROM graph_nodes gn
        INNER JOIN graph_relationships gr ON gn.id = gr.to_node_id
        INNER JOIN causal_chain cc ON gr.from_node_id = cc.node_id
        WHERE gr.relationship_type = 'SUPERSEDED_BY'
          AND gn.tenant_id = p_tenant_id
    )
    SELECT * FROM causal_chain ORDER BY valid_at ASC;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- INITIAL DATA
-- ============================================================================

-- Insert default constraint examples (Layer 0)
INSERT INTO constraints (constraint_type, rule, description) VALUES
    ('prompt_injection_pattern', '{"patterns": ["ignore previous", "forget that", "disregard", "override"]}', 'Detect common prompt injection attempts'),
    ('sql_injection_pattern', '{"patterns": ["DROP TABLE", "DELETE FROM", "INSERT INTO", "UPDATE.*SET", "--", "/*"]}', 'Detect SQL injection attempts'),
    ('max_observation_length', '{"max_length": 10000}', 'Maximum observation text length'),
    ('max_token_limit', '{"max_tokens": 8000}', 'Maximum token count for context recall')
ON CONFLICT DO NOTHING;

-- Create default system tenant for testing
INSERT INTO tenants (tenant_id, name) VALUES
    ('00000000-0000-0000-0000-000000000000', 'System')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- GRANTS (for application user)
-- ============================================================================

-- Grant necessary permissions to application role
-- Note: In production, create a specific role with limited permissions
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO membread_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO membread_app;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO membread_app;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE tenants IS 'Multi-tenant isolation root table';
COMMENT ON TABLE users IS 'User profiles with RLS enforcement';
COMMENT ON TABLE embeddings IS 'Vector embeddings for semantic search (pgvector)';
COMMENT ON TABLE graph_nodes IS 'Temporal graph nodes with valid_at/invalid_at timestamps';
COMMENT ON TABLE graph_relationships IS 'Temporal graph edges with validity tracking';
COMMENT ON TABLE observations IS 'Raw observations with cryptographic provenance';
COMMENT ON TABLE audit_logs IS 'Audit trail for Layer 1 privilege operations';
COMMENT ON TABLE constraints IS 'Layer 0 immutable system constraints';

COMMENT ON FUNCTION set_tenant_context IS 'Set tenant context for Row-Level Security';
COMMENT ON FUNCTION get_causal_chain IS 'Retrieve complete evolution history of an entity';
