"""Human-in-the-loop validation interface."""
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
from pathlib import Path
from pydantic import BaseModel, Field

from chakravyuh.core.logging import logger


class ReviewStatus(str, Enum):
    """Review status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


class ExpertReview(BaseModel):
    """Expert review of a threat model."""
    review_id: str
    threat_model_id: str
    reviewer_id: str
    status: ReviewStatus = ReviewStatus.PENDING
    comments: str = ""
    corrections: List[Dict[str, Any]] = Field(default_factory=list)
    accuracy_score: Optional[float] = None  # 0.0 to 1.0
    completeness_score: Optional[float] = None  # 0.0 to 1.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ValidationInterface:
    """Interface for human-in-the-loop validation."""

    def __init__(self, storage_path: str = "./data/evaluation/reviews"):
        """
        Initialize validation interface.

        Args:
            storage_path: Path to store reviews
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.reviews: Dict[str, ExpertReview] = {}
        self.load_reviews()

    def load_reviews(self) -> None:
        """Load reviews from storage."""
        reviews_file = self.storage_path / "reviews.json"

        if not reviews_file.exists():
            return

        try:
            with open(reviews_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            for review_data in data.get("reviews", []):
                review_data["timestamp"] = datetime.fromisoformat(review_data["timestamp"])
                review = ExpertReview(**review_data)
                self.reviews[review.review_id] = review

            logger.info(f"Loaded {len(self.reviews)} expert reviews")

        except Exception as e:
            logger.error(f"Error loading reviews: {e}")

    def save_reviews(self) -> None:
        """Save reviews to storage."""
        reviews_file = self.storage_path / "reviews.json"

        data = {
            "version": "1.0",
            "reviews": [review.dict() for review in self.reviews.values()],
        }

        with open(reviews_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    def create_review(
        self,
        threat_model_id: str,
        reviewer_id: str,
        threat_model: Dict[str, Any],
    ) -> ExpertReview:
        """
        Create a new review request.

        Args:
            threat_model_id: Threat model identifier
            reviewer_id: Reviewer identifier
            threat_model: Threat model data to review

        Returns:
            Created review
        """
        review_id = f"review_{threat_model_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        review = ExpertReview(
            review_id=review_id,
            threat_model_id=threat_model_id,
            reviewer_id=reviewer_id,
            status=ReviewStatus.PENDING,
        )

        self.reviews[review_id] = review
        self.save_reviews()

        logger.info(f"Created review {review_id} for threat model {threat_model_id}")

        return review

    def submit_review(
        self,
        review_id: str,
        status: ReviewStatus,
        comments: str = "",
        corrections: Optional[List[Dict[str, Any]]] = None,
        accuracy_score: Optional[float] = None,
        completeness_score: Optional[float] = None,
    ) -> ExpertReview:
        """
        Submit expert review.

        Args:
            review_id: Review identifier
            status: Review status
            comments: Review comments
            corrections: List of corrections
            accuracy_score: Accuracy score (0.0 to 1.0)
            completeness_score: Completeness score (0.0 to 1.0)

        Returns:
            Updated review
        """
        review = self.reviews.get(review_id)
        if not review:
            raise ValueError(f"Review {review_id} not found")

        review.status = status
        review.comments = comments
        review.corrections = corrections or []
        review.accuracy_score = accuracy_score
        review.completeness_score = completeness_score
        review.timestamp = datetime.utcnow()

        self.save_reviews()

        logger.info(f"Review {review_id} submitted with status {status.value}")

        return review

    def get_review(self, review_id: str) -> Optional[ExpertReview]:
        """Get review by ID."""
        return self.reviews.get(review_id)

    def get_reviews_for_threat_model(self, threat_model_id: str) -> List[ExpertReview]:
        """Get all reviews for a threat model."""
        return [r for r in self.reviews.values() if r.threat_model_id == threat_model_id]

    def get_pending_reviews(self) -> List[ExpertReview]:
        """Get all pending reviews."""
        return [r for r in self.reviews.values() if r.status == ReviewStatus.PENDING]

    def get_feedback_summary(self) -> Dict[str, Any]:
        """
        Get summary of expert feedback for system improvement.

        Returns:
            Summary statistics
        """
        total_reviews = len(self.reviews)
        if total_reviews == 0:
            return {"total_reviews": 0}

        approved = sum(1 for r in self.reviews.values() if r.status == ReviewStatus.APPROVED)
        rejected = sum(1 for r in self.reviews.values() if r.status == ReviewStatus.REJECTED)
        needs_revision = sum(1 for r in self.reviews.values() if r.status == ReviewStatus.NEEDS_REVISION)

        avg_accuracy = sum(r.accuracy_score for r in self.reviews.values() if r.accuracy_score) / total_reviews
        avg_completeness = sum(r.completeness_score for r in self.reviews.values() if r.completeness_score) / total_reviews

        return {
            "total_reviews": total_reviews,
            "approved": approved,
            "rejected": rejected,
            "needs_revision": needs_revision,
            "approval_rate": approved / total_reviews if total_reviews > 0 else 0.0,
            "average_accuracy": avg_accuracy,
            "average_completeness": avg_completeness,
        }
