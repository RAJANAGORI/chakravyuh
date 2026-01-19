"""Audit logging for security and compliance."""
import json
import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
from enum import Enum

from chakravyuh.core.logging import logger


class AuditEventType(str, Enum):
    """Types of audit events."""
    QUERY = "query"
    THREAT_MODEL = "threat_model"
    DOCUMENT_ACCESS = "document_access"
    DOCUMENT_INGEST = "document_ingest"
    ACCESS_DENIED = "access_denied"
    INJECTION_DETECTED = "injection_detected"
    CONFIG_CHANGE = "config_change"


class AuditLogger:
    """Comprehensive audit logging for compliance."""

    def __init__(self, log_dir: str = "./logs/audit"):
        """
        Initialize audit logger.

        Args:
            log_dir: Directory for audit logs
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def log_event(
        self,
        event_type: AuditEventType,
        user_id: str,
        details: Dict[str, Any],
        resource_id: Optional[str] = None,
        success: bool = True,
    ) -> None:
        """
        Log an audit event.

        Args:
            event_type: Type of event
            user_id: User identifier
            details: Event details
            resource_id: Optional resource identifier
            success: Whether the operation succeeded
        """
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type.value,
            "user_id": user_id,
            "resource_id": resource_id,
            "success": success,
            "details": details,
        }

        # Log to file with secure permissions
        log_file = self.log_dir / f"audit_{datetime.utcnow().strftime('%Y-%m-%d')}.jsonl"
        
        # Ensure log directory has secure permissions (0700)
        if self.log_dir.exists():
            os.chmod(self.log_dir, 0o700)
        
        # Write to file
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
        
        # Set secure file permissions: 0600 (rw-------) - owner read/write only
        os.chmod(log_file, 0o600)

        # Log to application logger
        if success:
            logger.info(f"Audit: {event_type.value} by {user_id} - {details.get('action', 'unknown')}")
        else:
            logger.warning(f"Audit: {event_type.value} by {user_id} - {details.get('action', 'unknown')}")

    def log_query(
        self,
        user_id: str,
        query: str,
        response_length: int,
        sources_used: List[str],
        structured: bool = False,
    ) -> None:
        """
        Log a query event with PII sanitization.

        Args:
            user_id: User identifier
            query: Query text
            response_length: Length of response
            sources_used: List of source document IDs
            structured: Whether structured output was requested
        """
        # Sanitize query to remove PII before logging
        sanitized_query = self._sanitize_query_for_logging(query[:500])
        
        self.log_event(
            event_type=AuditEventType.QUERY,
            user_id=user_id,
            details={
                "query": sanitized_query,  # Sanitized query
                "query_length": len(query),  # Log length instead of full query
                "response_length": response_length,
                "sources_count": len(sources_used),
                "sources": sources_used[:10],  # Limit to first 10
                "structured": structured,
            },
        )
    
    def _sanitize_query_for_logging(self, query: str) -> str:
        """
        Sanitize query text to remove potential PII and sensitive data.
        
        Args:
            query: Query text to sanitize
            
        Returns:
            Sanitized query text
        """
        import re
        
        # Remove email addresses
        query = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REDACTED]', query)
        
        # Remove potential API keys (patterns like sk-..., ls-..., etc.)
        query = re.sub(r'\b(sk-|ls-|pk-|ak-)[A-Za-z0-9_-]{20,}\b', '[API_KEY_REDACTED]', query)
        
        # Remove potential passwords (words followed by colon and alphanumeric)
        query = re.sub(r'\b(password|passwd|pwd|secret|token|key)\s*[:=]\s*[^\s]{8,}', r'\1=[REDACTED]', query, flags=re.IGNORECASE)
        
        # Remove potential credit card numbers (16 digits with optional spaces/dashes)
        query = re.sub(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CARD_REDACTED]', query)
        
        # Remove potential SSN (XXX-XX-XXXX format)
        query = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN_REDACTED]', query)
        
        # Remove potential IP addresses (basic pattern)
        query = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP_REDACTED]', query)
        
        return query

    def log_threat_model(
        self,
        user_id: str,
        threat_model_id: str,
        scope: str,
        risks_identified: int,
    ) -> None:
        """
        Log threat model creation.

        Args:
            user_id: User identifier
            threat_model_id: Threat model identifier
            scope: Threat model scope
            risks_identified: Number of risks identified
        """
        self.log_event(
            event_type=AuditEventType.THREAT_MODEL,
            user_id=user_id,
            resource_id=threat_model_id,
            details={
                "scope": scope,
                "risks_identified": risks_identified,
            },
        )

    def log_access_denied(
        self,
        user_id: str,
        resource_id: str,
        permission: str,
        reason: str,
    ) -> None:
        """
        Log access denied event.

        Args:
            user_id: User identifier
            resource_id: Resource identifier
            permission: Required permission
            reason: Reason for denial
        """
        self.log_event(
            event_type=AuditEventType.ACCESS_DENIED,
            user_id=user_id,
            resource_id=resource_id,
            success=False,
            details={
                "permission": permission,
                "reason": reason,
            },
        )

    def log_injection_detected(
        self,
        user_id: str,
        injection_type: str,
        query: str,
    ) -> None:
        """
        Log detected injection attack.

        Args:
            user_id: User identifier
            injection_type: Type of injection
            query: Query that triggered detection
        """
        self.log_event(
            event_type=AuditEventType.INJECTION_DETECTED,
            user_id=user_id,
            success=False,
            details={
                "injection_type": injection_type,
                "query": query[:200],  # Truncate
            },
        )

    def get_events(
        self,
        user_id: Optional[str] = None,
        event_type: Optional[AuditEventType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve audit events with filters.

        Args:
            user_id: Filter by user ID
            event_type: Filter by event type
            start_date: Start date filter
            end_date: End date filter
            limit: Maximum number of events

        Returns:
            List of audit events
        """
        events = []

        # Read from all log files in date range
        for log_file in sorted(self.log_dir.glob("audit_*.jsonl")):
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue

                    try:
                        event = json.loads(line)
                        event_time = datetime.fromisoformat(event["timestamp"])

                        # Apply filters
                        if user_id and event.get("user_id") != user_id:
                            continue
                        if event_type and event.get("event_type") != event_type.value:
                            continue
                        if start_date and event_time < start_date:
                            continue
                        if end_date and event_time > end_date:
                            continue

                        events.append(event)

                        if len(events) >= limit:
                            return events

                    except Exception as e:
                        logger.error(f"Error parsing audit log line: {e}")

        return events
