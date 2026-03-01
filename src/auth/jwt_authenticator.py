"""JWT authentication for MCP requests."""

from datetime import datetime, timedelta

import jwt
import structlog

from src.config import config
from src.models import AuthenticationError

logger = structlog.get_logger()


class JWTAuthenticator:
    """
    JWT token validation and claims extraction.
    """

    def __init__(self, secret: str = "", algorithm: str = ""):
        self.secret = secret or config.jwt_secret
        self.algorithm = algorithm or config.jwt_algorithm

    def validate_token(self, token: str) -> dict[str, str]:
        """
        Validate JWT token and extract claims.

        Args:
            token: JWT token string

        Returns:
            Dictionary with tenant_id and user_id

        Raises:
            AuthenticationError: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token,
                self.secret,
                algorithms=[self.algorithm],
            )

            tenant_id = payload.get("tenant_id")
            user_id = payload.get("user_id")

            if not tenant_id or not user_id:
                raise AuthenticationError("Token missing tenant_id or user_id")

            logger.info(
                "token_validated",
                tenant_id=tenant_id,
                user_id=user_id,
            )

            return {
                "tenant_id": tenant_id,
                "user_id": user_id,
            }

        except jwt.ExpiredSignatureError:
            logger.warning("token_expired")
            raise AuthenticationError("Token expired")
        except jwt.InvalidTokenError as e:
            logger.warning("token_invalid", error=str(e))
            raise AuthenticationError(f"Invalid token: {str(e)}")

    def generate_token(
        self,
        tenant_id: str,
        user_id: str,
        expires_in_hours: int = 24,
    ) -> str:
        """
        Generate JWT token for testing.

        Args:
            tenant_id: Tenant identifier
            user_id: User identifier
            expires_in_hours: Token expiration time

        Returns:
            JWT token string
        """
        payload = {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "exp": datetime.utcnow() + timedelta(hours=expires_in_hours),
            "iat": datetime.utcnow(),
        }

        token = jwt.encode(payload, self.secret, algorithm=self.algorithm)

        logger.info(
            "token_generated",
            tenant_id=tenant_id,
            user_id=user_id,
            expires_in_hours=expires_in_hours,
        )

        return token
