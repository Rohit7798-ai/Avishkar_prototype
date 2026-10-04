"""
Evaluation metrics for market price regression models.
Computes MAE, RMSE, R2, MAPE, and benchmarks against naive persistence.
"""

import math
from typing import Any, Dict, List

from app.ml.models.baseline import NaivePersistenceModel


def calculate_regression_metrics(y_true: List[float], y_pred: List[float]) -> Dict[str, float]:
    """
    Computes standard regression evaluation metrics.

    Args:
        y_true: Ground truth target values.
        y_pred: Predicted values.

    Returns:
        Dict with mae, rmse, r2, mape.
    """
    if not y_true or not y_pred:
        raise ValueError("y_true and y_pred must be non-empty.")
    if len(y_true) != len(y_pred):
        raise ValueError(f"Length mismatch: y_true ({len(y_true)}) vs y_pred ({len(y_pred)}).")

    n = len(y_true)
    abs_errors = [abs(t - p) for t, p in zip(y_true, y_pred)]
    sq_errors = [(t - p) ** 2 for t, p in zip(y_true, y_pred)]

    mae = sum(abs_errors) / n
    mse = sum(sq_errors) / n
    rmse = math.sqrt(mse)

    # R2 computation
    mean_y = sum(y_true) / n
    ss_tot = sum((t - mean_y) ** 2 for t in y_true)
    ss_res = sum(sq_errors)

    if ss_tot < 1e-12:
        r2 = 1.0 if ss_res < 1e-12 else 0.0
    else:
        r2 = 1.0 - (ss_res / ss_tot)

    # MAPE
    pct_errors = [abs(t - p) / t for t, p in zip(y_true, y_pred) if t > 0]
    mape = (sum(pct_errors) / len(pct_errors) * 100.0) if pct_errors else 0.0

    return {
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "r2": round(r2, 4),
        "mape_percent": round(mape, 2),
    }


def evaluate_pipeline(
    train_samples: List[Dict[str, Any]],
    val_samples: List[Dict[str, Any]],
    model: Any,
) -> Dict[str, Any]:
    """
    Evaluates a trained model against the validation set and compares with naive baseline.

    Args:
        train_samples: Training records.
        val_samples: Validation records.
        model: Trained model (e.g. LinearRegressionBaseline).

    Returns:
        Structured evaluation dictionary containing dates, metrics, and comparisons.
    """
    if not val_samples:
        raise ValueError("Validation samples cannot be empty for evaluation.")

    val_y_true = [float(s["target_next_modal_price"]) for s in val_samples]

    # Model predictions
    val_y_pred = model.predict(val_samples)
    model_metrics = calculate_regression_metrics(val_y_true, val_y_pred)

    # Naive baseline predictions
    naive_model = NaivePersistenceModel()
    naive_y_pred = naive_model.predict(val_samples)
    naive_metrics = calculate_regression_metrics(val_y_true, naive_y_pred)

    # Training period
    train_dates = [s["date"] for s in train_samples] if train_samples else []
    val_dates = [s["date"] for s in val_samples]

    # Relative improvement
    if naive_metrics["mae"] > 0:
        mae_improvement_pct = round(
            ((naive_metrics["mae"] - model_metrics["mae"]) / naive_metrics["mae"]) * 100.0,
            2,
        )
    else:
        mae_improvement_pct = 0.0

    return {
        "model_name": getattr(model, "model_name", "unknown_model"),
        "model_version": getattr(model, "model_version", "1.0.0"),
        "training_period": {
            "start_date": min(train_dates).isoformat() if train_dates else None,
            "end_date": max(train_dates).isoformat() if train_dates else None,
            "record_count": len(train_samples),
        },
        "validation_period": {
            "start_date": min(val_dates).isoformat(),
            "end_date": max(val_dates).isoformat(),
            "record_count": len(val_samples),
        },
        "features_used": getattr(model, "feature_names", []),
        "model_performance": model_metrics,
        "naive_baseline_performance": naive_metrics,
        "mae_improvement_percent": mae_improvement_pct,
    }
