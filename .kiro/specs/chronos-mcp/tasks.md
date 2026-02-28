# Implementation Plan: ChronosMCP

## Overview

This implementation plan breaks down the ChronosMCP Universal Temporal-Aware Memory Layer into discrete, incremental coding tasks. The approach follows a bottom-up strategy: first establishing the storage layer, then building the memory engine and governor logic, and finally exposing everything through the MCP server interface. Each task builds on previous work, with property-based tests integrated throughout to catch errors early.

## Tasks

- [x] 1. Project setup and database infrastructure
  - Create project structure following the specified repository layout
  - Set up pyproject.toml with dependencies (asyncpg, pgvector, anthropic-mcp-sdk, hypothesis, pytest, openai)
  - Create schema.sql with all table definitions, indexes, and RLS policies
  - Implement database connection pool with async support
  - Create database initialization script that runs schema.sql
  - _Requirements: 1.1, 1.2, 1.3, 9.2, 9.3_

- [ ] 2. Core data models and types
  - [x] 2.1 Implement data model classes
    - Create PrivilegeLayer enum
    - Create dataclasses: Observation, Fact, GraphNode, GraphRelationship, UserProfile
    - Create result types: StoreResult, RecallResult, ConflictResolution
    - Add type hints and validation using Pydantic
    - _Requirements: 1.6, 3.4, 3.6_
  
  - [ ]* 2.2 Write property test for data model validation
    - **Property 24: Error Logging Completeness**
    - **Validates: Requirements 9.6**

- [ ] 3. SQL Store implementation
  - [x] 3.1 Implement SQLStore class
    - Create connection management with tenant context setting
    - Implement get_profile with RLS enforcement
    - Implement update_profile with privilege checking
    - Implement create_audit_log for Layer 1 operations
    - Add helper methods for setting app.tenant_id session variable
    - _Requirements: 1.3, 1.7, 6.1, 6.6_
  
  - [ ]* 3.2 Write property test for tenant isolation
    - **Property 1: Tenant Isolation Invariant**
    - **Validates: Requirements 1.3, 1.7, 6.1, 6.4, 6.5**
  
  - [ ]* 3.3 Write property test for profile retrieval
    - **Property 5: Profile Retrieval Consistency**
    - **Validates: Requirements 2.6, 8.5**
  
  - [ ]* 3.4 Write property test for audit logging
    - **Property 19: Audit Log Completeness**
    - **Validates: Requirements 6.6**

- [ ] 4. Vector Store implementation
  - [x] 4.1 Implement VectorStore class
    - Create store_embedding method with metadata
    - Implement similarity_search with pgvector cosine similarity
    - Add metadata filtering for tenant_id and user_id
    - Create indexes for efficient vector search
    - _Requirements: 1.1, 1.5, 6.5, 8.1, 8.2_
  
  - [ ]* 4.2 Write property test for semantic search
    - **Property 3: Semantic Search Relevance**
    - **Validates: Requirements 1.5, 2.5, 8.3**
  
  - [ ]* 4.3 Write property test for metadata filtering
    - Test that tenant_id filtering works correctly in vector searches
    - _Requirements: 6.5_

- [ ] 5. Graph Store implementation
  - [x] 5.1 Implement GraphStore class
    - Create create_node with temporal validity (valid_at, invalid_at)
    - Implement invalidate_node for conflict resolution
    - Create create_relationship with temporal validity
    - Implement query_at_timestamp for time-travel queries
    - Implement get_causal_chain for lineage tracking
    - Add indexes on entity_id and validity timestamps
    - _Requirements: 1.2, 1.6, 3.4, 3.5, 3.6, 3.7, 7.1_
  
  - [ ]* 5.2 Write property test for temporal validity
    - **Property 8: Time-Travel Query Accuracy**
    - **Validates: Requirements 3.5, 3.7, 8.7**
  
  - [ ]* 5.3 Write property test for current facts filtering
    - **Property 9: Current Facts Validity**
    - **Validates: Requirements 3.7**
  
  - [ ]* 5.4 Write property test for causal chains
    - **Property 20: Hydra Lineage Completeness**
    - **Validates: Requirements 7.1**

- [ ] 6. Checkpoint - Ensure storage layer tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Embedding service integration
  - [x] 7.1 Implement EmbeddingService class
    - Create async client for OpenAI embeddings API
    - Implement generate_embedding method with error handling
    - Add retry logic with exponential backoff
    - Support batch embedding generation
    - _Requirements: 8.1_
  
  - [ ]* 7.2 Write unit tests for embedding service
    - Test API error handling
    - Test retry logic
    - Test batch operations
    - _Requirements: 8.1_

