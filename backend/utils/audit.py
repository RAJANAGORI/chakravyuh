import json
import logging
from typing import Any, Dict

from fastapi import Request


_logger = logging.getLogger("chakravyuh.audit")


def _request_meta(request: Request) -> Dict[str, Any]:
    return {
        "method": request.method,
        "path": str(request.url.path),
        "client_ip": request.client.host if request.client else "unknown",
        "request_id": request.headers.get("X-Request-Id", ""),
    }


def audit_event(request: Request, event: str, subject: str, **extra: Any) -> None:
    payload: Dict[str, Any] = {
        "event": event,
        "subject": subject,
        **_request_meta(request),
        **extra,
    }
    _logger.info(json.dumps(payload, default=str))
