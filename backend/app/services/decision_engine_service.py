"""
Transparent Agricultural Decision Engine Service.
Evaluates deterministic crop, farm weather, and mandi market indicators
to produce explainable assessments without predictions, scores, or black-box ML.
"""

from typing import Optional
from sqlalchemy.orm import Session

from app.core.exceptions import EntityNotFoundException
from app.repositories.crop_repository import CropRepository
from app.schemas.decision import (
    DecisionFactor,
    HarvestAssessmentResponse,
    MarketAssessmentResponse,
)
from app.services.crop_indicator_service import CropIndicatorService
from app.services.weather_indicator_service import WeatherIndicatorService
from app.services.market_indicator_service import MarketIndicatorService

# ponytail: Deterministic price stability boundary threshold (±2.0% change considered stable)
PRICE_STABILITY_THRESHOLD_PERCENT = 2.0

# ponytail: Maximum age in days for field observations before being considered stale
MAX_OBSERVATION_RECENCY_DAYS = 30


class DecisionEngineService:
    """
    Rule-based, transparent decision engine.
    Consumes indicator services and produces explainable condition assessments.
    Contains zero SQL queries and zero numerical scoring formulas.
    """

    def __init__(self, db: Session):
        self.crop_repo = CropRepository(db)
        self.crop_indicator_service = CropIndicatorService(db)
        self.weather_indicator_service = WeatherIndicatorService(db)
        self.market_indicator_service = MarketIndicatorService(db)

    def evaluate_harvest_assessment(self, crop_id: int) -> HarvestAssessmentResponse:
        """
        Evaluates harvest readiness for a crop planting from recorded indicators.
        Returns explainable factors without predicting future dates or guaranteeing outcomes.
        """
        crop = self.crop_repo.get_by_id(crop_id)
        if not crop:
            raise EntityNotFoundException("Crop", crop_id)

        crop_indicators = self.crop_indicator_service.get_crop_indicators(crop_id)
        weather_indicators = self.weather_indicator_service.get_farm_weather_indicators(crop.farm_id)

        # 1. Check for missing crop observations
        if crop_indicators.observation_count == 0:
            return HarvestAssessmentResponse(
                crop_id=crop_id,
                status="insufficient_data",
                data_sufficiency="insufficient",
                factors=[
                    DecisionFactor(
                        name="crop_observations",
                        value="none",
                        observation="No field observations recorded for this crop planting.",
                    )
                ],
            )

        # 2. Check for stale crop observations (> 30 days)
        days_since = crop_indicators.days_since_latest_observation
        if days_since is not None and days_since > MAX_OBSERVATION_RECENCY_DAYS:
            return HarvestAssessmentResponse(
                crop_id=crop_id,
                status="insufficient_data",
                data_sufficiency="insufficient",
                factors=[
                    DecisionFactor(
                        name="observation_recency",
                        value=f"{days_since} days ago",
                        observation=(
                            f"Latest field observation is {days_since} days old "
                            f"(exceeds {MAX_OBSERVATION_RECENCY_DAYS}-day threshold). "
                            "Fresh field scouting is required to verify current crop condition."
                        ),
                    ),
                    DecisionFactor(
                        name="last_recorded_stage",
                        value=crop_indicators.latest_growth_stage,
                        observation=(
                            f"Last recorded growth stage was '{crop_indicators.latest_growth_stage}' "
                            f"on {crop_indicators.latest_observation_date}."
                        ),
                    ),
                ],
            )

        # 3. Evaluate deterministic growth stage status
        stage = crop_indicators.latest_growth_stage
        if stage in ("maturity", "post_maturity"):
            status_val = "maturity_observed"
        elif stage == "fruiting":
            status_val = "approaching"
        else:
            status_val = "not_ready"

        # 4. Evaluate data sufficiency (sufficient when weather observations are also recorded)
        has_weather = weather_indicators.observation_count > 0
        data_sufficiency = "sufficient" if has_weather else "partial"

        # 5. Build transparent explanatory factors
        factors = []

        # Factor 1: Growth stage
        stage_display = stage.replace("_", " ") if stage else "unknown"
        factors.append(
            DecisionFactor(
                name="growth_stage",
                value=stage,
                observation=f"Latest crop observation reports {stage_display} stage.",
            )
        )

        # Factor 2: Crop health
        health = crop_indicators.latest_health_status
        if health in ("stressed", "damaged"):
            health_obs = f"Latest crop observation reports {health} condition; crop exhibits physical stress or damage."
        else:
            health_obs = f"Latest crop observation reports {health} condition."
        factors.append(
            DecisionFactor(
                name="health_status",
                value=health,
                observation=health_obs,
            )
        )

        # Factor 3: Observation recency
        if days_since == 0:
            recency_str = "today"
            recency_obs = f"Observation recorded today ({crop_indicators.latest_observation_date})."
        else:
            recency_str = f"{days_since} days ago"
            recency_obs = f"Observation recorded {days_since} days ago on {crop_indicators.latest_observation_date}."
        factors.append(
            DecisionFactor(
                name="observation_recency",
                value=recency_str,
                observation=recency_obs,
            )
        )

        # Factor 4: Ambient farm weather conditions
        if has_weather:
            factors.append(
                DecisionFactor(
                    name="weather_conditions",
                    value=f"{weather_indicators.observation_count} observations",
                    observation=(
                        f"Farm weather records show latest temperature {weather_indicators.latest_temperature}°C, "
                        f"humidity {weather_indicators.latest_humidity}%, and rainfall {weather_indicators.latest_rainfall}mm "
                        f"(total {weather_indicators.total_rainfall}mm over period)."
                    ),
                )
            )
        else:
            factors.append(
                DecisionFactor(
                    name="weather_conditions",
                    value="none",
                    observation="No farm weather observations recorded; field curing and drying conditions not available.",
                )
            )

        return HarvestAssessmentResponse(
            crop_id=crop_id,
            status=status_val,
            data_sufficiency=data_sufficiency,
            factors=factors,
        )

    def evaluate_market_assessment(
        self,
        crop_name: Optional[str] = None,
        market_name: Optional[str] = None,
    ) -> MarketAssessmentResponse:
        """
        Evaluates mandi price momentum and trend stability from recorded indicators.
        Returns explainable factors without predicting future prices or advising when to sell.
        """
        market_indicators = self.market_indicator_service.get_market_indicators(
            crop_name=crop_name, market_name=market_name
        )

        count = market_indicators.observation_count

        # Case 1: 0 observations
        if count == 0:
            return MarketAssessmentResponse(
                crop_name=crop_name,
                market_name=market_name,
                status="insufficient_data",
                data_sufficiency="insufficient",
                factors=[
                    DecisionFactor(
                        name="market_observations",
                        value="none",
                        observation="No mandi price observations recorded for this commodity/market combination.",
                    )
                ],
            )

        # Case 2: 1 observation (insufficient historical data to compute a trend)
        if count == 1:
            return MarketAssessmentResponse(
                crop_name=crop_name,
                market_name=market_name,
                status="insufficient_data",
                data_sufficiency="insufficient",
                factors=[
                    DecisionFactor(
                        name="observation_count",
                        value="1 observation",
                        observation="Only 1 market observation recorded; insufficient historical data to evaluate price trend.",
                    ),
                    DecisionFactor(
                        name="latest_price",
                        value=f"Rs. {market_indicators.latest_price}",
                        observation=f"Recorded price is Rs. {market_indicators.latest_price} on {market_indicators.latest_observation_date}.",
                    ),
                ],
            )

        # Case 3: 2 or more observations -> Evaluate deterministic momentum
        pct = market_indicators.price_change_percentage
        if pct is None:
            status_val = "price_stable"
        elif pct > PRICE_STABILITY_THRESHOLD_PERCENT:
            status_val = "price_rising"
        elif pct < -PRICE_STABILITY_THRESHOLD_PERCENT:
            status_val = "price_falling"
        else:
            status_val = "price_stable"

        # Build transparent explanatory factors
        factors = []

        # Factor 1: Price trend
        if status_val == "price_rising":
            trend_text = (
                f"Price increased by Rs. {market_indicators.price_change} (+{pct}%) "
                f"from Rs. {market_indicators.earliest_price} to Rs. {market_indicators.latest_price}."
            )
        elif status_val == "price_falling":
            trend_text = (
                f"Price decreased by Rs. {abs(market_indicators.price_change)} ({pct}%) "
                f"from Rs. {market_indicators.earliest_price} to Rs. {market_indicators.latest_price}."
            )
        else:
            trend_text = (
                f"Price remained within ±{PRICE_STABILITY_THRESHOLD_PERCENT}% stability band "
                f"(change: {pct:+0.2f}% / Rs. {market_indicators.price_change:+0.2f}) across observation period."
            )

        factors.append(
            DecisionFactor(
                name="price_trend",
                value=status_val,
                observation=trend_text,
            )
        )

        # Factor 2: Price range
        factors.append(
            DecisionFactor(
                name="price_range",
                value=f"Rs. {market_indicators.lowest_price} - Rs. {market_indicators.highest_price}",
                observation=(
                    f"Recorded prices span from a low of Rs. {market_indicators.lowest_price} "
                    f"to a high of Rs. {market_indicators.highest_price}."
                ),
            )
        )

        # Factor 3: Average price
        factors.append(
            DecisionFactor(
                name="average_price",
                value=f"Rs. {market_indicators.average_price}",
                observation=f"Arithmetic average of recorded observations is Rs. {market_indicators.average_price}.",
            )
        )

        # Factor 4: Observation count
        factors.append(
            DecisionFactor(
                name="observation_count",
                value=f"{count} observations",
                observation=f"Trend evaluation based on {count} observations up to {market_indicators.latest_observation_date}.",
            )
        )

        return MarketAssessmentResponse(
            crop_name=crop_name,
            market_name=market_name,
            status=status_val,
            data_sufficiency="sufficient",
            factors=factors,
        )
