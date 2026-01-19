"""Map threats to security frameworks (CIA/AAA/STRIDE/OWASP)."""
from typing import List, Dict, Optional
from enum import Enum

from chakravyuh.knowledge_graph.graph.models import ThreatNode, NodeType
from chakravyuh.core.logging import logger


class Framework(str, Enum):
    """Security frameworks."""
    CIA = "CIA"
    AAA = "AAA"
    STRIDE = "STRIDE"
    OWASP_TOP_10 = "OWASP_TOP_10"


class CIACategory(str, Enum):
    """CIA categories."""
    CONFIDENTIALITY = "confidentiality"
    INTEGRITY = "integrity"
    AVAILABILITY = "availability"


class AAACategory(str, Enum):
    """AAA categories."""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    ACCOUNTING = "accounting"


class STRIDECategory(str, Enum):
    """STRIDE categories."""
    SPOOFING = "spoofing"
    TAMPERING = "tampering"
    REPUDIATION = "repudiation"
    INFORMATION_DISCLOSURE = "information_disclosure"
    DENIAL_OF_SERVICE = "denial_of_service"
    ELEVATION_OF_PRIVILEGE = "elevation_of_privilege"


class FrameworkMapper:
    """Map threats to security frameworks."""

    def __init__(self):
        """Initialize framework mapper with keyword mappings."""
        # CIA mappings
        self.cia_keywords = {
            CIACategory.CONFIDENTIALITY: [
                "data breach", "leak", "exposure", "unauthorized access",
                "encryption", "privacy", "confidential", "secret", "pii", "phi"
            ],
            CIACategory.INTEGRITY: [
                "tamper", "modify", "alter", "corrupt", "unauthorized change",
                "data integrity", "validation", "checksum", "hash"
            ],
            CIACategory.AVAILABILITY: [
                "denial of service", "dos", "ddos", "downtime", "outage",
                "unavailable", "service disruption", "resource exhaustion"
            ],
        }

        # AAA mappings
        self.aaa_keywords = {
            AAACategory.AUTHENTICATION: [
                "authentication", "login", "credential", "password", "mfa",
                "identity", "user verification", "session", "token"
            ],
            AAACategory.AUTHORIZATION: [
                "authorization", "permission", "access control", "rbac",
                "privilege", "role", "policy", "acl"
            ],
            AAACategory.ACCOUNTING: [
                "audit", "logging", "accounting", "tracking", "monitoring",
                "compliance", "forensics", "audit trail"
            ],
        }

        # STRIDE mappings
        self.stride_keywords = {
            STRIDECategory.SPOOFING: [
                "spoof", "impersonate", "fake", "masquerade", "identity theft"
            ],
            STRIDECategory.TAMPERING: [
                "tamper", "modify", "alter", "manipulate", "change"
            ],
            STRIDECategory.REPUDIATION: [
                "repudiate", "deny", "non-repudiation", "audit", "proof"
            ],
            STRIDECategory.INFORMATION_DISCLOSURE: [
                "disclosure", "leak", "expose", "reveal", "information leak"
            ],
            STRIDECategory.DENIAL_OF_SERVICE: [
                "dos", "ddos", "denial", "unavailable", "outage"
            ],
            STRIDECategory.ELEVATION_OF_PRIVILEGE: [
                "privilege escalation", "elevation", "unauthorized access",
                "root", "admin", "sudo"
            ],
        }

    def map_to_cia(self, threat: ThreatNode) -> List[CIACategory]:
        """
        Map threat to CIA categories.

        Args:
            threat: Threat node

        Returns:
            List of CIA categories this threat affects
        """
        categories = []
        text = f"{threat.name} {threat.description or ''}".lower()

        for category, keywords in self.cia_keywords.items():
            if any(keyword in text for keyword in keywords):
                categories.append(category)

        return categories if categories else [CIACategory.CONFIDENTIALITY]  # Default

    def map_to_aaa(self, threat: ThreatNode) -> List[AAACategory]:
        """
        Map threat to AAA categories.

        Args:
            threat: Threat node

        Returns:
            List of AAA categories this threat affects
        """
        categories = []
        text = f"{threat.name} {threat.description or ''}".lower()

        for category, keywords in self.aaa_keywords.items():
            if any(keyword in text for keyword in keywords):
                categories.append(category)

        return categories

    def map_to_stride(self, threat: ThreatNode) -> List[STRIDECategory]:
        """
        Map threat to STRIDE categories.

        Args:
            threat: Threat node

        Returns:
            List of STRIDE categories this threat matches
        """
        categories = []
        text = f"{threat.name} {threat.description or ''}".lower()

        for category, keywords in self.stride_keywords.items():
            if any(keyword in text for keyword in keywords):
                categories.append(category)

        return categories

    def map_to_owasp_top10(self, threat: ThreatNode) -> Optional[str]:
        """
        Map threat to OWASP Top 10 category.

        Args:
            threat: Threat node

        Returns:
            OWASP Top 10 category ID or None
        """
        # OWASP Top 10 2021 categories
        owasp_mappings = {
            "A01:2021-Broken Access Control": [
                "access control", "authorization", "permission", "rbac", "privilege"
            ],
            "A02:2021-Cryptographic Failures": [
                "encryption", "cryptographic", "ssl", "tls", "cipher", "hash"
            ],
            "A03:2021-Injection": [
                "injection", "sql injection", "xss", "command injection", "code injection"
            ],
            "A04:2021-Insecure Design": [
                "design", "architecture", "insecure", "flawed"
            ],
            "A05:2021-Security Misconfiguration": [
                "misconfiguration", "configuration", "default", "weak"
            ],
            "A06:2021-Vulnerable Components": [
                "vulnerable", "component", "dependency", "library", "outdated"
            ],
            "A07:2021-Authentication Failures": [
                "authentication", "login", "credential", "password", "session"
            ],
            "A08:2021-Software and Data Integrity": [
                "integrity", "ci/cd", "supply chain", "update", "patch"
            ],
            "A09:2021-Security Logging Failures": [
                "logging", "audit", "monitoring", "detection", "forensics"
            ],
            "A10:2021-Server-Side Request Forgery": [
                "ssrf", "server-side request", "internal", "local"
            ],
        }

        text = f"{threat.name} {threat.description or ''}".lower()

        for category, keywords in owasp_mappings.items():
            if any(keyword in text for keyword in keywords):
                return category

        return None

    def map_threat(self, threat: ThreatNode) -> Dict[str, any]:
        """
        Map threat to all frameworks.

        Args:
            threat: Threat node

        Returns:
            Dictionary with framework mappings
        """
        return {
            "cia": [cat.value for cat in self.map_to_cia(threat)],
            "aaa": [cat.value for cat in self.map_to_aaa(threat)],
            "stride": [cat.value for cat in self.map_to_stride(threat)],
            "owasp_top10": self.map_to_owasp_top10(threat),
        }