- [ ] 8. Circuit breaker implementation
  - [x] 8.1 Implement CircuitBreaker class
    - Create state machine (CLOSED, OPEN, HALF_OPEN)
    - Implement execute method with state transitions
    - Add failure counting and timeout logic
    - Implement fallback mechanism support
    - _Requirements: 5.2, 5.3, 7.3_
  
  - [ ]* 8.2 Write unit test for circuit breaker states
    - Test state transitions under failures
    - Test fallback activation
    - _Requirements: 5.2, 5.3_

- [ ] 9. SQLite FTS5 fallback implementation
  - [x] 9.1 Implement SQLite fallback store
    - Create SQLite database with FTS5 extension
    - Implement fallback_to_sqlite function
    - Add observation indexing for full-text search
    - Ensure tenant isolation in fallback mode
    - _Requirements: 5.3_
  
  - [ ]* 9.2 Write unit test for fallback mechanism
    - Test fallback activation when PostgreSQL fails
    - Test search functionality in fallback mode
    - _Requirements: 5.3_

- [ ] 10. Context compression implementation
  - [x] 10.1 Implement ContextCompressor class
    - Create mini-LLM client for summarization
    - Implement compress method with token counting
    - Add semantic similarity verification after compression
    - Support configurable compression ratios
    - _Requirements: 5.6, 7.2_
  
  - [ ]* 10.2 Write property test for compression preservation
    - **Property 15: Context Compression Preservation**
    - **Validates: Requirements 5.6, 7.2**

- [ ] 11. Governor - Conflict resolver
  - [x] 11.1 Implement ConflictResolver class
    - Create resolve_conflict method with temporal logic
    - Implement fact contradiction detection
    - Add logic to invalidate old facts and create new ones
    - Create causal relationship linking old and new facts
    - _Requirements: 3.1, 3.2, 3.3, 3.4_
  
  - [ ]* 11.2 Write property test for conflict resolution
    - **Property 7: Temporal Conflict Resolution Completeness**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4**

- [ ] 12. Governor - Constraint enforcer
  - [x] 12.1 Implement ConstraintEnforcer class
    - Load Layer 0 immutable constraints from database
    - Implement enforce_constraints validation method
    - Add privilege layer checking (Layer 0/1/2)
    - Implement prompt injection detection
    - Add SQL injection pattern detection
    - _Requirements: 4.3, 4.4, 4.5, 4.7, 6.8, 7.5_
  
  - [ ]* 12.2 Write property test for privilege enforcement
    - **Property 11: Privilege Layer Enforcement**
    - **Validates: Requirements 4.3, 4.4, 4.5**
  
  - [ ]* 12.3 Write property test for prompt injection defense
    - **Property 13: Prompt Injection Defense**
    - **Validates: Requirements 4.7, 6.8, 7.5**

- [ ] 13. Governor - Lattice crawler
  - [x] 13.1 Implement LatticeCrawler class
    - Create multi_hop_traverse method with BFS/DFS
    - Implement relationship type filtering
    - Add max hop depth limiting
    - Support temporal validity filtering during traversal
    - _Requirements: 4.2_
  
  - [ ]* 13.2 Write property test for multi-hop traversal
    - **Property 10: Multi-Hop Traversal Completeness**
    - **Validates: Requirements 4.2**

- [ ] 14. Governor - Routing logic
  - [x] 14.1 Implement RoutingLogic class
    - Create route_operation method with deterministic rules
    - Implement store type selection based on data characteristics
    - Add operation priority ordering
    - _Requirements: 1.4, 4.1_
  
  - [ ]* 14.2 Write property test for routing determinism
    - **Property 2: Storage Routing Determinism**
    - **Validates: Requirements 1.4, 4.1**

- [ ] 15. Governor - Provenance tracking
  - [x] 15.1 Implement ProvenanceTracker class
    - Create cryptographic hash generation (SHA-256)
    - Implement hash verification method
    - Add provenance chain tracking
    - Store provenance data with observations
    - _Requirements: 4.6, 6.7_
  
  - [ ]* 15.2 Write property test for provenance integrity
    - **Property 12: Provenance Integrity**
    - **Validates: Requirements 4.6, 6.7**

