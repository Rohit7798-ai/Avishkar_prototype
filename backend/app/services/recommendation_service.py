"""
Domain Recommendation Orchestration Service.
Coordinates independent Harvest and Sell recommendation engines,
assembling grounded recommendations with complete data quality transparency.
Does NOT combine harvest and sell decisions, and contains zero black-box scoring logic.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.core.exceptions import EntityNotFoundException
from app.ml.services.prediction_service import MarketPricePredictionService
from app.repositories.crop_repository import CropRepository
from app.repositories.farm_repository import FarmRepository
from app.schemas.recommendation import (
    CropRecommendationResponse,
    DataQualitySummary,
)
from app.services.crop_indicator_service import CropIndicatorService
from app.services.weather_indicator_service import WeatherIndicatorService
from app.services.market_indicator_service import MarketIndicatorService
from app.services.harvest_recommendation_service import HarvestRecommendationService
from app.services.sell_recommendation_service import SellRecommendationService


class RecommendationService:
    """Orchestrates decoupled harvest and selling recommendations for crop plantings."""

    def __init__(
        self,
        db: Session,
        ml_service: Optional[MarketPricePredictionService] = None,
    ):
        self.db = db
        self.crop_repo = CropRepository(db)
        self.farm_repo = FarmRepository(db)
        self.crop_indicator_service = CropIndicatorService(db)
        self.weather_indicator_service = WeatherIndicatorService(db)
        self.market_indicator_service = MarketIndicatorService(db)
        self.harvest_service = HarvestRecommendationService(db)
        self.sell_service = SellRecommendationService(db, ml_service=ml_service)

    def get_crop_recommendation(self, crop_id: int) -> CropRecommendationResponse:
        crop = self.crop_repo.get_by_id(crop_id)
        if not crop:
            raise EntityNotFoundException("Crop", crop_id)

        farm = self.farm_repo.get_by_id(crop.farm_id)
        farm_name = farm.name if farm else "Unknown Farm"
        farm_location = farm.location if farm else "Unknown Location"

        # 1. Independent Harvest Recommendation
        harvest_rec = self.harvest_service.evaluate_harvest_recommendation(crop_id)

        # 2. Independent Sell Recommendation (evaluated for crop commodity)
        sell_rec = self.sell_service.evaluate_sell_recommendation(crop_name=crop.crop_name)

        # 3. Data Quality & Freshness Summary
        crop_ind = self.crop_indicator_service.get_crop_indicators(crop_id)
        weather_ind = self.weather_indicator_service.get_farm_weather_indicators(crop.farm_id)
        market_ind = self.market_indicator_service.get_market_indicators(crop_name=crop.crop_name)

        prediction_available = (
            sell_rec.supporting_factors.get("predicted_next_modal_price") is not None
        )

        data_quality = DataQualitySummary(
            harvest_data_sufficiency=harvest_rec.data_sufficiency,
            market_data_sufficiency=sell_rec.data_sufficiency,
            crop_observation_count=crop_ind.observation_count,
            observation_freshness_days=crop_ind.days_since_latest_observation,
            weather_observation_count=weather_ind.observation_count,
            market_observation_count=market_ind.observation_count,
            prediction_available=prediction_available,
        )

        return CropRecommendationResponse(
            crop_id=crop.id,
            crop_name=crop.crop_name,
            farm_name=farm_name,
            farm_location=farm_location,
            harvest_recommendation=harvest_rec,
            sell_recommendation=sell_rec,
            data_quality=data_quality,
            generated_at=datetime.utcnow(),
        )
