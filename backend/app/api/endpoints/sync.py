"""
API endpoints for manual synchronization with external data providers.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleViolationException, EntityNotFoundException
from app.db.session import get_db
from app.schemas.sync import MarketSyncRequest, SyncResponse, WeatherSyncRequest
from app.services.market_ingestion_service import MarketIngestionService
from app.services.weather_ingestion_service import WeatherIngestionService

router = APIRouter(tags=["Sync"])


@router.post(
    "/farms/{farm_id}/weather/sync",
    response_model=SyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Synchronize farm weather observations from Open-Meteo",
    description="Manually pulls recent weather measurements from Open-Meteo for a farm's coordinates and ingests them into observations.",
)
def sync_farm_weather(
    farm_id: int = Path(..., description="Target farm parcel ID", ge=1),
    payload: Optional[WeatherSyncRequest] = None,
    db: Session = Depends(get_db),
) -> SyncResponse:
    service = WeatherIngestionService(db)
    lat = payload.latitude if payload else None
    lon = payload.longitude if payload else None
    days = payload.days if (payload and payload.days) else 1

    try:
        result = service.sync_farm_weather(
            farm_id=farm_id,
            latitude=lat,
            longitude=lon,
            days=days,
        )
        return SyncResponse(
            provider=result["provider"],
            records_received=result["records_received"],
            records_accepted=result["records_accepted"],
            records_rejected=result["records_rejected"],
            message=f"Weather sync complete for Farm #{farm_id}.",
        )
    except EntityNotFoundException as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except BusinessRuleViolationException as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post(
    "/market/sync",
    response_model=SyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Synchronize mandi market price quotes from OGD India",
    description="Manually pulls commodity rate quotes from Government of India OGD Mandi API.",
)
def sync_market_data(
    payload: Optional[MarketSyncRequest] = None,
    db: Session = Depends(get_db),
) -> SyncResponse:
    service = MarketIngestionService(db)
    crop_name = payload.crop_name if (payload and payload.crop_name) else "Onion"
    market_name = payload.market_name if payload else None
    limit = payload.limit if (payload and payload.limit) else 50

    try:
        result = service.sync_market_data(
            crop_name=crop_name,
            market_name=market_name,
            limit=limit,
        )
        return SyncResponse(
            provider=result["provider"],
            records_received=result["records_received"],
            records_accepted=result["records_accepted"],
            records_rejected=result["records_rejected"],
            message=f"Market sync complete for {crop_name}.",
        )
    except BusinessRuleViolationException as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
