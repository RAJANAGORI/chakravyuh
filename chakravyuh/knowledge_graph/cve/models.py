"""CVE and CWE data models."""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class CWE(BaseModel):
    """Common Weakness Enumeration."""
    cwe_id: str  # e.g., "CWE-79"
    name: str
    description: str
    weakness_abstraction: Optional[str] = None  # "Base", "Variant", "Class", "Pillar"
    status: Optional[str] = None  # "Draft", "Incomplete", "Stable"
    related_weaknesses: List[str] = Field(default_factory=list)
    related_cves: List[str] = Field(default_factory=list)
    attack_techniques: List[str] = Field(default_factory=list)  # MITRE ATT&CK technique IDs


class CVE(BaseModel):
    """Common Vulnerabilities and Exposures."""
    cve_id: str  # e.g., "CVE-2024-1234"
    description: str
    published_date: Optional[datetime] = None
    modified_date: Optional[datetime] = None
    cvss_score: Optional[float] = None
    cvss_severity: Optional[str] = None  # "CRITICAL", "HIGH", "MEDIUM", "LOW"
    affected_products: List[str] = Field(default_factory=list)
    cwe_ids: List[str] = Field(default_factory=list)
    attack_techniques: List[str] = Field(default_factory=list)  # MITRE ATT&CK technique IDs
    references: List[str] = Field(default_factory=list)
    mitigations: List[str] = Field(default_factory=list)
