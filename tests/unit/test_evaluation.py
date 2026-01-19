"""Unit tests for evaluation modules."""
import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from chakravyuh.evaluation.benchmark.dataset import BenchmarkDataset, BenchmarkCase
from chakravyuh.evaluation.validation.interface import ValidationInterface, ReviewStatus


class TestBenchmarkDataset:
    """Tests for benchmark dataset."""

    def test_create_case(self):
        """Test creating benchmark case."""
        case = BenchmarkCase(
            case_id="test1",
            architecture_description="Test architecture",
            expected_threats=[{"risk": "Data breach", "impact": "High"}],
            expected_controls=["Encryption"],
        )

        assert case.case_id == "test1"
        assert len(case.expected_threats) == 1

    def test_evaluate_prediction(self):
        """Test prediction evaluation."""
        dataset = BenchmarkDataset(dataset_path="./tests/fixtures/benchmark")

        # Create a test case
        case = BenchmarkCase(
            case_id="eval_test",
            architecture_description="Test",
            expected_threats=[
                {"risk": "Data breach", "impact": "High", "likelihood": "Medium"},
            ],
            expected_controls=["Encryption", "Access control"],
        )

        dataset.add_case(case)

        # Evaluate prediction
        predicted_threats = [
            {"risk": "Data breach", "impact": "High", "likelihood": "Medium"},
            {"risk": "Unauthorized access", "impact": "Medium", "likelihood": "Low"},
        ]
        predicted_controls = ["Encryption"]

        result = dataset.evaluate_prediction(
            "eval_test",
            predicted_threats,
            predicted_controls,
        )

        assert result["precision"] > 0
        assert result["recall"] > 0
        assert result["f1_score"] > 0


class TestValidationInterface:
    """Tests for validation interface."""

    def test_create_review(self):
        """Test creating review."""
        validation = ValidationInterface(storage_path="./tests/fixtures/reviews")

        review = validation.create_review(
            threat_model_id="tm1",
            reviewer_id="expert1",
            threat_model={"scope": "Test"},
        )

        assert review.status == ReviewStatus.PENDING
        assert review.threat_model_id == "tm1"

    def test_submit_review(self):
        """Test submitting review."""
        validation = ValidationInterface(storage_path="./tests/fixtures/reviews")

        review = validation.create_review("tm1", "expert1", {})
        updated = validation.submit_review(
            review.review_id,
            ReviewStatus.APPROVED,
            comments="Looks good",
            accuracy_score=0.9,
            completeness_score=0.85,
        )

        assert updated.status == ReviewStatus.APPROVED
        assert updated.accuracy_score == 0.9
