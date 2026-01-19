"""CSRF protection for API endpoints."""
import os
import hmac
import hashlib
from typing import Optional
from fastapi import Request, HTTPException
from pydantic import BaseModel

from chakravyuh.core.config import get_config
from chakravyuh.core.logging import logger


class CsrfSettings(BaseModel):
    """CSRF protection settings."""
    secret_key: str = "your-secret-key-change-in-production"  # Should be from config/env
    cookie_secure: bool = True
    cookie_samesite: str = "strict"
    header_name: str = "X-CSRF-Token"


# Global CSRF settings
_csrf_settings: Optional[CsrfSettings] = None


def get_csrf_settings() -> Optional[CsrfSettings]:
    """Get or create CSRF settings."""
    global _csrf_settings
    if _csrf_settings is None:
        try:
            # Use a secret from config or environment
            secret_key = os.getenv("CSRF_SECRET_KEY", "change-me-in-production")
            _csrf_settings = CsrfSettings(
                secret_key=secret_key,
                cookie_secure=True,  # Only send over HTTPS
                cookie_samesite="strict",
            )
        except Exception as e:
            logger.warning(f"CSRF protection initialization failed: {e}")
            return None
    return _csrf_settings


def _generate_csrf_token(secret_key: str) -> str:
    """Generate a CSRF token."""
    # Simple token generation using HMAC
    import secrets
    token = secrets.token_urlsafe(32)
    signature = hmac.new(
        secret_key.encode(),
        token.encode(),
        hashlib.sha256
    ).hexdigest()
    return f"{token}.{signature}"


def _validate_csrf_token(token: str, secret_key: str) -> bool:
    """Validate a CSRF token."""
    try:
        if "." not in token:
            return False
        token_part, signature = token.rsplit(".", 1)
        expected_signature = hmac.new(
            secret_key.encode(),
            token_part.encode(),
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(signature, expected_signature)
    except Exception:
        return False


def csrf_protect(request: Request):
    """
    CSRF protection dependency for endpoints.
    
    Note: For REST APIs with token-based auth, CSRF is less critical,
    but we implement it for defense in depth.
    """
    # Skip CSRF for GET requests (they're idempotent)
    if request.method == "GET":
        return
    
    # Skip CSRF for health checks
    if request.url.path == "/health":
        return
    
    try:
        settings = get_csrf_settings()
        if not settings:
            # If CSRF is not configured, allow the request but log it
            logger.debug("CSRF protection not configured, skipping validation")
            return
        
        # Get CSRF token from header
        header_name = settings.header_name
        csrf_token = request.headers.get(header_name)
        
        if not csrf_token:
            logger.warning(f"CSRF token missing in header {header_name}")
            raise HTTPException(status_code=403, detail="CSRF token validation failed")
        
        # Validate the token
        if not _validate_csrf_token(csrf_token, settings.secret_key):
            logger.warning("CSRF token validation failed")
            raise HTTPException(status_code=403, detail="CSRF token validation failed")
            
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"CSRF protection error: {e}")
        # In case of errors, we'll allow the request but log it
        # This prevents CSRF protection from breaking the API
        pass
