"""Unit tests for knowledge graph modules."""
import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from chakravyuh.knowledge_graph.mitre.models import ATTACKTechnique, ATTACKTactic
from chakravyuh.knowledge_graph.cve.models import CVE, CWE
from chakravyuh.knowledge_graph.graph.models import ThreatNode, ThreatEdge, NodeType, EdgeType
from chakravyuh.knowledge_graph.graph.manager import ThreatGraphManager
from chakravyuh.knowledge_graph.framework_mapper import FrameworkMapper, CIACategory, AAACategory


class TestThreatGraph:
    """Tests for threat graph."""

    def test_add_node(self):
        """Test adding nodes to graph."""
        graph = ThreatGraphManager()

        node = ThreatNode(
            node_id="threat1",
            node_type=NodeType.THREAT,
            name="Data Breach",
            description="Unauthorized access to sensitive data",
            risk_score=0.8,
        )

        graph.add_node(node)
        assert graph.get_node("threat1") == node

    def test_add_edge(self):
        """Test adding edges to graph."""
        graph = ThreatGraphManager()

        node1 = ThreatNode(node_id="threat1", node_type=NodeType.THREAT, name="Threat 1")
        node2 = ThreatNode(node_id="control1", node_type=NodeType.CONTROL, name="Control 1")

        graph.add_node(node1)
        graph.add_node(node2)

        edge = ThreatEdge(
            edge_id="edge1",
            source_id="control1",
            target_id="threat1",
            edge_type=EdgeType.MITIGATES,
        )

        graph.add_edge(edge)
        neighbors = graph.get_neighbors("control1")
        assert len(neighbors) == 1

    def test_attack_path_discovery(self):
        """Test attack path discovery."""
        graph = ThreatGraphManager()

        # Create a simple attack path
        nodes = [
            ThreatNode(node_id="vuln1", node_type=NodeType.VULNERABILITY, name="Vuln 1"),
            ThreatNode(node_id="threat1", node_type=NodeType.THREAT, name="Threat 1"),
            ThreatNode(node_id="asset1", node_type=NodeType.ASSET, name="Asset 1"),
        ]

        for node in nodes:
            graph.add_node(node)

        edges = [
            ThreatEdge("e1", "vuln1", "threat1", EdgeType.EXPLOITS),
            ThreatEdge("e2", "threat1", "asset1", EdgeType.AFFECTS),
        ]

        for edge in edges:
            graph.add_edge(edge)

        paths = graph.find_attack_paths("vuln1", "asset1", max_depth=3)
        assert len(paths) > 0


class TestFrameworkMapper:
    """Tests for framework mapping."""

    def test_cia_mapping(self):
        """Test CIA framework mapping."""
        mapper = FrameworkMapper()

        threat = ThreatNode(
            node_id="t1",
            node_type=NodeType.THREAT,
            name="Data Breach",
            description="Unauthorized access to confidential data",
        )

        categories = mapper.map_to_cia(threat)
        assert CIACategory.CONFIDENTIALITY in categories

    def test_aaa_mapping(self):
        """Test AAA framework mapping."""
        mapper = FrameworkMapper()

        threat = ThreatNode(
            node_id="t1",
            node_type=NodeType.THREAT,
            name="Authentication Bypass",
            description="Weak authentication mechanisms",
        )

        categories = mapper.map_to_aaa(threat)
        assert AAACategory.AUTHENTICATION in categories

    def test_stride_mapping(self):
        """Test STRIDE framework mapping."""
        mapper = FrameworkMapper()

        threat = ThreatNode(
            node_id="t1",
            node_type=NodeType.THREAT,
            name="Spoofing Attack",
            description="Impersonation of user identity",
        )

        categories = mapper.map_to_stride(threat)
        assert len(categories) > 0