- [ ] 16. Governor - Main class integration
  - [x] 16.1 Implement Governor class
    - Integrate all governor components (resolver, enforcer, crawler, router, tracker)
    - Create unified interface for memory operations
    - Add coordination logic between components
    - _Requirements: 4.1, 4.2, 4.3, 4.6, 4.7_

- [ ] 17. Checkpoint - Ensure governor tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 18. Memory Engine - Core implementation
  - [x] 18.1 Implement MemoryEngine class
    - Initialize with all three stores and embedding service
    - Integrate circuit breaker for fault tolerance
    - Add optimistic concurrency control for writes
    - Implement performance logging for slow operations
    - _Requirements: 5.1, 5.2, 5.4, 5.5, 5.8_
  
  - [ ]* 18.2 Write property test for concurrent writes
    - **Property 14: Concurrent Write Conflict Resolution**
    - **Validates: Requirements 5.5, 7.4**
  
  - [ ]* 18.3 Write property test for performance logging
    - **Property 16: Performance Logging Completeness**
    - **Validates: Requirements 5.8**

- [ ] 19. Memory Engine - Store operation
  - [x] 19.1 Implement store_with_conflict_resolution method
    - Generate embedding for observation
    - Store in vector store with metadata
    - Extract entities and facts from observation
    - Check for conflicts using governor
    - Create/update graph nodes and relationships
    - Store observation record with provenance
    - Return StoreResult with IDs and stats
    - _Requirements: 2.4, 3.1, 3.2, 3.3, 8.1, 8.2, 8.6_
  
  - [ ]* 19.2 Write property test for observation storage round-trip
    - **Property 4: Observation Storage Round-Trip**
    - **Validates: Requirements 2.4, 8.1, 8.2**
  
  - [ ]* 19.3 Write property test for batch operations
    - **Property 22: Batch Operation Atomicity**
    - **Validates: Requirements 8.6**

- [ ] 20. Memory Engine - Recall operation
  - [x] 20.1 Implement recall_with_compression method
    - Perform semantic search in vector store
    - Query related entities in graph store
    - Combine results from both stores
    - Apply time-travel filtering if timestamp provided
    - Check token count and compress if needed
    - Return RecallResult with context and sources
    - _Requirements: 2.5, 3.5, 5.6, 8.3, 8.4, 8.7_
  
  - [ ]* 20.2 Write property test for multi-store integration
    - **Property 21: Multi-Store Recall Integration**
    - **Validates: Requirements 8.4**

- [ ] 21. JWT authentication implementation
  - [x] 21.1 Implement JWTAuthenticator class
    - Create JWT token validation method
    - Implement tenant_id and user_id extraction
    - Add token expiration checking
    - Support multiple JWT signing algorithms
    - _Requirements: 6.2, 6.3_
  
  - [ ]* 21.2 Write property test for JWT authentication
    - **Property 17: JWT Authentication Enforcement**
    - **Validates: Requirements 6.2**
  
  - [ ]* 21.3 Write property test for JWT claims extraction
    - **Property 18: JWT Claims Extraction**
    - **Validates: Requirements 6.3**

- [ ] 22. MCP Server - Tool implementations
  - [x] 22.1 Implement MCPServer class
    - Set up Anthropic MCP SDK server
    - Integrate JWT authenticator
    - Add request timeout enforcement (200ms SLA)
    - Implement error response formatting
    - _Requirements: 2.1, 2.2, 2.3, 2.7, 2.8, 5.1_
  
  - [x] 22.2 Implement chronos_store_observation tool
    - Extract and validate JWT from request
    - Call memory_engine.store_with_conflict_resolution
    - Format and return StoreResult
    - Handle errors with appropriate status codes
    - _Requirements: 2.1, 2.4_
  
  - [x] 22.3 Implement chronos_recall_context tool
    - Extract and validate JWT from request
    - Parse optional time_travel_ts parameter
    - Call memory_engine.recall_with_compression
    - Format and return RecallResult
    - _Requirements: 2.2, 2.5_
  
  - [x] 22.4 Implement chronos_get_profile tool
    - Extract and validate JWT from request
    - Call sql_store.get_profile
    - Format and return ProfileResult
    - _Requirements: 2.3, 2.6_
  
  - [ ]* 22.5 Write unit tests for MCP tool existence
    - Test that all three tools are exposed
    - Test MCP protocol compliance
    - _Requirements: 2.1, 2.2, 2.3, 2.7_
  
  - [ ]* 22.6 Write property test for response time
    - **Property 6: Response Time Bound**
    - **Validates: Requirements 2.8, 5.1**

