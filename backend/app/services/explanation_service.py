"""
Explanation Service and Provider Layer for the Farmer Decision Support System.
Translates structured domain indicators, rule-based decision assessments,
and baseline ML price predictions into transparent, farmer-friendly explanations.

Strictly adheres to:
1. Four distinct data categories: Observed, Calculated, Predicted, Assessment.
2. Provider-independent architecture via ExplanationProvider ABC.
3. Zero directive advice: No harvest recommendations, no sell recommendations.
4. Zero fabricated or demo data.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.core.exceptions import EntityNotFoundException
from app.ml.services.prediction_service import MarketPricePredictionService
from app.repositories.crop_repository import CropRepository
from app.repositories.farm_repository import FarmRepository
from app.repositories.crop_observation_repository import CropObservationRepository
from app.repositories.weather_observation_repository import WeatherObservationRepository
from app.repositories.market_observation_repository import MarketObservationRepository
from app.schemas.explanation import (
    ObservedDataBreakdown,
    CalculatedDataBreakdown,
    PredictedDataBreakdown,
    AssessmentDataBreakdown,
    CropExplanationResponse,
)
from app.services.crop_indicator_service import CropIndicatorService
from app.services.weather_indicator_service import WeatherIndicatorService
from app.services.market_indicator_service import MarketIndicatorService
from app.services.decision_engine_service import DecisionEngineService


class ExplanationProvider(ABC):
    """Abstract interface for explanation generation strategies."""

    @abstractmethod
    def generate_explanation(
        self,
        crop_name: str,
        farm_name: str,
        farm_location: str,
        observed: ObservedDataBreakdown,
        calculated: CalculatedDataBreakdown,
        predicted: Optional[PredictedDataBreakdown],
        assessment: AssessmentDataBreakdown,
    ) -> Dict[str, Any]:
        """
        Generates farmer-friendly texts and system limitations.

        Returns a dictionary containing:
          - summary: str
          - decision_explanation: str
          - weather_explanation: str
          - market_explanation: str
          - prediction_explanation: Optional[str]
          - limitations: List[str]
          - provider_name: str
        """
        pass


class RuleBasedExplanationProvider(ExplanationProvider):
    """
    Deterministic rule-based explanation provider.
    Synthesizes factual indicators into plain, accessible language
    without external API keys, network calls, or black-box non-determinism.
    """

    def generate_explanation(
        self,
        crop_name: str,
        farm_name: str,
        farm_location: str,
        observed: ObservedDataBreakdown,
        calculated: CalculatedDataBreakdown,
        predicted: Optional[PredictedDataBreakdown],
        assessment: AssessmentDataBreakdown,
    ) -> Dict[str, Any]:
        # 1. Harvest & Decision Assessment Explanation
        decision_text = self._explain_decision(observed, calculated, assessment)

        # 2. Weather Explanation
        weather_text = self._explain_weather(observed, calculated)

        # 3. Market Explanation
        market_text = self._explain_market(crop_name, observed, calculated, assessment)

        # 4. Prediction Explanation
        prediction_text = self._explain_prediction(observed, predicted)

        # 5. High-Level Summary Synthesis
        summary_text = self._synthesize_summary(
            crop_name=crop_name,
            farm_name=farm_name,
            observed=observed,
            calculated=calculated,
            predicted=predicted,
            assessment=assessment,
        )

        # 6. System Caveats & Boundaries
        limitations = [
            "Observations reflect manual field entries and local sensor records rather than continuous automated telemetry.",
            "Weather indicators summarize historical farm records and do not guarantee future meteorological forecasts.",
            "Market price predictions are baseline statistical projections based on historical patterns and cannot predict sudden mandi disruptions, regulatory changes, or transportation shocks.",
            "Decision assessments explain observed agricultural indicators; final harvest timing and selling decisions remain the sole responsibility of the farmer.",
            "Field observations older than 30 days are considered stale and require fresh scouting.",
        ]

        return {
            "summary": summary_text,
            "decision_explanation": decision_text,
            "weather_explanation": weather_text,
            "market_explanation": market_text,
            "prediction_explanation": prediction_text,
            "limitations": limitations,
            "provider_name": "rule-based-deterministic",
        }

    def _explain_decision(
        self,
        observed: ObservedDataBreakdown,
        calculated: CalculatedDataBreakdown,
        assessment: AssessmentDataBreakdown,
    ) -> str:
        status = assessment.harvest_status
        stage = observed.crop_stage
        health = observed.crop_health
        days_since = calculated.days_since_latest_crop_observation

        if status == "insufficient_data":
            if observed.crop_observations_count == 0:
                return (
                    "No crop observations have been recorded for this planting yet. "
                    "Field scouting is necessary to observe and record current growth stage and crop health."
                )
            if days_since is not None and days_since > 30:
                return (
                    f"The latest field observation was recorded {days_since} days ago "
                    f"(recorded stage: '{stage or 'unknown'}'). "
                    "Because conditions can change rapidly over a month, fresh field scouting is required to verify maturity."
                )
            return "Current recorded crop data is insufficient to assess harvest readiness."

        stage_str = stage.replace("_", " ") if stage else "unknown"
        health_str = f", with {health} health condition reported" if health else ""

        if status == "maturity_observed":
            recency_str = "today" if days_since == 0 else f"{days_since} days ago"
            return (
                f"The crop was observed at '{stage_str}' stage ({recency_str}){health_str}. "
                "This indicates the crop has reached physiological maturity based on recorded field visits."
            )
        elif status == "approaching":
            return (
                f"The crop is currently recorded at '{stage_str}' stage{health_str}. "
                "The planting is progressing toward maturity but has not yet reached full harvest stage."
            )
        else:
            return (
                f"The crop is currently recorded at '{stage_str}' stage{health_str}. "
                "It is in an early vegetative or flowering development phase and has not reached maturity."
            )

    def _explain_weather(
        self,
        observed: ObservedDataBreakdown,
        calculated: CalculatedDataBreakdown,
    ) -> str:
        count = observed.weather_observations_count
        if count == 0:
            return (
                "No weather observations have been recorded for this farm. "
                "Ambient drying, field curing conditions, and recent rainfall impacts cannot be determined."
            )

        parts = []
        if calculated.average_temperature_c is not None:
            parts.append(f"an average temperature of {calculated.average_temperature_c}°C")
        if calculated.average_humidity_percent is not None:
            parts.append(f"average humidity of {calculated.average_humidity_percent}%")
        if calculated.total_rainfall_mm is not None:
            parts.append(f"cumulative rainfall of {calculated.total_rainfall_mm} mm")
        if calculated.average_wind_speed_kmh is not None:
            parts.append(f"average wind speeds of {calculated.average_wind_speed_kmh} km/h")

        weather_summary = ", ".join(parts) if parts else "recent atmospheric readings"
        latest = observed.latest_weather or {}
        latest_str = ""
        if latest.get("temperature_c") is not None:
            latest_str = f" Latest reading on {latest.get('observed_at') or 'recent date'}: {latest.get('temperature_c')}°C and {latest.get('humidity_percent')}% humidity."

        return (
            f"Based on {count} recorded weather observation(s), the farm environment exhibits {weather_summary}."
            f"{latest_str}"
        )

    def _explain_market(
        self,
        crop_name: str,
        observed: ObservedDataBreakdown,
        calculated: CalculatedDataBreakdown,
        assessment: AssessmentDataBreakdown,
    ) -> str:
        count = observed.market_observations_count
        if count == 0:
            return (
                f"No mandi market price records exist for {crop_name}. "
                "Trading trends and price momentum cannot be determined without market observations."
            )

        latest_price = observed.latest_market_price
        latest_date = observed.latest_market_date or "the latest market date"

        if count == 1:
            return (
                f"A single mandi observation is recorded for {crop_name} at Rs. {latest_price} / Quintal on {latest_date}. "
                "Additional daily observations are needed to determine price trajectory."
            )

        trend = assessment.market_trend_status
        change = calculated.market_price_change
        pct = calculated.market_price_change_percentage
        change_str = ""
        if change is not None and pct is not None:
            sign = "+" if change > 0 else ""
            change_str = f" (change of {sign}{change} Rs/Quintal or {sign}{pct}%)"

        if trend == "price_rising":
            return (
                f"Mandi price records for {crop_name} show an upward trend across {count} observations, "
                f"with the latest price at Rs. {latest_price} / Quintal{change_str}."
            )
        elif trend == "price_falling":
            return (
                f"Mandi price records for {crop_name} show a downward trend across {count} observations, "
                f"with the latest price at Rs. {latest_price} / Quintal{change_str}."
            )
        else:
            return (
                f"Mandi price records for {crop_name} reflect relatively stable pricing across {count} observations, "
                f"with the latest price at Rs. {latest_price} / Quintal{change_str}."
            )

    def _explain_prediction(
        self,
        observed: ObservedDataBreakdown,
        predicted: Optional[PredictedDataBreakdown],
    ) -> Optional[str]:
        if predicted is None:
            return (
                "Price forecast is not available because there are no recent mandi price observations to initialize the baseline model."
            )

        forecast = predicted.predicted_next_modal_price
        current = observed.latest_market_price
        diff = predicted.price_difference_from_current
        direction = predicted.direction or "unchanged"
        pct = predicted.price_difference_percentage

        diff_str = ""
        if diff is not None and pct is not None:
            diff_abs = abs(diff)
            pct_abs = abs(pct)
            diff_str = f" ({diff_abs} Rs/Quintal or {pct_abs}% {direction} than the recorded price of Rs. {current})"

        return (
            f"The baseline statistical model ({predicted.model_name or 'Baseline'}) projects a next-day modal price of "
            f"Rs. {forecast} / Quintal{diff_str}. "
            "This projection is an automated mathematical estimate from historical data patterns and does not guarantee market transactions."
        )

    def _synthesize_summary(
        self,
        crop_name: str,
        farm_name: str,
        observed: ObservedDataBreakdown,
        calculated: CalculatedDataBreakdown,
        predicted: Optional[PredictedDataBreakdown],
        assessment: AssessmentDataBreakdown,
    ) -> str:
        # Crop status sentence
        if assessment.harvest_status == "maturity_observed":
            crop_sentence = f"{crop_name} at {farm_name} has reached maturity based on recent field observations."
        elif assessment.harvest_status == "approaching":
            crop_sentence = f"{crop_name} at {farm_name} is approaching maturity in the fruiting stage."
        elif assessment.harvest_status == "not_ready":
            stage_str = observed.crop_stage.replace("_", " ") if observed.crop_stage else "vegetative"
            crop_sentence = f"{crop_name} at {farm_name} is in the {stage_str} stage and has not reached maturity."
        else:
            crop_sentence = f"{crop_name} at {farm_name} has insufficient field observation data for maturity assessment."

        # Weather context sentence
        if observed.weather_observations_count > 0 and calculated.average_temperature_c is not None:
            weather_sentence = f"Farm weather records indicate {calculated.average_temperature_c}°C average temperature and {calculated.total_rainfall_mm or 0.0} mm rainfall."
        else:
            weather_sentence = "No local farm weather data is currently logged."

        # Market context sentence
        if observed.market_observations_count > 0 and observed.latest_market_price is not None:
            trend_map = {
                "price_rising": "upward",
                "price_falling": "downward",
                "price_stable": "stable",
                "insufficient_data": "single-point",
            }
            trend_desc = trend_map.get(assessment.market_trend_status, "recorded")
            market_sentence = f"Market observations indicate a latest price of Rs. {observed.latest_market_price} / Quintal with a {trend_desc} trend."
        else:
            market_sentence = "Market price observations are not yet recorded for this crop."

        return f"{crop_sentence} {weather_sentence} {market_sentence}"


class ExplanationService:
    """
    Coordinates data retrieval, indicator calculation, decision evaluation,
    and baseline price prediction to deliver structured crop explanations.
    """

    def __init__(
        self,
        db: Session,
        provider: Optional[ExplanationProvider] = None,
        ml_service: Optional[MarketPricePredictionService] = None,
    ):
        self.db = db
        self.provider = provider or RuleBasedExplanationProvider()
        self.crop_repo = CropRepository(db)
        self.farm_repo = FarmRepository(db)
        self.crop_obs_repo = CropObservationRepository(db)
        self.weather_obs_repo = WeatherObservationRepository(db)
        self.market_obs_repo = MarketObservationRepository(db)
        self.crop_indicator_service = CropIndicatorService(db)
        self.weather_indicator_service = WeatherIndicatorService(db)
        self.market_indicator_service = MarketIndicatorService(db)
        self.decision_engine = DecisionEngineService(db)
        self.ml_service = ml_service or MarketPricePredictionService()

    def get_crop_explanation(self, crop_id: int) -> CropExplanationResponse:
        """
        Gathers domain indicators and evaluations, invokes the explanation provider,
        and constructs the full CropExplanationResponse.
        """
        crop = self.crop_repo.get_by_id(crop_id)
        if not crop:
            raise EntityNotFoundException("Crop", crop_id)

        farm = self.farm_repo.get_by_id(crop.farm_id)
        farm_name = farm.name if farm else "Unknown Farm"
        farm_location = farm.location if farm else "Unknown Location"

        # 1. Fetch Indicators
        crop_indicators = self.crop_indicator_service.get_crop_indicators(crop_id)
        weather_indicators = self.weather_indicator_service.get_farm_weather_indicators(crop.farm_id)
        market_indicators = self.market_indicator_service.get_market_indicators(crop_name=crop.crop_name)

        # 2. Fetch Decision Engine Assessments
        harvest_assessment = self.decision_engine.evaluate_harvest_assessment(crop_id)
        market_assessment = self.decision_engine.evaluate_market_assessment(crop_name=crop.crop_name)

        # 3. Assemble Observed Breakdown
        latest_weather_dict = None
        if weather_indicators.observation_count > 0:
            latest_weather_dict = {
                "temperature_c": weather_indicators.latest_temperature,
                "humidity_percent": weather_indicators.latest_humidity,
                "rainfall_mm": weather_indicators.latest_rainfall,
                "wind_speed_kmh": weather_indicators.latest_wind_speed,
                "observed_at": str(weather_indicators.latest_observed_at) if weather_indicators.latest_observed_at else None,
            }

        observed = ObservedDataBreakdown(
            crop_stage=crop_indicators.latest_growth_stage,
            crop_health=crop_indicators.latest_health_status,
            latest_crop_observation_date=str(crop_indicators.latest_observation_date) if crop_indicators.latest_observation_date else None,
            crop_observations_count=crop_indicators.observation_count,
            latest_weather=latest_weather_dict,
            weather_observations_count=weather_indicators.observation_count,
            latest_market_price=market_indicators.latest_price,
            latest_market_date=str(market_indicators.latest_observation_date) if market_indicators.latest_observation_date else None,
            market_observations_count=market_indicators.observation_count,
        )

        # 4. Assemble Calculated Breakdown
        calculated = CalculatedDataBreakdown(
            days_since_latest_crop_observation=crop_indicators.days_since_latest_observation,
            average_temperature_c=weather_indicators.average_temperature,
            total_rainfall_mm=weather_indicators.total_rainfall,
            average_humidity_percent=weather_indicators.average_humidity,
            average_wind_speed_kmh=weather_indicators.average_wind_speed,
            market_price_change=market_indicators.price_change,
            market_price_change_percentage=market_indicators.price_change_percentage,
            market_average_price=market_indicators.average_price,
            market_lowest_price=market_indicators.lowest_price,
            market_highest_price=market_indicators.highest_price,
        )

        # 5. Assemble Baseline Prediction (if market observation exists)
        predicted: Optional[PredictedDataBreakdown] = None
        if market_indicators.latest_price is not None and market_indicators.latest_price > 0:
            try:
                pred_result = self.ml_service.predict_next_day_price(
                    current_modal_price=market_indicators.latest_price,
                    price_spread=0.0,
                    arrivals_tonnes=0.0,
                )
                pred_price = pred_result["predicted_next_modal_price"]
                diff = round(pred_price - market_indicators.latest_price, 2)
                diff_pct = round((diff / market_indicators.latest_price) * 100, 2)
                if diff > 0:
                    direction = "higher"
                elif diff < 0:
                    direction = "lower"
                else:
                    direction = "unchanged"

                predicted = PredictedDataBreakdown(
                    predicted_next_modal_price=pred_price,
                    currency=pred_result.get("currency", "Rs/Quintal"),
                    model_name=pred_result.get("model_name"),
                    model_version=pred_result.get("model_version"),
                    price_difference_from_current=diff,
                    price_difference_percentage=diff_pct,
                    direction=direction,
                )
            except Exception:
                predicted = None

        # 6. Assemble Assessment Breakdown
        assessment = AssessmentDataBreakdown(
            harvest_status=harvest_assessment.status,
            harvest_data_sufficiency=harvest_assessment.data_sufficiency,
            market_trend_status=market_assessment.status,
            market_data_sufficiency=market_assessment.data_sufficiency,
        )

        # 7. Generate Explanations via Provider
        provider_output = self.provider.generate_explanation(
            crop_name=crop.crop_name,
            farm_name=farm_name,
            farm_location=farm_location,
            observed=observed,
            calculated=calculated,
            predicted=predicted,
            assessment=assessment,
        )

        return CropExplanationResponse(
            crop_id=crop.id,
            crop_name=crop.crop_name,
            farm_name=farm_name,
            farm_location=farm_location,
            summary=provider_output["summary"],
            decision_explanation=provider_output["decision_explanation"],
            weather_explanation=provider_output["weather_explanation"],
            market_explanation=provider_output["market_explanation"],
            prediction_explanation=provider_output.get("prediction_explanation"),
            observations=observed,
            calculated=calculated,
            predicted=predicted,
            assessment=assessment,
            limitations=provider_output["limitations"],
            provider=provider_output.get("provider_name", "rule-based-deterministic"),
            generated_at=datetime.utcnow(),
        )
