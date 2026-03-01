"""FastAPI HTTP server for Membread / Membread."""

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Optional
from datetime import datetime
import structlog

from src.memory_engine.memory_engine import MemoryEngine
from src.memory_engine.sql_store import SQLStore
from src.auth.jwt_authenticator import JWTAuthenticator
from src.models import AuthenticationError

logger = structlog.get_logger()


# Request/Response Models
class StoreRequest(BaseModel):
    observation: str
    metadata: dict = {}


class RecallRequest(BaseModel):
    query: str
    time_travel_ts: Optional[str] = None
    max_tokens: int = 2000


class TokenRequest(BaseModel):
    tenant_id: str
    user_id: str


class StoreResponse(BaseModel):
    observation_id: str
    provenance_hash: str
    conflicts_resolved: int
    nodes_created: int
    message: str


class RecallResponse(BaseModel):
    context: str
    sources: list[str]
    token_count: int
    compressed: bool


class ProfileResponse(BaseModel):
    tenant_id: str
    user_id: str
    display_name: str
    preferences: dict
    created_at: str
    updated_at: str


class ListItem(BaseModel):
    id: str
    text: str
    metadata: dict


class ListResponse(BaseModel):
    items: list[ListItem]


class CountResponse(BaseModel):
    count: int


# ── Temporal / Graphiti request/response models ──────────────────────
class TemporalSearchRequest(BaseModel):
    query: str
    as_of: Optional[str] = None
    limit: int = 10


class TemporalHit(BaseModel):
    id: str
    text: str
    score: float
    event_time: Optional[str] = None
    ingestion_time: Optional[str] = None
    source: Optional[str] = None
    graph_score: float = 0.0


class TemporalSearchResponse(BaseModel):
    results: list[TemporalHit]
    as_of: Optional[str] = None


class EntityHistoryRequest(BaseModel):
    entity_name: str


class EntityVersionOut(BaseModel):
    entity_id: str
    name: str
    properties: dict[str, Any] = {}
    valid_from: str
    valid_until: Optional[str] = None


class EntityHistoryResponse(BaseModel):
    entity_name: str
    versions: list[EntityVersionOut]


class GraphDataResponse(BaseModel):
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]


class CaptureRequest(BaseModel):
    """Browser extension /capture payload."""
    conversation: list[dict[str, Any]]
    source: str = "browser_extension"
    url: Optional[str] = None
    title: Optional[str] = None


class CaptureResponse(BaseModel):
    episodes_ingested: int
    message: str


class TokenResponse(BaseModel):
    token: str
    tenant_id: str
    user_id: str
    expires_in_hours: int


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str


