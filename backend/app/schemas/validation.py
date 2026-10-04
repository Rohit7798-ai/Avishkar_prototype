"""
Pydantic schemas for Historical & Real-World Recommendation Validation.
Defines structured reports for walk-forward prediction benchmarking,
sell recommendation direction agreement, and transparent harvest evaluability status.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class MetricDetail(BaseModel):
    """Regression accuracy metrics."""
    mae: float = Field(..., description="Mean Absolute Error (Rs/Quintal)")
    rmse: float = Field(..., description="Root Mean Squared Error (Rs/Quintal)")
    mape_percent: float = Field(..., description="Mean Absolute Percentage Error (%)")

    model_config = ConfigDict(extra="forbid")


class MarketPredictionMetric(BaseModel):
    """Market-specific prediction accuracy metrics."""
    market: str
    evaluated_transitions: int
    model_performance: MetricDetail
    naive_baseline_performance: MetricDetail
    mae_improvement_percent: float

    model_config = ConfigDict(extra="forbid")


class PredictionValidationReport(BaseModel):
    """Aggregate and per-market prediction validation results."""
    model_name: str
    model_version: str
    total_evaluated_transitions: int
    overall_model_performance: MetricDetail
    overall_naive_performance: MetricDetail
    overall_mae_improvement_percent: float
    by_market: List[MarketPredictionMetric]

    model_config = ConfigDict(extra="forbid")


class RecommendationPostureOutcome(BaseModel):
    """Agreement statistics for a specific recommendation posture."""
    count: int
    agreed: int
    disagreed: int
    neutral: int
    agreement_rate_percent: Optional[float] = None

    model_config = ConfigDict(extra="forbid")


class SellValidationReport(BaseModel):
    """Validation outcomes for sell recommendations tested against subsequent market movements."""
    evaluation_horizon: str = Field("1-day walk-forward", description="Subsequent price verification window")
    total_evaluated_decisions: int
    total_agreed: int
    total_disagreed: int
    total_neutral: int
    overall_agreement_rate_percent: Optional[float] = None
    by_posture: Dict[str, RecommendationPostureOutcome]

    model_config = ConfigDict(extra="forbid")


class HarvestValidationReport(BaseModel):
    """Status for harvest recommendation validation."""
    status: str = Field("not_evaluable", description="Evaluability status: not_evaluable or evaluated")
    evaluated_cases: int = 0
    reason: str = Field(
        ...,
        description="Reason why harvest recommendation validation is evaluable or not_evaluable",
    )

    model_config = ConfigDict(extra="forbid")


class ValidationFailureCase(BaseModel):
    """Traceable record of a historical prediction or recommendation failure case."""
    date: str
    market: str
    failure_type: str = Field(
        ...,
        description="Failure category: direction_disagreement, high_prediction_error, insufficient_data",
    )
    recommendation: Optional[str] = None
    current_modal_price: float
    predicted_modal_price: Optional[float] = None
    actual_subsequent_modal_price: Optional[float] = None
    price_change: Optional[float] = None
    evidence: str

    model_config = ConfigDict(extra="forbid")


class HistoricalValidationResponse(BaseModel):
    """
    Comprehensive, transparent historical validation report.
    Keeps each evaluation dimension strictly decoupled without arbitrary aggregate scoring.
    """
    evaluation_period: Dict[str, str] = Field(
        ...,
        description="Chronological start_date and end_date evaluated",
    )
    dataset_summary: Dict[str, Any] = Field(
        ...,
        description="Summary of historical records (commodity, total_records, markets, usable_records)",
    )
    number_of_evaluated_cases: int
    number_of_not_evaluable_cases: int
    prediction_validation: PredictionValidationReport
    sell_recommendation_validation: SellValidationReport
    harvest_recommendation_validation: HarvestValidationReport
    failure_cases: List[ValidationFailureCase]
    data_limitations: List[str]
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(extra="forbid")
