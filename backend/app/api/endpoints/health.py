from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.schemas.health import HealthResponse, ReadinessResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Returns the operational status and service identifier.",
)
def get_health() -> HealthResponse:
    """Check service health and operational status."""
    return HealthResponse(
        status="ok",
        service="farmer-decision-system",
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness Probe",
    description="Validates local database connectivity. Returns 200 if ready, 503 if database is disconnected.",
    responses={
        200: {"description": "Service is ready to handle traffic"},
        503: {"description": "Service is unavailable due to database failure"},
    },
)
def get_readiness(
    response: Response,
    db: Session = Depends(get_db),
) -> ReadinessResponse:
    """Readiness probe validating database connectivity."""
    try:
        db.execute(text("SELECT 1"))
        return ReadinessResponse(
            status="ready",
            database="connected",
            environment=settings.ENVIRONMENT,
        )
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadinessResponse(
            status="unavailable",
            database="disconnected",
            environment=settings.ENVIRONMENT,
        )
