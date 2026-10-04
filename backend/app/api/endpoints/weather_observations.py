"""
REST API endpoints for WeatherObservation entity.
Mounted under /api/v1.
"""

from typing import List
from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.weather_observation import WeatherObservationCreate, WeatherObservationResponse
from app.services.weather_observation_service import WeatherObservationService

router = APIRouter(tags=["Weather Observations"])


@router.post(
    "/farms/{farm_id}/weather-observations",
    response_model=WeatherObservationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record Weather Observation",
    description="Records empirical weather measurements associated with a farm parcel.",
)
def record_weather_observation(
    farm_id: int,
    payload: WeatherObservationCreate,
    db: Session = Depends(get_db),
) -> WeatherObservationResponse:
    service = WeatherObservationService(db)
    obs = service.create_observation(farm_id, payload)
    return WeatherObservationResponse.model_validate(obs)


@router.get(
    "/farms/{farm_id}/weather-observations",
    response_model=List[WeatherObservationResponse],
    status_code=status.HTTP_200_OK,
    summary="List Weather Observations",
    description="Retrieves recorded weather observations for a specific farm parcel.",
)
def list_weather_observations(
    farm_id: int,
    db: Session = Depends(get_db),
) -> List[WeatherObservationResponse]:
    service = WeatherObservationService(db)
    observations = service.get_observations_by_farm(farm_id)
    return [WeatherObservationResponse.model_validate(item) for item in observations]


@router.delete(
    "/weather-observations/{observation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Weather Observation",
    description="Deletes a specific weather observation record.",
)
def delete_weather_observation(
    observation_id: int,
    db: Session = Depends(get_db),
) -> Response:
    service = WeatherObservationService(db)
    service.delete_observation(observation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
