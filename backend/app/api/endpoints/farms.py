"""
REST API endpoints for Farm domain entity.
Mounted under /api/v1.
"""

from typing import List
from fastapi import APIRouter, Depends, Query, status, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.farm import FarmCreate, FarmResponse
from app.services.farm_service import FarmService

router = APIRouter(tags=["Farms"])


@router.post(
    "/farms",
    response_model=FarmResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Farm",
    description="Registers a new agricultural parcel associated with a valid farmer.",
)
def create_farm(
    payload: FarmCreate,
    db: Session = Depends(get_db),
) -> FarmResponse:
    service = FarmService(db)
    farm = service.create_farm(payload)
    return FarmResponse.model_validate(farm)


@router.get(
    "/farms",
    response_model=List[FarmResponse],
    status_code=status.HTTP_200_OK,
    summary="List Farms",
    description="Retrieves a paginated list of all farms in the system.",
)
def list_farms(
    skip: int = Query(0, ge=0, description="Offset record count"),
    limit: int = Query(100, ge=1, le=1000, description="Page limit"),
    db: Session = Depends(get_db),
) -> List[FarmResponse]:
    service = FarmService(db)
    farms = service.list_farms(skip=skip, limit=limit)
    return [FarmResponse.model_validate(f) for f in farms]


@router.get(
    "/farms/{farm_id}",
    response_model=FarmResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Farm by ID",
    description="Retrieves details for a specific farm by primary key.",
)
def get_farm(
    farm_id: int,
    db: Session = Depends(get_db),
) -> FarmResponse:
    service = FarmService(db)
    farm = service.get_farm_by_id(farm_id)
    return FarmResponse.model_validate(farm)


@router.get(
    "/farmers/{farmer_id}/farms",
    response_model=List[FarmResponse],
    status_code=status.HTTP_200_OK,
    summary="List Farms by Farmer",
    description="Retrieves all agricultural land parcels belonging to a specific farmer.",
)
def list_farms_by_farmer(
    farmer_id: int,
    db: Session = Depends(get_db),
) -> List[FarmResponse]:
    service = FarmService(db)
    farms = service.list_farms_by_farmer(farmer_id)
    return [FarmResponse.model_validate(f) for f in farms]


@router.delete(
    "/farms/{farm_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Farm",
    description="Deletes a farm parcel and cascades deletion to all planted crops.",
)
def delete_farm(
    farm_id: int,
    db: Session = Depends(get_db),
) -> Response:
    service = FarmService(db)
    service.delete_farm(farm_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
