"""
REST API endpoint for Historical & Real-World Recommendation Validation.
Exposes precomputed, cached validation report.
Guarantees zero model training or walk-forward evaluation occurs during the HTTP request.
"""

from fastapi import APIRouter, status

from app.schemas.validation import HistoricalValidationResponse
from app.services.validation_service import ValidationService

router = APIRouter(tags=["Validation"])


@router.get(
    "/validation/historical",
    response_model=HistoricalValidationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Historical Walk-Forward Validation Report",
    description=(
        "Returns the precomputed walk-forward validation report evaluating baseline price predictions, "
        "sell recommendation directional outcomes, and harvest recommendation evaluability "
        "against the real historical dataset. Zero training or walk-forward evaluation occurs inside the request."
    ),
)
def get_historical_validation() -> HistoricalValidationResponse:
    """
    Returns the cached chronological validation report.
    """
    service = ValidationService()
    return service.get_historical_validation_report()
