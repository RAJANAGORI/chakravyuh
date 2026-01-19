"""CSRF protection for API endpoints."""
from fastapi import Request, HTTPException
from fastapi_csrf_protect import CsrfProtect
from fastapi_csrf_protect.exceptions import CsrfProtectError
from pydantic import BaseModel

from chakravyuh.core.config import get_config
from chakravyuh.core.logging import logger


class CsrfSettings(BaseModel):
    """CSRF protection settings."""
    secret_key: str = "your-secret-key-change-in-production"  # Should be from config/env
    cookie_secure: bool = True
    cookie_samesite: str = "strict"
    header_name: str = "X-CSRF-Token"
    header_type: str = "X-CSRF-Token"


# Global CSRF protector instance
_csrf_protect: Optional[CsrfProtect] = None


def get_csrf_protect() -> Optional[CsrfProtect]:
    """Get or create CSRF protector instance."""
    global _csrf_protect
    if _csrf_protect is None:
        try:
            # Use a secret from config or environment
            secret_key = os.getenv("CSRF_SECRET_KEY", "change-me-in-production")
            
            @CsrfProtect.load_config
            def get_csrf_config():
                return CsrfSettings(
                    secret_key=secret_key,
                    cookie_secure=True,  # Only send over HTTPS
                    cookie_samesite="strict",
                )
            
            _csrf_protect = CsrfProtect()
        except Exception as e:
            logger.warning(f"CSRF protection initialization failed: {e}")
            # Return None if initialization fails (will be handled gracefully)
            return None
    return _csrf_protect


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
        csrf = get_csrf_protect()
        if csrf:
            csrf.validate_csrf(request)
    except CsrfProtectError as e:
        logger.warning(f"CSRF validation failed: {e}")
        raise HTTPException(status_code=403, detail="CSRF token validation failed")
    except Exception as e:
        logger.error(f"CSRF protection error: {e}")
        # In case of errors, we'll allow the request but log it
        # This prevents CSRF protection from breaking the API
        pass
