"""Threat intelligence graph manager."""
from typing import List, Dict, Optional, Set, Tuple
from collections import defaultdict, deque

from chakravyuh.knowledge_graph.graph.models import (
    ThreatNode,
    ThreatEdge,
    AttackPath,
    NodeType,
    EdgeType,
)
from chakravyuh.core.logging import logger


class ThreatGraphManager:
    """Manages threat intelligence graph with relationships."""

    def __init__(self):
        """Initialize empty threat graph."""
        self.nodes: Dict[str, ThreatNode] = {}
        self.edges: Dict[str, ThreatEdge] = {}
        self.adjacency: Dict[str, List[str]] = defaultdict(list)  # node_id -> [edge_ids]
        self.reverse_adjacency: Dict[str, List[str]] = defaultdict(list)  # target -> [edge_ids]

    def add_node(self, node: ThreatNode) -> None:
        """
        Add a node to the graph.

        Args:
            node: ThreatNode to add
        """
        self.nodes[node.node_id] = node
        if node.node_id not in self.adjacency:
            self.adjacency[node.node_id] = []
        if node.node_id not in self.reverse_adjacency:
            self.reverse_adjacency[node.node_id] = []

    def add_edge(self, edge: ThreatEdge) -> None:
        """
        Add an edge to the graph.

        Args:
            edge: ThreatEdge to add
        """
        if edge.source_id not in self.nodes:
            raise ValueError(f"Source node {edge.source_id} not found")
        if edge.target_id not in self.nodes:
            raise ValueError(f"Target node {edge.target_id} not found")

        self.edges[edge.edge_id] = edge
        self.adjacency[edge.source_id].append(edge.edge_id)
        self.reverse_adjacency[edge.target_id].append(edge.edge_id)

    def get_node(self, node_id: str) -> Optional[ThreatNode]:
        """Get node by ID."""
        return self.nodes.get(node_id)

    def get_neighbors(self, node_id: str, edge_type: Optional[EdgeType] = None) -> List[ThreatNode]:
        """
        Get neighboring nodes.

        Args:
            node_id: Source node ID
            edge_type: Optional filter by edge type

        Returns:
            List of neighboring nodes
        """
        neighbors = []
        edge_ids = self.adjacency.get(node_id, [])

        for edge_id in edge_ids:
            edge = self.edges.get(edge_id)
            if not edge:
                continue

            if edge_type and edge.edge_type != edge_type:
                continue

            target_node = self.nodes.get(edge.target_id)
            if target_node:
                neighbors.append(target_node)

        return neighbors

    def find_attack_paths(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5,
        edge_types: Optional[List[EdgeType]] = None,
    ) -> List[AttackPath]:
        """
        Find all attack paths from source to target.

        Args:
            source_id: Starting node ID
            target_id: Target node ID
            max_depth: Maximum path length
            edge_types: Optional filter by edge types

        Returns:
            List of attack paths
        """
        if source_id not in self.nodes or target_id not in self.nodes:
            return []

        paths = []
        queue = deque([(source_id, [source_id], [])])  # (current_node, path_nodes, path_edges)
        visited = set()

        while queue:
            current, path_nodes, path_edges = queue.popleft()

            if len(path_nodes) > max_depth:
                continue

            if current == target_id and len(path_nodes) > 1:
                # Found a path
                path = AttackPath(
                    path_id=f"path_{len(paths)}",
                    nodes=path_nodes,
                    edges=path_edges,
                    total_risk=self._calculate_path_risk(path_nodes),
                )
                paths.append(path)
                continue

            # Explore neighbors
            edge_ids = self.adjacency.get(current, [])
            for edge_id in edge_ids:
                edge = self.edges.get(edge_id)
                if not edge:
                    continue

                if edge_types and edge.edge_type not in edge_types:
                    continue

                next_node = edge.target_id
                path_key = (current, next_node, edge_id)

                if path_key in visited:
                    continue

                visited.add(path_key)
                queue.append((next_node, path_nodes + [next_node], path_edges + [edge_id]))

        logger.info(f"Found {len(paths)} attack paths from {source_id} to {target_id}")
        return paths

    def _calculate_path_risk(self, node_ids: List[str]) -> float:
        """Calculate total risk score for a path."""
        total_risk = 0.0
        count = 0

        for node_id in node_ids:
            node = self.nodes.get(node_id)
            if node and node.risk_score is not None:
                total_risk += node.risk_score
                count += 1

        return total_risk / count if count > 0 else 0.0

    def link_cve_to_technique(self, cve_id: str, technique_id: str, weight: float = 1.0) -> None:
        """
        Link a CVE to a MITRE ATT&CK technique.

        Args:
            cve_id: CVE node ID
            technique_id: ATT&CK technique node ID
            weight: Edge weight
        """
        edge = ThreatEdge(
            edge_id=f"cve_{cve_id}_to_tech_{technique_id}",
            source_id=cve_id,
            target_id=technique_id,
            edge_type=EdgeType.RELATED_TO,
            weight=weight,
            metadata={"relationship": "cve_exploits_technique"},
        )
        self.add_edge(edge)

    def link_technique_to_mitigation(self, technique_id: str, control_id: str, weight: float = 1.0) -> None:
        """
        Link a technique to a mitigation control.

        Args:
            technique_id: ATT&CK technique node ID
            control_id: Control node ID
            weight: Edge weight
        """
        edge = ThreatEdge(
            edge_id=f"tech_{technique_id}_to_control_{control_id}",
            source_id=control_id,
            target_id=technique_id,
            edge_type=EdgeType.MITIGATES,
            weight=weight,
            metadata={"relationship": "control_mitigates_technique"},
        )
        self.add_edge(edge)

    def get_mitigations_for_threat(self, threat_id: str) -> List[ThreatNode]:
        """
        Get all mitigation controls for a threat.

        Args:
            threat_id: Threat node ID

        Returns:
            List of control nodes that mitigate this threat
        """
        mitigations = []
        edge_ids = self.reverse_adjacency.get(threat_id, [])

        for edge_id in edge_ids:
            edge = self.edges.get(edge_id)
            if not edge or edge.edge_type != EdgeType.MITIGATES:
                continue

            source_node = self.nodes.get(edge.source_id)
            if source_node and source_node.node_type == NodeType.CONTROL:
                mitigations.append(source_node)

        return mitigations

    def get_related_threats(self, node_id: str, max_hops: int = 2) -> List[ThreatNode]:
        """
        Get related threats within N hops.

        Args:
            node_id: Starting node ID
            max_hops: Maximum number of hops

        Returns:
            List of related threat nodes
        """
        related = []
        visited = set()
        queue = deque([(node_id, 0)])

        while queue:
            current, hops = queue.popleft()

            if hops > max_hops:
                continue

            if current in visited:
                continue

            visited.add(current)

            node = self.nodes.get(current)
            if node and node.node_type == NodeType.THREAT and current != node_id:
                related.append(node)

            # Explore neighbors
            edge_ids = self.adjacency.get(current, []) + self.reverse_adjacency.get(current, [])
            for edge_id in edge_ids:
                edge = self.edges.get(edge_id)
                if not edge:
                    continue

                next_node_id = edge.target_id if edge.source_id == current else edge.source_id
                if next_node_id not in visited:
                    queue.append((next_node_id, hops + 1))

        return related