- [ ] 23. Configuration and environment variables
  - [x] 23.1 Implement configuration management
    - Create Config class with environment variable loading
    - Support DATABASE_URL, OPENAI_API_KEY, JWT_SECRET
    - Add optional configuration for timeouts, limits, etc.
    - Implement validation for required variables
    - _Requirements: 9.4_
  
  - [ ]* 23.2 Write property test for configuration binding
    - **Property 23: Configuration Environment Variable Binding**
    - **Validates: Requirements 9.4**

- [ ] 24. Health check and monitoring endpoints
  - [ ] 24.1 Implement health check endpoints
    - Create /health endpoint returning system status
    - Add /health/ready endpoint checking database connectivity
    - Implement /health/live endpoint for liveness probe
    - Include version information in responses
    - _Requirements: 9.5_
  
  - [ ]* 24.2 Write unit tests for health endpoints
    - Test health endpoint responses
    - Test database connectivity checking
    - _Requirements: 9.5_

- [ ] 25. Structured logging implementation
  - [x] 25.1 Implement logging infrastructure
    - Set up structured JSON logging
    - Add log levels (DEBUG, INFO, WARNING, ERROR)
    - Include context (tenant_id, user_id, operation) in logs
    - Implement performance metric logging
    - _Requirements: 9.6_

- [ ] 26. Checkpoint - Ensure MCP server tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 27. Benchmark tests implementation
  - [ ]* 27.1 Implement Hydra of Nine Heads benchmark
    - Create test with entity undergoing 9+ changes
    - Verify complete lineage chain maintenance
    - Test time-travel queries at each change point
    - _Requirements: 7.1, 7.6_
  
  - [ ]* 27.2 Implement Vegetarian Trap benchmark
    - Create test with Layer 0 constraint (vegetarian preference)
    - Attempt prompt injection to override constraint
    - Verify injection is detected and rejected
    - Verify original constraint remains intact
    - _Requirements: 7.5, 7.7_

- [ ] 28. Docker containerization
  - [x] 28.1 Create Dockerfile
    - Use Python 3.11 base image
    - Install system dependencies (postgresql-client)
    - Copy application code and install Python dependencies
    - Set up entrypoint script
    - Expose MCP server port
    - _Requirements: 9.1_
  
  - [x] 28.2 Create docker-compose.yml
    - Define PostgreSQL service with pgvector
    - Define ChronosMCP service
    - Set up networking and volumes
    - Configure environment variables
    - _Requirements: 9.1, 9.3_
  
  - [ ]* 28.3 Write integration test for container startup
    - Test that container starts successfully
    - Test that database schemas are initialized
    - Test that health endpoints respond
    - _Requirements: 9.3_

- [ ] 29. Documentation and README
  - [x] 29.1 Create comprehensive README.md
    - Add project overview and features
    - Include installation instructions
    - Document environment variables
    - Add usage examples for each MCP tool
    - Include architecture diagram
    - Add troubleshooting section
  
  - [x] 29.2 Create API documentation
    - Document all MCP tools with parameters
    - Include request/response examples
    - Document error codes and messages
    - Add authentication requirements

- [ ] 30. Final integration testing and validation
  - [ ]* 30.1 Run complete test suite
    - Execute all unit tests
    - Execute all property tests (100+ iterations each)
    - Execute benchmark tests
    - Verify test coverage >85%
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8_
  
  - [ ]* 30.2 End-to-end integration test
    - Start system with Docker Compose
    - Store observations via MCP
    - Recall context with time-travel
    - Verify multi-tenant isolation
    - Test circuit breaker with simulated failures
    - Verify all requirements are met

- [ ] 31. Final checkpoint - Production readiness
  - Ensure all tests pass, ask the user if questions arise.
  - Verify sub-200ms latency requirement
  - Verify multi-tenant isolation
  - Verify temporal conflict resolution
  - Verify circuit breaker functionality
  - System is ready for deployment

## Notes

- Tasks marked with `*` are optional test-related sub-tasks that can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at major milestones
- Property tests validate universal correctness properties with 100+ iterations
- Unit tests validate specific examples, edge cases, and error conditions
- The implementation follows a bottom-up approach: storage → engine → governor → MCP server
- All code should be fully typed with Python type hints
- All async operations should use asyncio and async/await patterns
- Database operations should use connection pooling for performance