def create_app(
    memory_engine: MemoryEngine,
    sql_store: SQLStore,
    authenticator: JWTAuthenticator,
) -> FastAPI:
    """Create FastAPI application."""
    
    app = FastAPI(
        title="Membread API",
        description="Universal Temporal-Aware Memory Layer for AI Agents",
        version="0.1.0",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, specify exact origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Dependency for JWT authentication
    async def get_current_user(authorization: str = Header(None)):
        """Extract and validate JWT token."""
        if not authorization:
            raise HTTPException(status_code=401, detail="Authorization header missing")
        
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization format")
        
        token = authorization.replace("Bearer ", "")
        
        try:
            claims = authenticator.validate_token(token)
            return claims
        except AuthenticationError as e:
            raise HTTPException(status_code=401, detail=str(e))

    @app.get("/", response_model=HealthResponse)
    async def root():
        """Root endpoint."""
        return HealthResponse(
            status="healthy",
            version="0.1.0",
            timestamp=datetime.utcnow().isoformat(),
        )

    @app.get("/health", response_model=HealthResponse)
    async def health():
        """Health check endpoint."""
        return HealthResponse(
            status="healthy",
            version="0.1.0",
            timestamp=datetime.utcnow().isoformat(),
        )

    @app.post("/api/auth/token", response_model=TokenResponse)
    async def generate_token(request: TokenRequest):
        """Generate JWT token for testing."""
        token = authenticator.generate_token(
            tenant_id=request.tenant_id,
            user_id=request.user_id,
        )
        
        return TokenResponse(
            token=token,
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            expires_in_hours=24,
        )

    @app.post("/api/memory/store", response_model=StoreResponse)
    async def store_observation(
        request: StoreRequest,
        user: dict = Depends(get_current_user),
    ):
        """Store an observation with temporal metadata."""
        try:
            result = await memory_engine.store_with_conflict_resolution(
                observation=request.observation,
                metadata=request.metadata,
                tenant_id=user["tenant_id"],
                user_id=user["user_id"],
            )
            
            return StoreResponse(
                observation_id=result.observation_id,
                provenance_hash=result.provenance_hash,
                conflicts_resolved=result.conflicts_resolved,
                nodes_created=result.nodes_created,
                message="Observation stored successfully",
            )
        except Exception as e:
            logger.error("store_observation_failed", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/memory/recall", response_model=RecallResponse)
    async def recall_context(
        request: RecallRequest,
        user: dict = Depends(get_current_user),
    ):
        """Retrieve relevant context with optional time-travel."""
        try:
            time_travel_ts = None
            if request.time_travel_ts:
                time_travel_ts = datetime.fromisoformat(request.time_travel_ts)
            
            result = await memory_engine.recall_with_compression(
                query=request.query,
                tenant_id=user["tenant_id"],
                user_id=user["user_id"],
                time_travel_ts=time_travel_ts,
                max_tokens=request.max_tokens,
            )
            
            return RecallResponse(
                context=result.context,
                sources=result.sources,
                token_count=result.token_count,
                compressed=result.compressed,
            )
        except Exception as e:
            logger.error("recall_context_failed", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/memory/profile", response_model=ProfileResponse)
    async def get_profile(user: dict = Depends(get_current_user)):
        """Get user profile."""
        try:
            profile = await sql_store.get_profile(
                tenant_id=user["tenant_id"],
                user_id=user["user_id"],
            )
            
            if not profile:
                # Create default profile
                profile = await sql_store.create_profile(
                    tenant_id=user["tenant_id"],
                    user_id=user["user_id"],
                    display_name="User",
                    preferences={},
                )
            
            return ProfileResponse(
                tenant_id=profile.tenant_id,
                user_id=profile.user_id,
                display_name=profile.display_name,
                preferences=profile.preferences,
                created_at=profile.created_at.isoformat(),
                updated_at=profile.updated_at.isoformat(),
            )
        except Exception as e:
            logger.error("get_profile_failed", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/memory/list", response_model=ListResponse)
    async def list_memories(user: dict = Depends(get_current_user), limit: int = 50):
        """Return recent observations for the authenticated user."""
        try:
            results = await memory_engine.vector_store.list_embeddings(
                tenant_id=user["tenant_id"],
                user_id=user["user_id"],
                limit=limit,
            )
            return ListResponse(
                items=[ListItem(id=r.id, text=r.text, metadata=r.metadata) for r in results]
            )
        except Exception as e:
            logger.error("list_memories_failed", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/memory/count", response_model=CountResponse)
    async def count_memories(user: dict = Depends(get_current_user)):
        """Return total count of embeddings for the user."""
        try:
            count = await memory_engine.vector_store.get_embedding_count(
                tenant_id=user["tenant_id"],
                user_id=user["user_id"],
            )
            return CountResponse(count=count)
        except Exception as e:
            logger.error("count_memories_failed", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))

    # ── Temporal / Graphiti endpoints ─────────────────────────────────

    @app.post("/api/memory/search/temporal", response_model=TemporalSearchResponse)
    async def temporal_search(
        request: TemporalSearchRequest,
        user: dict = Depends(get_current_user),
    ):
        """
        Bi-temporal «time-travel» search.

        When `as_of` is provided, returns what the system knew at that
        point in time.  Otherwise behaves like a normal hybrid search
        powered by the Graphiti knowledge graph.
        """
        try:
            as_of_dt = None
            if request.as_of:
                as_of_dt = datetime.fromisoformat(request.as_of)

            hits = await memory_engine.search_temporal(
                query=request.query,
                tenant_id=user["tenant_id"],
                as_of=as_of_dt,
                limit=request.limit,
            )

            return TemporalSearchResponse(
                results=[
                    TemporalHit(
                        id=h.id,
                        text=h.text,
                        score=h.score,
                        event_time=h.event_time.isoformat() if h.event_time else None,
                        ingestion_time=h.ingestion_time.isoformat() if h.ingestion_time else None,
                        source=h.source,
                        graph_score=h.graph_score,
                    )
                    for h in hits
                ],
                as_of=request.as_of,
            )
        except Exception as e:
            logger.error("temporal_search_failed", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/memory/entity/history", response_model=EntityHistoryResponse)
    async def entity_history(
        request: EntityHistoryRequest,
        user: dict = Depends(get_current_user),
    ):
        """Retrieve every recorded version of a named entity."""
        try:
            versions = await memory_engine.get_entity_history(
                entity_name=request.entity_name,
                tenant_id=user["tenant_id"],
            )
            return EntityHistoryResponse(
                entity_name=request.entity_name,
                versions=[
                    EntityVersionOut(
                        entity_id=v.entity_id,
                        name=v.name,
                        properties=v.properties,
                        valid_from=v.valid_from.isoformat(),
                        valid_until=v.valid_until.isoformat() if v.valid_until else None,
                    )
                    for v in versions
                ],
            )
        except Exception as e:
            logger.error("entity_history_failed", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/memory/graph", response_model=GraphDataResponse)
    async def graph_data(
        user: dict = Depends(get_current_user),
        limit: int = 200,
    ):
        """Return nodes & edges for the interactive graph dashboard."""
        try:
            data = await memory_engine.get_graph_data(
                tenant_id=user["tenant_id"],
                limit=limit,
            )
            return GraphDataResponse(nodes=data["nodes"], edges=data["edges"])
        except Exception as e:
            logger.error("graph_data_failed", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/capture", response_model=CaptureResponse)
    async def capture_conversation(
        request: CaptureRequest,
        user: dict = Depends(get_current_user),
    ):
        """
        Browser extension hook — accepts a ChatGPT / Claude conversation
        payload and ingests each message as a temporal episode.
        """
        try:
            count = 0
            for msg in request.conversation:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if not content:
                    continue

                await memory_engine.store_with_conflict_resolution(
                    observation=content,
                    metadata={
                        "source": request.source,
                        "role": role,
                        "url": request.url or "",
                        "title": request.title or "",
                    },
                    tenant_id=user["tenant_id"],
                    user_id=user["user_id"],
                )
                count += 1

            return CaptureResponse(
                episodes_ingested=count,
                message=f"Captured {count} messages from {request.source}",
            )
        except Exception as e:
            logger.error("capture_conversation_failed", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))

    return app
