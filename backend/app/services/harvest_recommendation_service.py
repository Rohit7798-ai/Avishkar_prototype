"""
Harvest Recommendation Engine.
Produces transparent, deterministic harvest recommendations based strictly
on recorded crop observations, recency, health, and farm weather indicators.
Does NOT combine harvest and sell decisions, and does NOT generate black-box scores.
"""

from typing import List, Optional
from sqlalchemy.orm import Session

from app.core.exceptions import EntityNotFoundException
from app.repositories.crop_repository import CropRepository
from app.schemas.recommendation import HarvestRecommendation
from app.services.crop_indicator_service import CropIndicatorService
from app.services.weather_indicator_service import WeatherIndicatorService
from app.services.decision_engine_service import DecisionEngineService


class HarvestRecommendationService:
    """Evaluates harvest readiness from grounded field indicators."""

    def __init__(self, db: Session):
        self.crop_repo = CropRepository(db)
        self.crop_indicator_service = CropIndicatorService(db)
        self.weather_indicator_service = WeatherIndicatorService(db)
        self.decision_engine = DecisionEngineService(db)

    def evaluate_harvest_recommendation(self, crop_id: int) -> HarvestRecommendation:
        crop = self.crop_repo.get_by_id(crop_id)
        if not crop:
            raise EntityNotFoundException("Crop", crop_id)

        crop_indicators = self.crop_indicator_service.get_crop_indicators(crop_id)
        weather_indicators = self.weather_indicator_service.get_farm_weather_indicators(crop.farm_id)
        harvest_assessment = self.decision_engine.evaluate_harvest_assessment(crop_id)

        stage = crop_indicators.latest_growth_stage
        health = crop_indicators.latest_health_status
        days_since = crop_indicators.days_since_latest_observation
        obs_count = crop_indicators.observation_count
        weather_count = weather_indicators.observation_count

        supporting_factors = {
            "growth_stage": stage,
            "health_status": health,
            "observation_date": str(crop_indicators.latest_observation_date) if crop_indicators.latest_observation_date else None,
            "days_since_observation": days_since,
            "observation_count": obs_count,
            "expected_harvest_date": str(crop.expected_harvest_date) if crop.expected_harvest_date else None,
            "weather_observations_count": weather_count,
            "latest_temperature_c": weather_indicators.latest_temperature,
            "latest_rainfall_mm": weather_indicators.latest_rainfall,
        }

        # Case 1: Insufficient Data (0 observations or stale > 30 days)
        if harvest_assessment.status == "insufficient_data":
            reasons = [f.observation for f in harvest_assessment.factors]
            risks: List[str] = []
            if obs_count == 0:
                risks.append("No recorded field observations; cannot determine crop maturity or health.")
            elif days_since is not None and days_since > 30:
                risks.append(f"Observation is {days_since} days old (exceeds 30-day freshness limit); field scouting required.")

            if weather_count == 0:
                risks.append("Weather information unavailable for this farm parcel.")

            return HarvestRecommendation(
                recommendation="insufficient_data",
                status="insufficient_data",
                confidence="insufficient",
                reasons=reasons,
                supporting_factors=supporting_factors,
                risks=risks,
                data_sufficiency="insufficient",
            )

        # Case 2: Maturity Observed -> harvest_now
        if stage in ("maturity", "post_maturity"):
            reasons = [
                f"Crop has reached physiological maturity (recorded stage: '{stage}' on {crop_indicators.latest_observation_date}).",
            ]
            if health in ("stressed", "damaged"):
                reasons.append(f"Crop health is reported as '{health}'; prompt harvest is warranted to prevent field deterioration.")
            else:
                reasons.append(f"Crop health is reported as '{health}', indicating optimal harvest condition.")

            if weather_count > 0 and weather_indicators.latest_temperature is not None:
                reasons.append(
                    f"Ambient farm weather shows {weather_indicators.latest_temperature}°C and {weather_indicators.latest_rainfall}mm rainfall."
                )

            # Determine confidence
            if days_since is not None and days_since <= 7 and weather_count > 0:
                confidence = "high"
            elif days_since is not None and days_since <= 14:
                confidence = "medium"
            else:
                confidence = "low"

            risks = []
            if weather_count == 0:
                risks.append("Weather information unavailable; field drying and curing conditions cannot be verified.")
            if days_since is not None and days_since > 14:
                risks.append(f"Observation is {days_since} days old; verify field condition before bulk harvesting.")
            if health in ("stressed", "damaged"):
                risks.append(f"Reported crop health is '{health}', which may impact marketable grade.")
            if weather_indicators.latest_rainfall is not None and weather_indicators.latest_rainfall > 10.0:
                risks.append("Recent rainfall recorded; wet soil conditions may impede field harvesting.")

            return HarvestRecommendation(
                recommendation="harvest_now",
                status="harvest_now",
                confidence=confidence,
                reasons=reasons,
                supporting_factors=supporting_factors,
                risks=risks,
                data_sufficiency=harvest_assessment.data_sufficiency,
            )

        # Case 3: Fruiting -> approaching_harvest
        if stage == "fruiting":
            reasons = [
                f"Crop is currently in fruiting / bulb development stage and progressing toward physiological maturity.",
            ]
            if crop.expected_harvest_date:
                reasons.append(f"Planned expected harvest date is {crop.expected_harvest_date}.")
            reasons.append(f"Current plant health is reported as '{health}'.")

            if days_since is not None and days_since <= 7:
                confidence = "high"
            elif days_since is not None and days_since <= 20:
                confidence = "medium"
            else:
                confidence = "low"

            risks = []
            if weather_count == 0:
                risks.append("Weather information unavailable for monitoring late-season maturation.")
            if days_since is not None and days_since > 14:
                risks.append(f"Latest observation recorded {days_since} days ago; monitor field as harvest window approaches.")
            if health in ("stressed", "damaged"):
                risks.append(f"Crop health exhibits {health} symptoms during bulb development.")

            return HarvestRecommendation(
                recommendation="approaching_harvest",
                status="approaching_harvest",
                confidence=confidence,
                reasons=reasons,
                supporting_factors=supporting_factors,
                risks=risks,
                data_sufficiency=harvest_assessment.data_sufficiency,
            )

        # Case 4: Early / Vegetative / Flowering -> not_ready
        stage_display = stage.replace("_", " ") if stage else "vegetative"
        reasons = [
            f"Crop is in early {stage_display} phase and has not developed mature harvestable yield.",
        ]
        if crop.expected_harvest_date:
            reasons.append(f"Expected harvest date is scheduled for {crop.expected_harvest_date}.")

        confidence = "high" if (days_since is not None and days_since <= 14) else "medium"

        risks = []
        if weather_count == 0:
            risks.append("No weather tracking data recorded for this parcel.")
        if health in ("stressed", "damaged"):
            risks.append(f"Crop exhibits {health} symptoms during active vegetative growth.")

        return HarvestRecommendation(
            recommendation="not_ready",
            status="not_ready",
            confidence=confidence,
            reasons=reasons,
            supporting_factors=supporting_factors,
            risks=risks,
            data_sufficiency=harvest_assessment.data_sufficiency,
        )
