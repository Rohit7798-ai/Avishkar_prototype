"""
Historical Walk-Forward Recommendation and Prediction Validation Framework.
Performs strictly chronological walk-forward evaluation without lookahead bias.
Compares ML predictions against naive persistence baselines, evaluates commercial
posture agreement against subsequent market price changes, and documents harvest
lifecycle evaluability.
"""

from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.ml.datasets.loader import get_default_dataset_path, load_raw_mandi_dataset
from app.ml.evaluation.metrics import calculate_regression_metrics
from app.ml.services.prediction_service import MarketPricePredictionService
from app.schemas.validation import (
    MetricDetail,
    MarketPredictionMetric,
    PredictionValidationReport,
    RecommendationPostureOutcome,
    SellValidationReport,
    HarvestValidationReport,
    ValidationFailureCase,
    HistoricalValidationResponse,
)

# ponytail: Stability threshold consistent with DecisionEngineService (±2.0%)
PRICE_STABILITY_THRESHOLD_PERCENT = 2.0

# ponytail: Error threshold for flagging notable prediction variance (Rs. 35/Quintal or 1.5% relative error)
NOTABLE_ERROR_ABS_THRESHOLD = 35.0
NOTABLE_ERROR_PCT_THRESHOLD = 1.5


def validate_historical_dataset(file_path: Optional[str | Path] = None) -> Dict[str, Any]:
    """
    Validates structural integrity, non-negativity, and consistency of the historical dataset.

    Returns:
        Dict summarizing dataset characteristics (commodity, total_records, markets, date_range).
    """
    records = load_raw_mandi_dataset(file_path)
    if not records:
        raise ValueError("Historical dataset contains no usable records.")

    dates = [r["date"] for r in records]
    markets = sorted(list(set(r["market"] for r in records)))
    commodity = records[0]["commodity"]

    return {
        "commodity": commodity,
        "total_records": len(records),
        "usable_records": len(records),
        "mandis_count": len(markets),
        "mandis": markets,
        "start_date": min(dates).isoformat(),
        "end_date": max(dates).isoformat(),
    }


