"""MITRE ATT&CK data ingestion."""
import json
import requests
from typing import List, Dict, Any, Optional
from pathlib import Path

from chakravyuh.knowledge_graph.mitre.models import ATTACKTechnique, ATTACKTactic, ATTACKProcedure
from chakravyuh.core.logging import logger


class MITREIngestor:
    """Ingest MITRE ATT&CK framework data."""

    ATTACK_ENTERPRISE_URL = "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"
    ATTACK_MOBILE_URL = "https://raw.githubusercontent.com/mitre/cti/master/mobile-attack/mobile-attack.json"
    ATTACK_ICS_URL = "https://raw.githubusercontent.com/mitre/cti/master/ics-attack/ics-attack.json"

    def __init__(self, cache_dir: str = "./data/knowledge/mitre"):
        """
        Initialize MITRE ATT&CK ingestor.

        Args:
            cache_dir: Directory to cache downloaded data
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.techniques: Dict[str, ATTACKTechnique] = {}
        self.tactics: Dict[str, ATTACKTactic] = {}
        self.procedures: Dict[str, ATTACKProcedure] = {}

    def download_attack_data(self, domain: str = "enterprise") -> Dict[str, Any]:
        """
        Download MITRE ATT&CK data from GitHub.

        Args:
            domain: "enterprise", "mobile", or "ics"

        Returns:
            Parsed JSON data
        """
        urls = {
            "enterprise": self.ATTACK_ENTERPRISE_URL,
            "mobile": self.ATTACK_MOBILE_URL,
            "ics": self.ATTACK_ICS_URL,
        }

        if domain not in urls:
            raise ValueError(f"Unknown domain: {domain}. Must be one of {list(urls.keys())}")

        cache_file = self.cache_dir / f"attack_{domain}.json"

        # Use cache if available
        if cache_file.exists():
            logger.info(f"Loading cached MITRE ATT&CK {domain} data from {cache_file}")
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)

        # Download fresh data
        logger.info(f"Downloading MITRE ATT&CK {domain} data from {urls[domain]}")
        try:
            response = requests.get(urls[domain], timeout=30)
            response.raise_for_status()
            data = response.json()

            # Cache it
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            logger.info(f"Cached MITRE ATT&CK {domain} data to {cache_file}")
            return data

        except Exception as e:
            logger.error(f"Error downloading MITRE ATT&CK data: {e}")
            raise

    def parse_techniques(self, attack_data: Dict[str, Any]) -> Dict[str, ATTACKTechnique]:
        """
        Parse techniques from ATT&CK data.

        Args:
            attack_data: Raw ATT&CK JSON data

        Returns:
            Dictionary of technique_id -> ATTACKTechnique
        """
        techniques = {}
        objects = attack_data.get("objects", [])

        for obj in objects:
            if obj.get("type") != "attack-pattern":
                continue

            external_refs = {ref.get("source_name"): ref for ref in obj.get("external_references", [])}
            mitre_ref = external_refs.get("mitre-attack")

            if not mitre_ref:
                continue

            technique_id = mitre_ref.get("external_id")
            if not technique_id:
                continue

            # Extract tactics
            kill_chain_names = obj.get("kill_chain_phases", [])
            tactics = [phase.get("phase_name") for phase in kill_chain_names]

            # Extract platforms
            x_mitre_platforms = obj.get("x_mitre_platforms", [])

            # Extract data sources
            x_mitre_data_sources = obj.get("x_mitre_data_sources", [])

            technique = ATTACKTechnique(
                technique_id=technique_id,
                name=obj.get("name", ""),
                description=obj.get("description", ""),
                tactics=tactics,
                platforms=x_mitre_platforms,
                kill_chain_phases=tactics,
                data_sources=x_mitre_data_sources,
                references=[ref.get("url", "") for ref in obj.get("external_references", []) if ref.get("url")],
            )

            techniques[technique_id] = technique

        logger.info(f"Parsed {len(techniques)} MITRE ATT&CK techniques")
        return techniques

    def parse_tactics(self, attack_data: Dict[str, Any]) -> Dict[str, ATTACKTactic]:
        """
        Parse tactics from ATT&CK data.

        Args:
            attack_data: Raw ATT&CK JSON data

        Returns:
            Dictionary of tactic_id -> ATTACKTactic
        """
        tactics = {}
        objects = attack_data.get("objects", [])

        for obj in objects:
            if obj.get("type") != "x-mitre-tactic":
                continue

            external_refs = {ref.get("source_name"): ref for ref in obj.get("external_references", [])}
            mitre_ref = external_refs.get("mitre-attack")

            if not mitre_ref:
                continue

            tactic_id = mitre_ref.get("external_id")
            if not tactic_id:
                continue

            tactic = ATTACKTactic(
                tactic_id=tactic_id,
                name=obj.get("name", ""),
                description=obj.get("description", ""),
            )

            tactics[tactic_id] = tactic

        logger.info(f"Parsed {len(tactics)} MITRE ATT&CK tactics")
        return tactics

    def ingest(self, domain: str = "enterprise") -> Dict[str, Any]:
        """
        Ingest MITRE ATT&CK data.

        Args:
            domain: "enterprise", "mobile", or "ics"

        Returns:
            Dictionary with techniques, tactics, and procedures
        """
        logger.info(f"Ingesting MITRE ATT&CK {domain} data...")

        # Download data
        attack_data = self.download_attack_data(domain)

        # Parse techniques and tactics
        self.techniques = self.parse_techniques(attack_data)
        self.tactics = self.parse_tactics(attack_data)

        # Link techniques to tactics
        for technique in self.techniques.values():
            for tactic_name in technique.tactics:
                # Find tactic by name
                for tactic in self.tactics.values():
                    if tactic.name == tactic_name:
                        if technique.technique_id not in tactic.techniques:
                            tactic.techniques.append(technique.technique_id)

        logger.info(f"✅ Ingested {len(self.techniques)} techniques and {len(self.tactics)} tactics")

        return {
            "techniques": self.techniques,
            "tactics": self.tactics,
            "procedures": self.procedures,
        }

    def get_technique_by_id(self, technique_id: str) -> Optional[ATTACKTechnique]:
        """Get technique by ID."""
        return self.techniques.get(technique_id)

    def search_techniques(self, query: str) -> List[ATTACKTechnique]:
        """
        Search techniques by name or description.

        Args:
            query: Search query

        Returns:
            List of matching techniques
        """
        query_lower = query.lower()
        results = []

        for technique in self.techniques.values():
            if (
                query_lower in technique.name.lower()
                or query_lower in technique.description.lower()
                or query_lower in technique.technique_id.lower()
            ):
                results.append(technique)

        return results
