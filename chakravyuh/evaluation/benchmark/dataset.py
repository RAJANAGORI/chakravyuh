"""Threat modeling benchmark dataset."""
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from pydantic import BaseModel, Field

from chakravyuh.core.logging import logger


class BenchmarkCase(BaseModel):
    """A single benchmark test case."""
    case_id: str
    architecture_description: str
    expected_threats: List[Dict[str, Any]] = Field(default_factory=list)  # Expected CIA/AAA threats
    expected_controls: List[str] = Field(default_factory=list)
    expected_risks: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BenchmarkMetrics(BaseModel):
    """Metrics for benchmark evaluation."""
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    threat_detection_rate: float = 0.0
    hallucination_rate: float = 0.0
    false_positive_rate: float = 0.0
    false_negative_rate: float = 0.0
    total_cases: int = 0
    correct_predictions: int = 0


class BenchmarkDataset:
    """Threat modeling benchmark dataset with ground truth."""

    def __init__(self, dataset_path: str = "./data/evaluation/benchmark"):
        """
        Initialize benchmark dataset.

        Args:
            dataset_path: Path to benchmark dataset directory
        """
        self.dataset_path = Path(dataset_path)
        self.dataset_path.mkdir(parents=True, exist_ok=True)
        self.cases: Dict[str, BenchmarkCase] = {}
        self.load_dataset()

    def load_dataset(self) -> None:
        """Load benchmark dataset from files."""
        dataset_file = self.dataset_path / "benchmark.json"

        if not dataset_file.exists():
            logger.info(f"Benchmark dataset not found at {dataset_file}, creating default")
            self._create_default_dataset()
            return

        try:
            with open(dataset_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            for case_data in data.get("cases", []):
                case = BenchmarkCase(**case_data)
                self.cases[case.case_id] = case

            logger.info(f"Loaded {len(self.cases)} benchmark cases from {dataset_file}")

        except Exception as e:
            logger.error(f"Error loading benchmark dataset: {e}")
            self._create_default_dataset()

    def _create_default_dataset(self) -> None:
        """Create default benchmark dataset with sample cases."""
        default_cases = [
            BenchmarkCase(
                case_id="s3_bucket_public",
                architecture_description=(
                    "An S3 bucket configured for public read access. "
                    "The bucket contains sensitive customer data including PII. "
                    "No encryption at rest is enabled. Access logging is disabled."
                ),
                expected_threats=[
                    {
                        "category": "confidentiality",
                        "risk": "Unauthorized data access",
                        "impact": "High",
                        "likelihood": "High",
                    },
                    {
                        "category": "integrity",
                        "risk": "Data tampering",
                        "impact": "High",
                        "likelihood": "Medium",
                    },
                ],
                expected_controls=[
                    "Enable bucket encryption",
                    "Disable public access",
                    "Enable access logging",
                    "Implement bucket policies",
                ],
                expected_risks=["Data breach", "Compliance violation", "Data loss"],
            ),
            BenchmarkCase(
                case_id="ec2_no_iam_role",
                architecture_description=(
                    "EC2 instances running without IAM roles. "
                    "Applications use hardcoded credentials stored in environment variables. "
                    "No MFA required for access. SSH keys are shared across instances."
                ),
                expected_threats=[
                    {
                        "category": "authentication",
                        "risk": "Credential compromise",
                        "impact": "High",
                        "likelihood": "High",
                    },
                    {
                        "category": "authorization",
                        "risk": "Privilege escalation",
                        "impact": "High",
                        "likelihood": "Medium",
                    },
                ],
                expected_controls=[
                    "Use IAM roles for EC2",
                    "Implement MFA",
                    "Rotate credentials regularly",
                    "Use AWS Secrets Manager",
                ],
                expected_risks=["Unauthorized access", "Privilege escalation"],
            ),
        ]

        for case in default_cases:
            self.cases[case.case_id] = case

        self.save_dataset()
        logger.info(f"Created default benchmark dataset with {len(self.cases)} cases")

    def save_dataset(self) -> None:
        """Save benchmark dataset to file."""
        dataset_file = self.dataset_path / "benchmark.json"

        data = {
            "version": "1.0",
            "cases": [case.dict() for case in self.cases.values()],
        }

        with open(dataset_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved benchmark dataset to {dataset_file}")

    def add_case(self, case: BenchmarkCase) -> None:
        """
        Add a benchmark case.

        Args:
            case: Benchmark case to add
        """
        self.cases[case.case_id] = case
        self.save_dataset()
        logger.info(f"Added benchmark case: {case.case_id}")

    def get_case(self, case_id: str) -> Optional[BenchmarkCase]:
        """Get benchmark case by ID."""
        return self.cases.get(case_id)

    def get_all_cases(self) -> List[BenchmarkCase]:
        """Get all benchmark cases."""
        return list(self.cases.values())

    def evaluate_prediction(
        self,
        case_id: str,
        predicted_threats: List[Dict[str, Any]],
        predicted_controls: List[str],
    ) -> Dict[str, Any]:
        """
        Evaluate a prediction against ground truth.

        Args:
            case_id: Benchmark case ID
            predicted_threats: Predicted threats
            predicted_controls: Predicted controls

        Returns:
            Evaluation metrics
        """
        case = self.get_case(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found")

        # Calculate precision and recall for threats
        expected_threat_risks = {t.get("risk", "") for t in case.expected_threats}
        predicted_threat_risks = {t.get("risk", "") for t in predicted_threats}

        true_positives = len(expected_threat_risks & predicted_threat_risks)
        false_positives = len(predicted_threat_risks - expected_threat_risks)
        false_negatives = len(expected_threat_risks - predicted_threat_risks)

        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        # Calculate control coverage
        expected_controls_set = set(case.expected_controls)
        predicted_controls_set = set(predicted_controls)
        control_coverage = len(expected_controls_set & predicted_controls_set) / len(expected_controls_set) if expected_controls_set else 0.0

        return {
            "case_id": case_id,
            "precision": precision,
            "recall": recall,
            "f1_score": f1_score,
            "control_coverage": control_coverage,
            "true_positives": true_positives,
            "false_positives": false_positives,
            "false_negatives": false_negatives,
            "expected_threats_count": len(case.expected_threats),
            "predicted_threats_count": len(predicted_threats),
        }
