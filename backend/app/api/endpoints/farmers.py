"""
REST API endpoints for Farmer domain entity.
Mounted under /api/v1/farmers.
"""

from typing import List
from fastapi import APIRouter, Depends, Query, status, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.farmer import FarmerCreate, FarmerResponse
from app.services.farmer_service import FarmerService

router = APIRouter(tags=["Farmers"])


@router.post(
    "/farmers",
    response_model=FarmerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Farmer",
    description="Registers a new farmer profile in the system.",
)
def create_farmer(
    payload: FarmerCreate,
    db: Session = Depends(get_db),
) -> FarmerResponse:
    service = FarmerService(db)
    farmer = service.create_farmer(payload)
    return FarmerResponse.model_validate(farmer)


@router.get(
    "/farmers",
    response_model=List[FarmerResponse],
    status_code=status.HTTP_200_OK,
    summary="List Farmers",
    description="Retrieves a paginated list of registered farmers.",
)
def list_farmers(
    skip: int = Query(0, ge=0, description="Offset record count"),
    limit: int = Query(100, ge=1, le=1000, description="Page limit"),
    db: Session = Depends(get_db),
) -> List[FarmerResponse]:
    service = FarmerService(db)
    farmers = service.list_farmers(skip=skip, limit=limit)
    return [FarmerResponse.model_validate(f) for f in farmers]


@router.get(
    "/farmers/{farmer_id}",
    response_model=FarmerResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Farmer by ID",
    description="Retrieves details for a specific farmer by primary key.",
)
def get_farmer(
    farmer_id: int,
    db: Session = Depends(get_db),
) -> FarmerResponse:
    service = FarmerService(db)
    farmer = service.get_farmer_by_id(farmer_id)
    return FarmerResponse.model_validate(farmer)


@router.delete(
    "/farmers/{farmer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Farmer",
    description="Deletes a farmer profile and cascades deletion to owned farms and crops.",
)
def delete_farmer(
    farmer_id: int,
    db: Session = Depends(get_db),
) -> Response:
    service = FarmerService(db)
    service.delete_farmer(farmer_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
