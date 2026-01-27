"""Middleware for correlation IDs and service-to-service authentication."""
import uuid
import time
import jwt
from datetime import datetime, timedelta
from typing import Optional, Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# =============================================================================
# Correlation ID Middleware
# =============================================================================

CORRELATION_ID_HEADER = "X-Request-ID"
CORRELATION_ID_KEY = "correlation_id"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle correlation IDs for request tracing.

    - Extracts X-Request-ID from incoming requests
    - Generates a new ID if not present
    - Adds the ID to response headers
    - Makes the ID available in request state
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get or generate correlation ID
        correlation_id = request.headers.get(CORRELATION_ID_HEADER)
        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        # Store in request state for access in handlers
        request.state.correlation_id = correlation_id

        # Process request
        response = await call_next(request)

        # Add correlation ID to response
        response.headers[CORRELATION_ID_HEADER] = correlation_id

        return response


def get_correlation_id(request: Request) -> str:
    """Get correlation ID from request state."""
    return getattr(request.state, "correlation_id", str(uuid.uuid4()))


# =============================================================================
# Service-to-Service JWT Authentication
# =============================================================================

SERVICE_JWT_HEADER = "X-Service-Token"
SERVICE_JWT_SECRET = settings.DEFAULT_API_KEY  # Use API key as JWT secret for simplicity
SERVICE_JWT_ALGORITHM = "HS256"
SERVICE_JWT_EXPIRY_MINUTES = 5


class ServiceToken:
    """Service-to-service JWT token utilities."""

    @staticmethod
    def generate(
        service_name: str,
        target_service: str = "*",
        expiry_minutes: int = SERVICE_JWT_EXPIRY_MINUTES,
    ) -> str:
        """
        Generate a JWT token for service-to-service calls.

        Args:
            service_name: Name of the calling service
            target_service: Target service (* for any)
            expiry_minutes: Token validity in minutes

        Returns:
            JWT token string
        """
        payload = {
            "iss": service_name,
            "aud": target_service,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(minutes=expiry_minutes),
            "type": "service",
        }
        return jwt.encode(payload, SERVICE_JWT_SECRET, algorithm=SERVICE_JWT_ALGORITHM)

    @staticmethod
    def validate(token: str, expected_service: str = None) -> Optional[dict]:
        """
        Validate a service JWT token.

        Args:
            token: JWT token to validate
            expected_service: Expected issuing service (optional)

        Returns:
            Token payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                SERVICE_JWT_SECRET,
                algorithms=[SERVICE_JWT_ALGORITHM],
            )

            # Check token type
            if payload.get("type") != "service":
                logger.warning("Invalid token type")
                return None

            # Check issuer if specified
            if expected_service and payload.get("iss") != expected_service:
                logger.warning(f"Unexpected service: {payload.get('iss')}")
                return None

            return payload

        except jwt.ExpiredSignatureError:
            logger.warning("Service token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid service token: {e}")
            return None


class ServiceAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware for service-to-service authentication.

    Validates X-Service-Token header on internal routes.
    """

    def __init__(self, app, internal_paths: list[str] = None):
        super().__init__(app)
        self.internal_paths = internal_paths or ["/internal/"]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check if this is an internal route
        path = request.url.path
        is_internal = any(path.startswith(p) for p in self.internal_paths)

        if is_internal:
            # Require service token for internal routes
            token = request.headers.get(SERVICE_JWT_HEADER)
            if not token:
                logger.warning(f"Missing service token for internal route: {path}")
                return Response(
                    content='{"error": "Service token required"}',
                    status_code=401,
                    media_type="application/json",
                )

            payload = ServiceToken.validate(token)
            if not payload:
                return Response(
                    content='{"error": "Invalid service token"}',
                    status_code=401,
                    media_type="application/json",
                )

            # Store service info in request state
            request.state.calling_service = payload.get("iss")

        return await call_next(request)


# =============================================================================
# Request Logging Middleware
# =============================================================================


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all requests with correlation IDs and timing.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        # Get correlation ID (should be set by CorrelationIdMiddleware)
        correlation_id = getattr(request.state, "correlation_id", "unknown")

        # Log request
        logger.info(
            f"Request started",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "client_ip": request.client.host if request.client else "unknown",
            }
        )

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log response
        logger.info(
            f"Request completed",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            }
        )

        # Add timing header
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

        return response


# =============================================================================
# Audit Logging (to database)
# =============================================================================


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log requests to the audit database.

    This is async and non-blocking - failures don't affect the request.
    """

    def __init__(self, app, enabled: bool = True, exclude_paths: list[str] = None):
        super().__init__(app)
        self.enabled = enabled
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/docs", "/openapi.json"]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.enabled:
            return await call_next(request)

        # Skip excluded paths
        if any(request.url.path.startswith(p) for p in self.exclude_paths):
            return await call_next(request)

        start_time = time.time()
        correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log to audit (fire and forget - don't block response)
        try:
            await self._log_to_audit(
                request=request,
                response=response,
                correlation_id=correlation_id,
                duration_ms=duration_ms,
            )
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

        return response

    async def _log_to_audit(
        self,
        request: Request,
        response: Response,
        correlation_id: str,
        duration_ms: float,
    ):
        """Write request to audit log table."""
        # Import here to avoid circular imports
        from app.core.database import AsyncSessionLocal
        from sqlalchemy import text
        import json

        async with AsyncSessionLocal() as session:
            await session.execute(
                text("""
                    INSERT INTO audit.api_requests (
                        request_id, source_service, source_ip, method, path,
                        query_params, request_headers, response_status, latency_ms
                    ) VALUES (
                        CAST(:request_id AS uuid), :source_service, :source_ip, :method, :path,
                        CAST(:query_params AS jsonb), CAST(:headers AS jsonb), :status, :latency_ms
                    )
                """),
                {
                    "request_id": correlation_id,
                    "source_service": getattr(request.state, "calling_service", None),
                    "source_ip": request.client.host if request.client else None,
                    "method": request.method,
                    "path": request.url.path,
                    "query_params": json.dumps(dict(request.query_params)),
                    "headers": json.dumps({"user-agent": request.headers.get("user-agent")}),
                    "status": response.status_code,
                    "latency_ms": round(duration_ms, 2),
                },
            )
            await session.commit()