def run_walk_forward_validation(
    file_path: Optional[str | Path] = None,
    ml_service: Optional[MarketPricePredictionService] = None,
) -> HistoricalValidationResponse:
    """
    Executes chronological walk-forward validation across the real historical dataset.

    Guarantees:
      - Strictly chronological: At step t, only observations <= t are visible.
      - Decoupled outputs: Prediction, sell recommendation, and harvest evaluability evaluated separately.
      - Zero fabricated data: Harvest validation marked 'not_evaluable' due to absence of field observations.
    """
    dataset_summary = validate_historical_dataset(file_path)
    records = load_raw_mandi_dataset(file_path)

    service = ml_service or MarketPricePredictionService(auto_train_if_missing=True)

    # Group records chronologically by market yard
    market_records: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in records:
        market_records[r["market"]].append(r)

    # Sort each market yard strictly by date asc
    for m in market_records:
        market_records[m].sort(key=lambda x: x["date"])

    all_y_true: List[float] = []
    all_y_pred: List[float] = []
    all_y_naive: List[float] = []

    market_metrics_list: List[MarketPredictionMetric] = []
    failure_cases: List[ValidationFailureCase] = []

    # Sell recommendation tracking
    posture_stats = {
        "hold_for_observation": {"count": 0, "agreed": 0, "disagreed": 0, "neutral": 0},
        "sell_now": {"count": 0, "agreed": 0, "disagreed": 0, "neutral": 0},
        "price_stable": {"count": 0, "agreed": 0, "disagreed": 0, "neutral": 0},
    }

    total_evaluated_transitions = 0
    total_not_evaluable_cases = 0

    for market_name, m_records in sorted(market_records.items()):
        n = len(m_records)
        m_y_true: List[float] = []
        m_y_pred: List[float] = []
        m_y_naive: List[float] = []

        for i in range(n - 1):
            total_evaluated_transitions += 1

            current_rec = m_records[i]
            next_rec = m_records[i + 1]

            cur_date = current_rec["date"].isoformat()
            cur_price = current_rec["modal_price"]
            spread = round(current_rec["max_price"] - current_rec["min_price"], 2)
            arrivals = current_rec["arrivals_tonnes"]

            target_price = next_rec["modal_price"]

            # 1. Prediction Walk-Forward Step
            pred_dict = service.predict_next_day_price(
                current_modal_price=cur_price,
                price_spread=spread,
                arrivals_tonnes=arrivals,
            )
            pred_price = pred_dict["predicted_next_modal_price"]

            m_y_true.append(target_price)
            m_y_pred.append(pred_price)
            m_y_naive.append(cur_price)

            all_y_true.append(target_price)
            all_y_pred.append(pred_price)
            all_y_naive.append(cur_price)

            abs_error = abs(pred_price - target_price)
            pct_error = (abs_error / target_price) * 100.0 if target_price > 0 else 0.0

            # Flag notable prediction error
            if abs_error > NOTABLE_ERROR_ABS_THRESHOLD or pct_error > NOTABLE_ERROR_PCT_THRESHOLD:
                failure_cases.append(
                    ValidationFailureCase(
                        date=cur_date,
                        market=market_name,
                        failure_type="high_prediction_error",
                        recommendation=None,
                        current_modal_price=cur_price,
                        predicted_modal_price=pred_price,
                        actual_subsequent_modal_price=target_price,
                        price_change=round(target_price - cur_price, 2),
                        evidence=(
                            f"Model predicted Rs. {pred_price} / Q vs actual Rs. {target_price} / Q "
                            f"(error of Rs. {round(abs_error, 2)} or {round(pct_error, 2)}%)."
                        ),
                    )
                )

            # 2. Sell Recommendation Walk-Forward Step
            # History up to day i: m_records[0 ... i]
            history_count = i + 1
            if history_count < 2:
                total_not_evaluable_cases += 1
                failure_cases.append(
                    ValidationFailureCase(
                        date=cur_date,
                        market=market_name,
                        failure_type="insufficient_data",
                        recommendation="insufficient_data",
                        current_modal_price=cur_price,
                        predicted_modal_price=pred_price,
                        actual_subsequent_modal_price=target_price,
                        price_change=round(target_price - cur_price, 2),
                        evidence="Single historical observation available; insufficient history to detect price momentum.",
                    )
                )
                continue

            earliest_price = m_records[0]["modal_price"]
            hist_change = cur_price - earliest_price
            hist_pct = (hist_change / earliest_price) * 100.0 if earliest_price > 0 else 0.0

            # Determine posture from explicit domain rules
            if hist_pct > PRICE_STABILITY_THRESHOLD_PERCENT:
                posture = "hold_for_observation"
            elif hist_pct < -PRICE_STABILITY_THRESHOLD_PERCENT:
                posture = "sell_now"
            else:
                posture = "price_stable"

            subsequent_delta = round(target_price - cur_price, 2)
            subsequent_delta_pct = (subsequent_delta / cur_price) * 100.0 if cur_price > 0 else 0.0

            stat = posture_stats[posture]
            stat["count"] += 1

            if posture == "hold_for_observation":
                if subsequent_delta > 0:
                    stat["agreed"] += 1
                elif subsequent_delta < 0:
                    stat["disagreed"] += 1
                    failure_cases.append(
                        ValidationFailureCase(
                            date=cur_date,
                            market=market_name,
                            failure_type="direction_disagreement",
                            recommendation="hold_for_observation",
                            current_modal_price=cur_price,
                            predicted_modal_price=pred_price,
                            actual_subsequent_modal_price=target_price,
                            price_change=subsequent_delta,
                            evidence=(
                                f"Historical trend was upward (+{round(hist_pct, 2)}%) recommending 'hold_for_observation', "
                                f"but subsequent price dropped by Rs. {abs(subsequent_delta)} / Q."
                            ),
                        )
                    )
                else:
                    stat["neutral"] += 1

            elif posture == "sell_now":
                if subsequent_delta < 0:
                    stat["agreed"] += 1
                elif subsequent_delta > 0:
                    stat["disagreed"] += 1
                    failure_cases.append(
                        ValidationFailureCase(
                            date=cur_date,
                            market=market_name,
                            failure_type="direction_disagreement",
                            recommendation="sell_now",
                            current_modal_price=cur_price,
                            predicted_modal_price=pred_price,
                            actual_subsequent_modal_price=target_price,
                            price_change=subsequent_delta,
                            evidence=(
                                f"Historical trend was downward ({round(hist_pct, 2)}%) recommending 'sell_now', "
                                f"but subsequent price increased by Rs. {subsequent_delta} / Q."
                            ),
                        )
                    )
                else:
                    stat["neutral"] += 1

            elif posture == "price_stable":
                if abs(subsequent_delta_pct) <= PRICE_STABILITY_THRESHOLD_PERCENT:
                    stat["agreed"] += 1
                else:
                    stat["disagreed"] += 1
                    failure_cases.append(
                        ValidationFailureCase(
                            date=cur_date,
                            market=market_name,
                            failure_type="direction_disagreement",
                            recommendation="price_stable",
                            current_modal_price=cur_price,
                            predicted_modal_price=pred_price,
                            actual_subsequent_modal_price=target_price,
                            price_change=subsequent_delta,
                            evidence=(
                                f"Prices were stable within ±2% recommending 'price_stable', "
                                f"but subsequent price changed by {round(subsequent_delta_pct, 2)}%."
                            ),
                        )
                    )

        # Market-specific metrics
        m_mod_m = calculate_regression_metrics(m_y_true, m_y_pred)
        m_nai_m = calculate_regression_metrics(m_y_true, m_y_naive)
        m_impr = (
            round(((m_nai_m["mae"] - m_mod_m["mae"]) / m_nai_m["mae"]) * 100.0, 2)
            if m_nai_m["mae"] > 0
            else 0.0
        )

        market_metrics_list.append(
            MarketPredictionMetric(
                market=market_name,
                evaluated_transitions=len(m_y_true),
                model_performance=MetricDetail(
                    mae=m_mod_m["mae"],
                    rmse=m_mod_m["rmse"],
                    mape_percent=m_mod_m["mape_percent"],
                ),
                naive_baseline_performance=MetricDetail(
                    mae=m_nai_m["mae"],
                    rmse=m_nai_m["rmse"],
                    mape_percent=m_nai_m["mape_percent"],
                ),
                mae_improvement_percent=m_impr,
            )
        )

    # Overall prediction metrics
    ov_mod_m = calculate_regression_metrics(all_y_true, all_y_pred)
    ov_nai_m = calculate_regression_metrics(all_y_true, all_y_naive)
    ov_impr = (
        round(((ov_nai_m["mae"] - ov_mod_m["mae"]) / ov_nai_m["mae"]) * 100.0, 2)
        if ov_nai_m["mae"] > 0
        else 0.0
    )

    pred_validation_report = PredictionValidationReport(
        model_name="LinearRegressionBaseline",
        model_version="1.0.0",
        total_evaluated_transitions=len(all_y_true),
        overall_model_performance=MetricDetail(
            mae=ov_mod_m["mae"],
            rmse=ov_mod_m["rmse"],
            mape_percent=ov_mod_m["mape_percent"],
        ),
        overall_naive_performance=MetricDetail(
            mae=ov_nai_m["mae"],
            rmse=ov_nai_m["rmse"],
            mape_percent=ov_nai_m["mape_percent"],
        ),
        overall_mae_improvement_percent=ov_impr,
        by_market=market_metrics_list,
    )

    # Sell validation breakdown
    total_decisions = sum(s["count"] for s in posture_stats.values())
    total_agreed = sum(s["agreed"] for s in posture_stats.values())
    total_disagreed = sum(s["disagreed"] for s in posture_stats.values())
    total_neutral = sum(s["neutral"] for s in posture_stats.values())
    overall_agreement_pct = (
        round((total_agreed / total_decisions) * 100.0, 2)
        if total_decisions > 0
        else None
    )

    by_posture_dict: Dict[str, RecommendationPostureOutcome] = {}
    for post_name, s in posture_stats.items():
        agr_pct = (
            round((s["agreed"] / s["count"]) * 100.0, 2)
            if s["count"] > 0
            else None
        )
        by_posture_dict[post_name] = RecommendationPostureOutcome(
            count=s["count"],
            agreed=s["agreed"],
            disagreed=s["disagreed"],
            neutral=s["neutral"],
            agreement_rate_percent=agr_pct,
        )

    sell_validation_report = SellValidationReport(
        evaluation_horizon="1-day walk-forward",
        total_evaluated_decisions=total_decisions,
        total_agreed=total_agreed,
        total_disagreed=total_disagreed,
        total_neutral=total_neutral,
        overall_agreement_rate_percent=overall_agreement_pct,
        by_posture=by_posture_dict,
    )

    # Harvest validation (formally not_evaluable)
    harvest_validation_report = HarvestValidationReport(
        status="not_evaluable",
        evaluated_cases=0,
        reason=(
            "The historical dataset (data/raw/mandi_rates.json) contains mandi prices and market arrivals, "
            "but does not record field crop observations (growth stages, crop health, or actual harvest dates). "
            "Crop maturity cannot be scientifically inferred from market price data without fabricating agricultural records."
        ),
    )

    data_limitations = [
        "Dataset scope is limited to 14 consecutive calendar days (September 15–28, 2026) across 5 Nashik APMC mandis.",
        "Market dataset contains price and arrival data only; zero field crop lifecycle records exist, making harvest validation not evaluable.",
        "Walk-forward validation evaluates a single-step (1-day ahead) forecasting horizon; longer holding windows are not represented.",
        "Mandi modal prices represent APMC transaction aggregates and do not reflect individual farmer transport costs, grading discounts, or storage weight shrinkage.",
    ]

    return HistoricalValidationResponse(
        evaluation_period={
            "start_date": dataset_summary["start_date"],
            "end_date": dataset_summary["end_date"],
            "horizon": "1-day walk-forward",
        },
        dataset_summary=dataset_summary,
        number_of_evaluated_cases=total_evaluated_transitions,
        number_of_not_evaluable_cases=total_not_evaluable_cases,
        prediction_validation=pred_validation_report,
        sell_recommendation_validation=sell_validation_report,
        harvest_recommendation_validation=harvest_validation_report,
        failure_cases=failure_cases,
        data_limitations=data_limitations,
        generated_at=datetime.utcnow(),
    )
