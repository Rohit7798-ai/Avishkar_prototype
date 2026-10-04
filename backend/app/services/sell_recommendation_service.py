"""
Sell Recommendation Engine.
Produces transparent, deterministic selling recommendations based on
recorded mandi price momentum, price stability thresholds, and baseline ML forecasts.
Does NOT guarantee future prices, claim certainty, or combine with harvest decisions.
"""

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.ml.services.prediction_service import MarketPricePredictionService
from app.schemas.recommendation import SellRecommendation
from app.services.market_indicator_service import MarketIndicatorService
from app.services.decision_engine_service import DecisionEngineService


class SellRecommendationService:
    """Evaluates commercial selling posture from grounded market indicators and baseline forecasts."""

    def __init__(
        self,
        db: Session,
        ml_service: Optional[MarketPricePredictionService] = None,
    ):
        self.market_indicator_service = MarketIndicatorService(db)
        self.decision_engine = DecisionEngineService(db)
        self.ml_service = ml_service or MarketPricePredictionService()

    def evaluate_sell_recommendation(
        self,
        crop_name: str,
        market_name: Optional[str] = None,
    ) -> SellRecommendation:
        market_indicators = self.market_indicator_service.get_market_indicators(
            crop_name=crop_name, market_name=market_name
        )
        market_assessment = self.decision_engine.evaluate_market_assessment(
            crop_name=crop_name, market_name=market_name
        )

        count = market_indicators.observation_count
        latest_price = market_indicators.latest_price
        trend = market_assessment.status

        # Try baseline prediction if latest price is valid
        pred_result: Optional[Dict[str, Any]] = None
        predicted_price: Optional[float] = None
        pred_diff: Optional[float] = None
        pred_pct: Optional[float] = None

        if latest_price is not None and latest_price > 0:
            try:
                pred_result = self.ml_service.predict_next_day_price(
                    current_modal_price=latest_price,
                    price_spread=0.0,
                    arrivals_tonnes=0.0,
                )
                predicted_price = pred_result["predicted_next_modal_price"]
                pred_diff = round(predicted_price - latest_price, 2)
                pred_pct = round((pred_diff / latest_price) * 100, 2)
            except Exception:
                pred_result = None

        supporting_factors: Dict[str, Any] = {
            "current_modal_price": latest_price,
            "price_change": market_indicators.price_change,
            "price_change_percentage": market_indicators.price_change_percentage,
            "observation_count": count,
            "trend_status": trend,
            "predicted_next_modal_price": predicted_price,
            "predicted_difference": pred_diff,
            "predicted_difference_percentage": pred_pct,
            "model_name": pred_result.get("model_name") if pred_result else None,
            "model_version": pred_result.get("model_version") if pred_result else None,
        }

        # Case 1: Insufficient Market History (0 or 1 observation)
        if count < 2:
            reasons = [f.observation for f in market_assessment.factors]
            risks = [
                "Insufficient market history prevents trend detection.",
                "Baseline price forecast cannot be reliably initialized without multiple historical records.",
            ]
            return SellRecommendation(
                recommendation="insufficient_data",
                status="insufficient_data",
                confidence="insufficient",
                reasons=reasons,
                supporting_factors=supporting_factors,
                risks=risks,
                data_sufficiency="insufficient",
            )

        # Base risks common to all multi-observation commercial market situations
        common_risks = [
            "Price forecasts are statistical baseline estimates and do not guarantee actual mandi transactions.",
            "Sudden arrival surges or policy changes at local APMC mandis can alter price momentum unexpectedly.",
        ]
        if count < 4:
            common_risks.append(f"Limited historical dataset (only {count} recorded observations).")

        # Case 2: Falling Prices -> sell_now
        if trend == "price_falling":
            change_val = abs(market_indicators.price_change) if market_indicators.price_change else 0.0
            change_pct = abs(market_indicators.price_change_percentage) if market_indicators.price_change_percentage else 0.0
            reasons = [
                f"Recorded mandi prices show a downward trend with a price decline of Rs. {change_val} ({change_pct}%).",
            ]
            if predicted_price is not None:
                sign = "+" if pred_diff and pred_diff > 0 else ""
                reasons.append(
                    f"Baseline model estimate projects next-day modal price near Rs. {predicted_price} / Quintal ({sign}{pred_diff} Rs/Q difference)."
                )
                reasons.append("Selling now mitigates risk of further price erosion in a weakening market.")
            else:
                reasons.append("Selling now reduces exposure to continuing downward market momentum.")

            confidence = "high" if (count >= 3 and predicted_price is not None) else "medium"

            return SellRecommendation(
                recommendation="sell_now",
                status="sell_now",
                confidence=confidence,
                reasons=reasons,
                supporting_factors=supporting_factors,
                risks=common_risks,
                data_sufficiency=market_assessment.data_sufficiency,
            )

        # Case 3: Rising Prices -> hold_for_observation
        if trend == "price_rising":
            change_val = market_indicators.price_change or 0.0
            change_pct = market_indicators.price_change_percentage or 0.0
            reasons = [
                f"Recorded mandi prices show an upward trend with a price gain of Rs. {change_val} (+{change_pct}%).",
            ]
            if predicted_price is not None:
                sign = "+" if pred_diff and pred_diff > 0 else ""
                reasons.append(
                    f"Baseline model estimate indicates next-day modal price around Rs. {predicted_price} / Quintal ({sign}{pred_diff} Rs/Q difference)."
                )
                reasons.append("Holding produce for ongoing observation allows monitoring whether positive price momentum continues.")
            else:
                reasons.append("Holding for observation permits tracking price gains across subsequent trading sessions.")

            holding_risks = list(common_risks)
            holding_risks.append("Holding produce incurs storage cost, physical shrinkage, and spoilage risk for perishable crops.")

            confidence = "high" if (count >= 3 and predicted_price is not None) else "medium"

            return SellRecommendation(
                recommendation="hold_for_observation",
                status="hold_for_observation",
                confidence=confidence,
                reasons=reasons,
                supporting_factors=supporting_factors,
                risks=holding_risks,
                data_sufficiency=market_assessment.data_sufficiency,
            )

        # Case 4: Price Stable -> price_stable
        reasons = [
            f"Recorded mandi prices reflect stability within a ±2.0% band (latest price: Rs. {latest_price} / Quintal).",
        ]
        if predicted_price is not None:
            reasons.append(
                f"Baseline model estimate projects next-day modal price at Rs. {predicted_price} / Quintal, confirming market equilibrium."
            )
        reasons.append("Market exhibits balanced supply and demand without decisive directional momentum.")

        confidence = "high" if count >= 3 else "medium"

        return SellRecommendation(
            recommendation="price_stable",
            status="price_stable",
            confidence=confidence,
            reasons=reasons,
            supporting_factors=supporting_factors,
            risks=common_risks,
            data_sufficiency=market_assessment.data_sufficiency,
        )
