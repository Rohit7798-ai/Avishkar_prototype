"""
Naive Persistence Baseline Model for Market Price.
Standard benchmark: predicts that next-day price will simply equal current-day price.
"""

from typing import Any, Dict, List


class NaivePersistenceModel:
    """
    Naive baseline that outputs today's modal price as tomorrow's predicted modal price.
    y_hat_{t+1} = y_t
    """

    @property
    def model_name(self) -> str:
        return "naive_persistence_baseline"

    @property
    def model_version(self) -> str:
        return "1.0.0"

    def fit(self, samples: List[Dict[str, Any]]) -> "NaivePersistenceModel":
        """Naive model requires no parameter learning."""
        return self

    def predict_one(self, current_modal_price: float, **kwargs) -> float:
        """Predicts tomorrow's price directly from current price."""
        if current_modal_price <= 0:
            raise ValueError("current_modal_price must be strictly positive.")
        return float(current_modal_price)

    def predict(self, samples: List[Dict[str, Any]]) -> List[float]:
        """Generates predictions across a list of sample dictionaries."""
        return [float(s["current_modal_price"]) for s in samples]
