# ChronosMCP Demo Instructions

## Overview
ChronosMCP is a Universal Temporal-Aware Memory Layer for AI Agents. This demo showcases the core functionality including authentication, storing observations, recalling context, and viewing user profiles.

## Prerequisites
- Docker and Docker Compose installed
- Ports 3000, 5432, and 8000 available

## Starting the Application

1. **Start all services:**
   ```bash
   docker-compose up -d
   ```

2. **Verify all containers are running:**
   ```bash
   docker-compose ps
   ```
   
   You should see 4 containers running:
   - `chronos-postgres` - PostgreSQL database with pgvector extension
   - `chronos-api` - FastAPI HTTP server
   - `chronos-mcp` - MCP server for AI agent integration
   - `chronos-frontend` - Web UI (Nginx)

3. **Check API health:**
   ```bash
   curl http://localhost:8000/health
   ```
   
   Expected response:
   ```json
   {"status":"healthy","version":"0.1.0","timestamp":"..."}
   ```

## Accessing the Demo

Open your web browser and navigate to:
```
http://localhost:3000
```

## Demo Walkthrough

### 1. Authentication
The first step is to generate an authentication token:

1. In the **Authentication** card (top-left), you'll see:
   - Tenant ID: `demo-tenant` (pre-filled)
   - User ID: `demo-user` (pre-filled)

2. Click **Generate Token**

3. You'll receive a JWT token that expires in 24 hours

**What's happening behind the scenes:**
- The system creates a tenant and user if they don't exist
- A JWT token is generated with tenant and user context
- This token is used for all subsequent API calls

### 2. Store Observations
Now you can store observations (memories) in the system:

1. In the **Store Observation** card (top-right), enter some text, for example:
   ```
   The user prefers dark mode for all applications
   ```

2. Click **Store**

3. You'll see a success message with:
   - Observation ID (unique identifier)
   - Provenance Hash (cryptographic proof)
   - Nodes Created (graph entities extracted)
   - Conflicts Resolved (if any contradictions were found)

**What's happening behind the scenes:**
- The observation is stored in the SQL database
- Text is embedded using OpenAI's embedding model
- Entities and relationships are extracted and stored in the temporal graph
- The Governor checks for conflicts with existing knowledge
- Provenance tracking ensures data integrity

### 3. Recall Context
Query the system to recall relevant information:

1. In the **Recall Context** card (bottom-left), enter a query:
   ```
   What are the user's preferences?
   ```

2. Set Max Tokens (default: 2000)

3. Click **Recall**

4. You'll see:
   - Number of sources found
   - Token count
   - Whether compression was applied
   - The recalled context

**What's happening behind the scenes:**
- Your query is embedded using the same model
- Vector similarity search finds relevant observations
- Graph traversal finds related entities
- Context is assembled and optionally compressed
- Results are returned within the token limit

### 4. User Profile
View the user's profile information:

1. In the **User Profile** card (bottom-right), click **Get Profile**

2. You'll see:
   - Display name
   - Tenant and User IDs
   - Creation and update timestamps
   - User preferences (JSON)

### 5. Session Stats
The bottom card shows real-time statistics:
- **Observations Stored**: Total number of observations you've stored
- **Contexts Recalled**: Number of recall operations
- **Total Tokens**: Cumulative token count from recalls
- **Compressions**: How many times context was compressed

## Advanced Demo Scenarios

### Scenario 1: Temporal Queries
Store observations at different times and query with time travel:

1. Store: "The project deadline is March 15th"
2. Wait a moment
3. Store: "The project deadline has been moved to March 22nd"
4. Recall: "When is the project deadline?"
   - The system will return the most recent information
   - The temporal graph maintains the history of changes

### Scenario 2: Conflict Resolution
Test the Governor's conflict resolution:

1. Store: "The user's favorite color is blue"
2. Store: "The user's favorite color is red"
3. Recall: "What is the user's favorite color?"
   - The Governor detects the conflict
   - The most recent observation takes precedence
   - Both are maintained in the temporal graph

### Scenario 3: Multi-Tenant Isolation
Test tenant isolation:

1. Generate a token for `tenant-a` / `user-1`
2. Store some observations
3. Generate a token for `tenant-b` / `user-1`
4. Try to recall - you won't see tenant-a's data
   - Row-Level Security (RLS) ensures data isolation
   - Each tenant's data is completely separate

## API Endpoints

If you want to test the API directly:

### Generate Token
```bash
curl -X POST http://localhost:8000/api/auth/token \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "demo-tenant", "user_id": "demo-user"}'
```

### Store Observation
```bash
curl -X POST http://localhost:8000/api/memory/store \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"observation": "Test observation", "metadata": {}}'
```

### Recall Context
```bash
curl -X POST http://localhost:8000/api/memory/recall \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"query": "test", "max_tokens": 2000}'
```

### Get Profile
```bash
curl http://localhost:8000/api/memory/profile \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## MCP Server Integration

The MCP server (`chronos-mcp`) provides the same functionality through the Model Context Protocol for AI agent integration. It runs in stdio mode and can be connected to AI agents like Claude Desktop.

To test the MCP server:
```bash
docker exec -it chronos-mcp python -m src.main
```

## Stopping the Application

```bash
docker-compose down
```

To also remove the database volume:
```bash
docker-compose down -v
```

## Troubleshooting

### Containers not starting
```bash
docker-compose logs
```

### API not responding
```bash
docker logs chronos-api
```

### Database connection issues
```bash
docker logs chronos-postgres
```

### Frontend not loading
```bash
docker logs chronos-frontend
```

## Architecture Highlights

### Layer 0: Immutable Constraints
- Prompt injection detection
- SQL injection prevention
- Token limits
- Observation length limits

### Layer 1: Governor
- Conflict detection and resolution
- Constraint enforcement
- Provenance tracking
- Routing logic

### Layer 2: Memory Engine
- Vector store (semantic search)
- Graph store (temporal relationships)
- SQL store (structured data)
- Context compression

### Layer 3: API & MCP
- HTTP REST API
- Model Context Protocol server
- JWT authentication
- Multi-tenant isolation

## Key Features Demonstrated

1. **Temporal Awareness**: All data has valid_at/invalid_at timestamps
2. **Conflict Resolution**: Automatic detection and resolution of contradictions
3. **Provenance Tracking**: Cryptographic hashing for data integrity
4. **Multi-Tenancy**: Complete data isolation between tenants
5. **Context Compression**: Intelligent summarization when token limits are exceeded
6. **Vector Search**: Semantic similarity for relevant context retrieval
7. **Graph Traversal**: Relationship-based context assembly

## Next Steps

- Explore the codebase in `src/`
- Review the database schema in `schema.sql`
- Check the spec documents in `.kiro/specs/chronos-mcp/`
- Integrate with your AI agent using the MCP server

## Support

For issues or questions, refer to:
- README.md - Project overview
- .kiro/specs/chronos-mcp/design.md - Detailed design document
- .kiro/specs/chronos-mcp/requirements.md - Requirements and acceptance criteria
