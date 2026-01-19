"""CVE/CWE data ingestion."""
import json
import requests
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from chakravyuh.knowledge_graph.cve.models import CVE, CWE
from chakravyuh.core.logging import logger


class CVEIngestor:
    """Ingest CVE and CWE data."""

    CVE_API_BASE = "https://services.nvd.nist.gov/rest/json/cves/2.0"
    CWE_API_BASE = "https://cwe.mitre.org/data/csv/1000.csv"  # CWE Top 1000

    def __init__(self, cache_dir: str = "./data/knowledge/cve"):
        """
        Initialize CVE/CWE ingestor.

        Args:
            cache_dir: Directory to cache downloaded data
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cves: Dict[str, CVE] = {}
        self.cwes: Dict[str, CWE] = {}

    def fetch_cve(self, cve_id: str, use_cache: bool = True) -> Optional[CVE]:
        """
        Fetch a specific CVE from NVD API.

        Args:
            cve_id: CVE identifier (e.g., "CVE-2024-1234")
            use_cache: Whether to use cached data if available

        Returns:
            CVE object or None if not found
        """
        cache_file = self.cache_dir / f"{cve_id}.json"

        # Check cache
        if use_cache and cache_file.exists():
            logger.debug(f"Loading cached CVE {cve_id}")
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return self._parse_cve(data)

        # Fetch from API
        try:
            url = f"{self.CVE_API_BASE}?cveId={cve_id}"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()

            if not data.get("vulnerabilities"):
                return None

            cve_data = data["vulnerabilities"][0]["cve"]
            cve = self._parse_cve(cve_data)

            # Cache it
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cve_data, f, indent=2, default=str)

            return cve

        except Exception as e:
            logger.error(f"Error fetching CVE {cve_id}: {e}")
            return None

    def _parse_cve(self, cve_data: Dict[str, Any]) -> CVE:
        """Parse CVE data from NVD API response."""
        cve_id = cve_data.get("id", "")
        descriptions = cve_data.get("descriptions", [])
        description = descriptions[0].get("value", "") if descriptions else ""

        # Extract CVSS scores
        cvss_score = None
        cvss_severity = None
        metrics = cve_data.get("metrics", {})
        if "cvssMetricV31" in metrics and metrics["cvssMetricV31"]:
            cvss_data = metrics["cvssMetricV31"][0]["cvssData"]
            cvss_score = cvss_data.get("baseScore")
            cvss_severity = cvss_data.get("baseSeverity")

        # Extract CWE IDs
        cwe_ids = []
        weaknesses = cve_data.get("weaknesses", [])
        for weakness in weaknesses:
            for desc in weakness.get("description", []):
                cwe_id = desc.get("value", "")
                if cwe_id.startswith("CWE-"):
                    cwe_ids.append(cwe_id)

        # Extract affected products
        affected_products = []
        configurations = cve_data.get("configurations", [])
        for config in configurations:
            nodes = config.get("nodes", [])
            for node in nodes:
                for cpe_match in node.get("cpeMatch", []):
                    criteria = cpe_match.get("criteria", "")
                    if criteria:
                        affected_products.append(criteria)

        # Extract references
        references = []
        refs = cve_data.get("references", [])
        for ref in refs:
            url = ref.get("url", "")
            if url:
                references.append(url)

        # Parse dates
        published_date = None
        modified_date = None
        published = cve_data.get("published")
        modified = cve_data.get("lastModified")

        if published:
            try:
                published_date = datetime.fromisoformat(published.replace("Z", "+00:00"))
            except Exception:
                pass

        if modified:
            try:
                modified_date = datetime.fromisoformat(modified.replace("Z", "+00:00"))
            except Exception:
                pass

        return CVE(
            cve_id=cve_id,
            description=description,
            published_date=published_date,
            modified_date=modified_date,
            cvss_score=cvss_score,
            cvss_severity=cvss_severity,
            affected_products=affected_products,
            cwe_ids=cwe_ids,
            references=references,
        )

    def fetch_cwe(self, cwe_id: str) -> Optional[CWE]:
        """
        Fetch CWE information (simplified - would need full CWE database).

        Args:
            cwe_id: CWE identifier (e.g., "CWE-79")

        Returns:
            CWE object or None
        """
        # Note: Full CWE database is large. This is a simplified version.
        # In production, you'd want to download the full CWE XML/JSON database.
        cache_file = self.cache_dir / f"{cwe_id}.json"

        if cache_file.exists():
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return CWE(**data)

        # For now, return a basic CWE object
        # In production, fetch from CWE database
        cwe = CWE(
            cwe_id=cwe_id,
            name=f"CWE {cwe_id}",
            description="CWE description not available",
        )

        # Cache it
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cwe.dict(), f, indent=2, default=str)

        return cwe

    def link_cve_to_attack(self, cve_id: str, attack_ingestor) -> List[str]:
        """
        Link CVE to MITRE ATT&CK techniques based on description/keywords.

        Args:
            cve_id: CVE identifier
            attack_ingestor: MITREIngestor instance

        Returns:
            List of related ATT&CK technique IDs
        """
        cve = self.fetch_cve(cve_id)
        if not cve:
            return []

        # Simple keyword-based matching
        # In production, use ML/NLP for better matching
        related_techniques = []
        description_lower = cve.description.lower()

        for technique in attack_ingestor.techniques.values():
            technique_keywords = [
                technique.name.lower(),
                technique.description.lower()[:200],  # First 200 chars
            ]

            for keyword_text in technique_keywords:
                # Simple overlap check
                words = set(keyword_text.split())
                desc_words = set(description_lower.split())
                overlap = len(words & desc_words)

                if overlap > 3:  # Threshold for matching
                    related_techniques.append(technique.technique_id)
                    break

        return related_techniques
