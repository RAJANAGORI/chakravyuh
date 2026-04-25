import os
import time
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import jwt
from dotenv import load_dotenv
from fastapi import HTTPException, Request, status
from jwt import InvalidTokenError

# Load backend/.env for uvicorn and tests (Makefile also sources .env, but not all runners do).
_env_file = Path(__file__).resolve().parent.parent / ".env"
if _env_file.is_file():
    load_dotenv(_env_file)

_log = logging.getLogger(__name__)


@dataclass
class AuthContext:
    subject: str
    claims: Dict[str, Any]


def _as_bool(value: Optional[str], default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _has_jwt_key() -> bool:
    return bool(
        (os.getenv("JWT_SECRET") or "").strip() or (os.getenv("JWT_PUBLIC_KEY") or "").strip()
    )


def is_auth_enabled() -> bool:
    """
    JWT auth is on only when AUTH_ENABLED is true (default) *and* a verification key is set.
    This avoids 500s when a browser sends a Bearer token but the API has no JWT_SECRET yet.
    """
    if not _as_bool(os.getenv("AUTH_ENABLED"), True):
        return False
    if not _has_jwt_key():
        raw = (os.getenv("AUTH_ENABLED") or "").strip().lower()
        if raw in {"1", "true", "yes", "on"}:
            _log.warning(
                "AUTH_ENABLED=true but JWT_SECRET/JWT_PUBLIC_KEY is missing; auth disabled until a key is configured."
            )
        return False
    return True


def _extract_bearer_token(request: Request) -> str:
    header = request.headers.get("Authorization", "").strip()
    if not header.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header.",
        )
    token = header[7:].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token is empty.",
        )
    return token


def _decode_token(token: str) -> Dict[str, Any]:
    secret = (os.getenv("JWT_SECRET") or "").strip()
    public_key = (os.getenv("JWT_PUBLIC_KEY") or "").strip()
    issuer = (os.getenv("JWT_ISSUER") or "").strip()
    audience = (os.getenv("JWT_AUDIENCE") or "").strip()
    algorithm = (os.getenv("JWT_ALGORITHM") or "HS256").strip()

    if not secret and not public_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Auth is enabled but JWT verification key is not configured.",
        )

    key = public_key or secret
    # jwt.io’s sample token has no "exp"; require it in production only.
    required: list[str] = ["sub"]
    if _as_bool(os.getenv("SECURITY_PRODUCTION_MODE"), False):
        required.append("exp")
    options: Dict[str, Any] = {"require": required}
    kwargs: Dict[str, Any] = {"algorithms": [algorithm], "options": options}
    if audience:
        kwargs["audience"] = audience
    if issuer:
        kwargs["issuer"] = issuer

    try:
        return jwt.decode(token, key=key, **kwargs)
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(exc)}",
        ) from exc


async def require_auth(request: Request) -> AuthContext:
    if not is_auth_enabled():
        return AuthContext(subject="anonymous-dev", claims={"auth_disabled": True})

    token = _extract_bearer_token(request)
    claims = _decode_token(token)
    subject = str(claims.get("sub") or "").strip()
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing required subject claim.",
        )
    request.state.auth_subject = subject
    request.state.auth_claims = claims
    return AuthContext(subject=subject, claims=claims)


def get_subject_or_default(request: Request) -> str:
    subject = getattr(request.state, "auth_subject", "")
    if subject:
        return str(subject)
    return "anonymous-dev"


def is_production_mode() -> bool:
    return _as_bool(os.getenv("SECURITY_PRODUCTION_MODE"), False)


def unix_now() -> int:
    return int(time.time())
