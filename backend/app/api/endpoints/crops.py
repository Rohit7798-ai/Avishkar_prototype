"""
REST API endpoints for Crop domain entity.
Mounted under /api/v1.
"""

from typing import List
from fastapi import APIRouter, Depends, Query, status, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.crop import CropCreate, CropResponse
from app.services.crop_service import CropService

router = APIRouter(tags=["Crops"])


@router.post(
    "/crops",
    response_model=CropResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Crop",
    description="Registers a new crop planting linked to a valid farm parcel.",
)
def create_crop(
    payload: CropCreate,
    db: Session = Depends(get_db),
) -> CropResponse:
    service = CropService(db)
    crop = service.create_crop(payload)
    return CropResponse.model_validate(crop)


@router.get(
    "/crops",
    response_model=List[CropResponse],
    status_code=status.HTTP_200_OK,
    summary="List Crops",
    description="Retrieves a paginated list of all crop plantings.",
)
def list_crops(
    skip: int = Query(0, ge=0, description="Offset record count"),
    limit: int = Query(100, ge=1, le=1000, description="Page limit"),
    db: Session = Depends(get_db),
) -> List[CropResponse]:
    service = CropService(db)
    crops = service.list_crops(skip=skip, limit=limit)
    return [CropResponse.model_validate(c) for f in [crops] for c in f]


@router.get(
    "/crops/{crop_id}",
    response_model=CropResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Crop by ID",
    description="Retrieves details for a specific crop planting by primary key.",
)
def get_crop(
    crop_id: int,
    db: Session = Depends(get_db),
) -> CropResponse:
    service = CropService(db)
    crop = service.get_crop_by_id(crop_id)
    return CropResponse.model_validate(crop)


@router.get(
    "/farms/{farm_id}/crops",
    response_model=List[CropResponse],
    status_code=status.HTTP_200_OK,
    summary="List Crops by Farm",
    description="Retrieves all crop plantings located on a specific farm parcel.",
)
def list_crops_by_farm(
    farm_id: int,
    db: Session = Depends(get_db),
) -> List[CropResponse]:
    service = CropService(db)
    crops = service.list_crops_by_farm(farm_id)
    return [CropResponse.model_validate(c) for c in crops]


@router.delete(
    "/crops/{crop_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Crop",
    description="Deletes a crop planting record.",
)
def delete_crop(
    crop_id: int,
    db: Session = Depends(get_db),
) -> Response:
    service = CropService(db)
    service.delete_crop(crop_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
