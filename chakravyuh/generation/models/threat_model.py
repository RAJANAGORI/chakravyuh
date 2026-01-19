"""Threat modeling data models."""
from typing import List
from pydantic import BaseModel, Field


class RiskItem(BaseModel):
    """Risk item with impact and mitigations."""
    risk: str
    impact: str
    likelihood: str
    mitigations: List[str] = Field(default_factory=list)


class CIASection(BaseModel):
    """CIA (Confidentiality, Integrity, Availability) section."""
    confidentiality: List[RiskItem] = Field(default_factory=list)
    integrity: List[RiskItem] = Field(default_factory=list)
    availability: List[RiskItem] = Field(default_factory=list)


class AAASection(BaseModel):
    """AAA (Authentication, Authorization, Accounting) section."""
    authentication: List[RiskItem] = Field(default_factory=list)
    authorization: List[RiskItem] = Field(default_factory=list)
    accounting: List[RiskItem] = Field(default_factory=list)


class ThreatModelReport(BaseModel):
    """Structured threat model report."""
    scope_summary: str
    cia: CIASection
    aaa: AAASection
    key_controls: List[str] = Field(default_factory=list)
    residual_risk_rating: str
    assumptions: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)  # URLs or titles
