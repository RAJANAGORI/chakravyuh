"""MITRE ATT&CK data models."""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class ATTACKTechnique(BaseModel):
    """MITRE ATT&CK Technique."""
    technique_id: str  # e.g., "T1001"
    name: str
    description: str
    tactics: List[str] = Field(default_factory=list)  # e.g., ["Initial Access", "Execution"]
    platforms: List[str] = Field(default_factory=list)  # e.g., ["Windows", "Linux"]
    kill_chain_phases: List[str] = Field(default_factory=list)
    data_sources: List[str] = Field(default_factory=list)
    detection_rules: List[str] = Field(default_factory=list)
    mitigations: List[str] = Field(default_factory=list)
    references: List[str] = Field(default_factory=list)
    created: Optional[datetime] = None
    modified: Optional[datetime] = None


class ATTACKTactic(BaseModel):
    """MITRE ATT&CK Tactic."""
    tactic_id: str  # e.g., "TA0001"
    name: str
    description: str
    techniques: List[str] = Field(default_factory=list)  # Technique IDs


class ATTACKProcedure(BaseModel):
    """MITRE ATT&CK Procedure (real-world example)."""
    procedure_id: str
    technique_id: str
    name: str
    description: str
    actor: Optional[str] = None
    tools: List[str] = Field(default_factory=list)
    examples: List[str] = Field(default_factory=list)
    references: List[str] = Field(default_factory=list)
