"""FastAPI HTTP server for ChronosMCP."""

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
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
        title="ChronosMCP API",
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

    return app
