"""Threat graph data models."""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class NodeType(str, Enum):
    """Types of nodes in the threat graph."""
    THREAT = "threat"
    ASSET = "asset"
    CONTROL = "control"
    VULNERABILITY = "vulnerability"
    TECHNIQUE = "technique"  # MITRE ATT&CK
    CVE = "cve"
    CWE = "cwe"


class EdgeType(str, Enum):
    """Types of edges in the threat graph."""
    EXPLOITS = "exploits"
    MITIGATES = "mitigates"
    AFFECTS = "affects"
    RELATED_TO = "related_to"
    PRECEDES = "precedes"
    CAUSES = "causes"


class ThreatNode(BaseModel):
    """Node in the threat intelligence graph."""
    node_id: str
    node_type: NodeType
    name: str
    description: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    risk_score: Optional[float] = None  # 0.0 to 1.0


class ThreatEdge(BaseModel):
    """Edge in the threat intelligence graph."""
    edge_id: str
    source_id: str
    target_id: str
    edge_type: EdgeType
    weight: float = 1.0  # Relationship strength
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AttackPath(BaseModel):
    """Attack path through the threat graph."""
    path_id: str
    nodes: List[str]  # Node IDs in order
    edges: List[str]  # Edge IDs in order
    total_risk: float = 0.0
    description: Optional[str] = None
