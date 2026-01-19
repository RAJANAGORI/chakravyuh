"""Continuous evaluation pipeline."""
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel

from chakravyuh.evaluation.benchmark.dataset import BenchmarkDataset, BenchmarkMetrics
from chakravyuh.core.logging import logger


class EvaluationResult(BaseModel):
    """Result of an evaluation run."""
    run_id: str
    timestamp: datetime
    metrics: BenchmarkMetrics
    case_results: List[Dict[str, Any]] = []
    overall_score: float = 0.0


class EvaluationPipeline:
    """Continuous evaluation pipeline for threat modeling system."""

    def __init__(self, benchmark_dataset: BenchmarkDataset):
        """
        Initialize evaluation pipeline.

        Args:
            benchmark_dataset: Benchmark dataset to use
        """
        self.benchmark = benchmark_dataset
        self.results: List[EvaluationResult] = []

    def evaluate_system(
        self,
        threat_model_generator,
        run_id: Optional[str] = None,
    ) -> EvaluationResult:
        """
        Evaluate the entire system on benchmark dataset.

        Args:
            threat_model_generator: Function that takes architecture description
                                   and returns threat model
            run_id: Optional run identifier

        Returns:
            Evaluation result
        """
        if not run_id:
            run_id = f"eval_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        logger.info(f"Starting evaluation run: {run_id}")

        case_results = []
        total_precision = 0.0
        total_recall = 0.0
        total_f1 = 0.0
        total_cases = 0

        for case in self.benchmark.get_all_cases():
            try:
                # Generate threat model
                threat_model = threat_model_generator(case.architecture_description)

                # Extract predictions
                predicted_threats = self._extract_threats(threat_model)
                predicted_controls = threat_model.get("key_controls", [])

                # Evaluate
                case_result = self.benchmark.evaluate_prediction(
                    case.case_id,
                    predicted_threats,
                    predicted_controls,
                )
                case_results.append(case_result)

                total_precision += case_result["precision"]
                total_recall += case_result["recall"]
                total_f1 += case_result["f1_score"]
                total_cases += 1

            except Exception as e:
                logger.error(f"Error evaluating case {case.case_id}: {e}")
                case_results.append({
                    "case_id": case.case_id,
                    "error": str(e),
                })

        # Calculate overall metrics
        avg_precision = total_precision / total_cases if total_cases > 0 else 0.0
        avg_recall = total_recall / total_cases if total_cases > 0 else 0.0
        avg_f1 = total_f1 / total_cases if total_cases > 0 else 0.0

        metrics = BenchmarkMetrics(
            precision=avg_precision,
            recall=avg_recall,
            f1_score=avg_f1,
            total_cases=total_cases,
            correct_predictions=sum(1 for r in case_results if r.get("f1_score", 0) > 0.7),
        )

        overall_score = (avg_precision + avg_recall + avg_f1) / 3.0

        result = EvaluationResult(
            run_id=run_id,
            timestamp=datetime.utcnow(),
            metrics=metrics,
            case_results=case_results,
            overall_score=overall_score,
        )

        self.results.append(result)
        logger.info(f"Evaluation complete: {run_id} - Score: {overall_score:.2f}")

        return result

    def _extract_threats(self, threat_model: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract threats from threat model structure."""
        threats = []

        # Extract from CIA section
        cia = threat_model.get("cia", {})
        for category in ["confidentiality", "integrity", "availability"]:
            items = cia.get(category, [])
            for item in items:
                threats.append({
                    "category": category,
                    "risk": item.get("risk", ""),
                    "impact": item.get("impact", ""),
                    "likelihood": item.get("likelihood", ""),
                })

        # Extract from AAA section
        aaa = threat_model.get("aaa", {})
        for category in ["authentication", "authorization", "accounting"]:
            items = aaa.get(category, [])
            for item in items:
                threats.append({
                    "category": category,
                    "risk": item.get("risk", ""),
                    "impact": item.get("impact", ""),
                    "likelihood": item.get("likelihood", ""),
                })

        return threats

    def compare_runs(self, run_id1: str, run_id2: str) -> Dict[str, Any]:
        """
        Compare two evaluation runs.

        Args:
            run_id1: First run ID
            run_id2: Second run ID

        Returns:
            Comparison results
        """
        result1 = next((r for r in self.results if r.run_id == run_id1), None)
        result2 = next((r for r in self.results if r.run_id == run_id2), None)

        if not result1 or not result2:
            raise ValueError("One or both runs not found")

        return {
            "run1": {
                "run_id": run_id1,
                "score": result1.overall_score,
                "precision": result1.metrics.precision,
                "recall": result1.metrics.recall,
                "f1": result1.metrics.f1_score,
            },
            "run2": {
                "run_id": run_id2,
                "score": result2.overall_score,
                "precision": result2.metrics.precision,
                "recall": result2.metrics.recall,
                "f1": result2.metrics.f1_score,
            },
            "improvement": {
                "score": result2.overall_score - result1.overall_score,
                "precision": result2.metrics.precision - result1.metrics.precision,
                "recall": result2.metrics.recall - result1.metrics.recall,
                "f1": result2.metrics.f1_score - result1.metrics.f1_score,
            },
        }

    def get_latest_result(self) -> Optional[EvaluationResult]:
        """Get the most recent evaluation result."""
        if not self.results:
            return None
        return max(self.results, key=lambda r: r.timestamp)
