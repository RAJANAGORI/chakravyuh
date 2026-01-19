"""Adversarial attack detection and defense."""
import re
from typing import List, Optional, Dict, Any
from enum import Enum

from chakravyuh.core.logging import logger


class InjectionType(str, Enum):
    """Types of injection attacks."""
    PROMPT_INJECTION = "prompt_injection"
    SQL_INJECTION = "sql_injection"
    COMMAND_INJECTION = "command_injection"
    PATH_TRAVERSAL = "path_traversal"
    DATA_POISONING = "data_poisoning"


class AdversarialDetector:
    """Detect adversarial attacks and prompt injections."""

    def __init__(self):
        """Initialize adversarial detector with attack patterns."""
        # Enhanced prompt injection patterns
        self.prompt_injection_patterns = [
            r"(?i)(ignore|forget|disregard|skip).*(previous|above|instructions|prompt|system)",
            r"(?i)(you are|act as|pretend to be|roleplay|simulate|imagine)",
            r"(?i)(system|assistant|user|human|ai):",
            r"(?i)(new instructions|updated instructions|override|replace)",
            r"(?i)(jailbreak|dan|do anything now|unrestricted|unfiltered)",
            r"(?i)(<\|.*?\|>)",  # Special tokens
            r"(?i)(\[INST\]|\[/INST\]|\[SYSTEM\]|\[/SYSTEM\])",  # Instruction markers
            r"(?i)(###|===|---).*(instruction|prompt|system)",  # Markdown separators
            r"(?i)(begin|start).*(new|fresh|clean).*(conversation|session|chat)",
            r"(?i)(forget everything|clear memory|reset|wipe)",
            r"(?i)(show me|reveal|display|print).*(prompt|instruction|system)",
            r"(?i)(what are|what were|tell me).*(your|the).*(instruction|prompt|system)",
            r"(?i)(repeat|echo|say back).*(your|the).*(instruction|prompt)",
        ]

        # Enhanced SQL injection patterns
        self.sql_injection_patterns = [
            r"(?i)(union.*select|select.*from|insert.*into|update.*set|delete.*from)",
            r"(?i)(drop|delete|truncate|alter|create).*(table|database|schema|index)",
            r"(?i)(or|and).*['\"]?\d+['\"]?\s*[=<>]+\s*['\"]?\d+",
            r"(?i)(;|--|\#|\/\*|\*\/).*(drop|delete|insert|update|select)",
            r"(?i)(exec|execute|executive).*\(.*\)",
            r"(?i)(xp_|sp_).*\(.*\)",  # SQL Server stored procedures
            r"(?i)(pg_|plpgsql_).*\(.*\)",  # PostgreSQL functions
            r"(?i)(information_schema|sys\.|mysql\.)",  # Database metadata
            r"(?i)(1\s*=\s*1|1\s*=\s*'1'|'1'\s*=\s*'1')",  # Always true conditions
            r"(?i)(waitfor|sleep|delay).*\(.*\)",  # Time-based attacks
            r"(?i)(benchmark|pg_sleep).*\(.*\)",  # Performance-based attacks
        ]

        # Enhanced command injection patterns
        self.command_injection_patterns = [
            r"[;&|`$\(\)\{\}\[\]<>]",  # Command separators
            r"(?i)(cat|ls|pwd|whoami|id|uname|hostname|env|printenv).*[;&|`]",
            r"(?i)(rm|mv|cp|chmod|chown|mkdir|rmdir).*[\*\.]",
            r"(?i)(curl|wget|nc|netcat|ncat|telnet|ssh|scp).*http",
            r"(?i)(python|python3|perl|ruby|bash|sh|zsh).*-c.*['\"]",
            r"(?i)(eval|exec|system|popen|subprocess).*\(.*\)",
            r"(?i)(\$\{|`|\(\(|\[\[)",  # Command substitution
            r"(?i)(base64|b64encode|b64decode).*-d",
            r"(?i)(powershell|cmd|cscript|wscript).*\/",
            r"(?i)(\.\.\/|\.\.\\).*(etc|proc|sys|dev|boot)",  # Path traversal in commands
        ]

        # Enhanced path traversal patterns
        self.path_traversal_patterns = [
            r"\.\./",  # Unix path traversal
            r"\.\.\\",  # Windows path traversal
            r"\.\.%2[fF]",  # URL encoded
            r"\.\.%5[cC]",  # URL encoded backslash
            r"/etc/passwd",  # Sensitive Unix files
            r"/etc/shadow",
            r"/proc/",  # Linux proc filesystem
            r"/sys/",  # Linux sys filesystem
            r"c:\\windows\\",  # Windows system paths
            r"c:\\windows\\system32",
            r"\.\.\/\.\.\/",  # Multiple traversals
            r"\.\.\\\.\.\\",  # Multiple Windows traversals
            r"\.\.%2[fF]\.\.%2[fF]",  # URL encoded multiple
            r"\/\.\.\/",  # Absolute path with traversal
            r"\\\.\.\\",  # Windows absolute with traversal
        ]

    def detect_prompt_injection(self, text: str) -> bool:
        """
        Detect prompt injection attempts.

        Args:
            text: Input text to check

        Returns:
            True if prompt injection detected
        """
        text_lower = text.lower()

        for pattern in self.prompt_injection_patterns:
            if re.search(pattern, text):
                logger.warning(f"Prompt injection detected: {pattern}")
                return True

        return False

    def detect_sql_injection(self, text: str) -> bool:
        """
        Detect SQL injection attempts.

        Args:
            text: Input text to check

        Returns:
            True if SQL injection detected
        """
        for pattern in self.sql_injection_patterns:
            if re.search(pattern, text):
                logger.warning(f"SQL injection detected: {pattern}")
                return True

        return False

    def detect_command_injection(self, text: str) -> bool:
        """
        Detect command injection attempts.

        Args:
            text: Input text to check

        Returns:
            True if command injection detected
        """
        for pattern in self.command_injection_patterns:
            if re.search(pattern, text):
                logger.warning(f"Command injection detected: {pattern}")
                return True

        return False

    def detect_path_traversal(self, text: str) -> bool:
        """
        Detect path traversal attempts.

        Args:
            text: Input text to check

        Returns:
            True if path traversal detected
        """
        for pattern in self.path_traversal_patterns:
            if re.search(pattern, text):
                logger.warning(f"Path traversal detected: {pattern}")
                return True

        return False

    def detect_injection(self, text: str) -> Optional[InjectionType]:
        """
        Detect any type of injection attack.

        Args:
            text: Input text to check

        Returns:
            InjectionType if detected, None otherwise
        """
        if self.detect_prompt_injection(text):
            return InjectionType.PROMPT_INJECTION
        if self.detect_sql_injection(text):
            return InjectionType.SQL_INJECTION
        if self.detect_command_injection(text):
            return InjectionType.COMMAND_INJECTION
        if self.detect_path_traversal(text):
            return InjectionType.PATH_TRAVERSAL

        return None

    def sanitize_query(self, text: str) -> str:
        """
        Enhanced sanitization of user query to prevent injection.

        Args:
            text: Input text to sanitize

        Returns:
            Sanitized text
        """
        # Remove suspicious patterns
        sanitized = text
        original_length = len(text)

        # Remove special instruction markers (more comprehensive)
        sanitized = re.sub(r"(?i)(ignore|forget|disregard|skip).*(previous|above|instructions|prompt|system)", "", sanitized)
        sanitized = re.sub(r"(?i)(system|assistant|user|human|ai):", "", sanitized)
        sanitized = re.sub(r"(?i)(new instructions|updated instructions|override|replace)", "", sanitized)
        sanitized = re.sub(r"(?i)(jailbreak|dan|do anything now)", "", sanitized)

        # Remove command separators and dangerous characters
        sanitized = re.sub(r"[;&|`$]", "", sanitized)
        
        # Remove command substitution patterns
        sanitized = re.sub(r"\$\{.*?\}", "", sanitized)
        sanitized = re.sub(r"`.*?`", "", sanitized)
        sanitized = re.sub(r"\(\(.*?\)\)", "", sanitized)

        # Remove path traversal (more comprehensive)
        sanitized = re.sub(r"\.\./", "", sanitized)
        sanitized = re.sub(r"\.\.\\", "", sanitized)
        sanitized = re.sub(r"\.\.%2[fF]", "", sanitized)  # URL encoded
        sanitized = re.sub(r"\.\.%5[cC]", "", sanitized)  # URL encoded backslash
        
        # Remove multiple consecutive path traversals
        sanitized = re.sub(r"(\.\./)+", "", sanitized)
        sanitized = re.sub(r"(\.\.\\)+", "", sanitized)

        # Remove SQL injection patterns
        sanitized = re.sub(r"(?i)(union.*select|select.*from)", "", sanitized)
        sanitized = re.sub(r"(?i)(drop|delete|truncate).*(table|database)", "", sanitized)
        sanitized = re.sub(r"(?i)(;|--|\#).*(drop|delete|insert|update)", "", sanitized)

        # Remove suspicious file paths
        sanitized = re.sub(r"/etc/(passwd|shadow|hosts)", "", sanitized)
        sanitized = re.sub(r"/proc/", "", sanitized)
        sanitized = re.sub(r"c:\\windows\\", "", sanitized, flags=re.IGNORECASE)

        # Trim whitespace and normalize
        sanitized = sanitized.strip()
        # Remove excessive whitespace
        sanitized = re.sub(r"\s+", " ", sanitized)

        if sanitized != text:
            removed = original_length - len(sanitized)
            logger.info(f"Sanitized query: removed {removed} suspicious characters/patterns")
            
            # If too much was removed, it might be a malicious query
            if removed > len(text) * 0.3:  # More than 30% removed
                logger.warning(f"Extensive sanitization required - possible attack: {text[:100]}")

        return sanitized

    def check_data_poisoning(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Check documents for data poisoning indicators.

        Args:
            documents: List of document dictionaries

        Returns:
            List of suspicious documents with metadata
        """
        suspicious = []

        for doc in documents:
            content = doc.get("content", "") or doc.get("page_content", "")
            metadata = doc.get("metadata", {})

            # Check for suspicious patterns
            if self.detect_prompt_injection(content):
                suspicious.append({
                    "document": doc,
                    "reason": "Contains prompt injection patterns",
                    "severity": "high",
                })

            # Check for unusual metadata
            if "source" not in metadata or not metadata.get("source"):
                suspicious.append({
                    "document": doc,
                    "reason": "Missing source information",
                    "severity": "medium",
                })

        if suspicious:
            logger.warning(f"Detected {len(suspicious)} potentially poisoned documents")

        return suspicious
