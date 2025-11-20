"""Request ID tracking middleware"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import uuid
import logging

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to each request for tracking"""
    
    async def dispatch(self, request: Request, call_next):
        # Generate or use existing request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        
        # Add to request state for use in routes/services
        request.state.request_id = request_id
        
        # Add to response headers
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        
        # Log request with ID
        logger.info(f"Request {request_id}: {request.method} {request.url.path}")
        
        return response

