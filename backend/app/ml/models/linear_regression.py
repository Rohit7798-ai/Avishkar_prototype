"""
Ordinary Least Squares / Linear Regression Baseline Model.
Pure Python standard library implementation with zero external dependencies.
Solves normal equations (X^T X + lambda I) beta = X^T y via Gaussian elimination.
"""

from datetime import datetime
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class LinearRegressionBaseline:
    """
    Multivariate linear regression baseline for time-series next-period price prediction.
    y_hat = beta_0 + beta_1 * X_1 + ... + beta_p * X_p
    """

    def __init__(
        self,
        feature_names: Optional[List[str]] = None,
        ridge_penalty: float = 1e-4,
    ):
        self.feature_names = feature_names or ["current_modal_price", "price_spread", "arrivals_tonnes"]
        self.ridge_penalty = ridge_penalty
        self.intercept: float = 0.0
        self.coefficients: Dict[str, float] = {}
        self.is_fitted: bool = False
        self.trained_at: Optional[str] = None
        self.training_records_count: int = 0

    @property
    def model_name(self) -> str:
        return "linear_regression_baseline"

    @property
    def model_version(self) -> str:
        return "1.0.0"

    def fit(self, samples: List[Dict[str, Any]]) -> "LinearRegressionBaseline":
        """
        Fits linear regression coefficients on the provided training samples.
        """
        if not samples or len(samples) < len(self.feature_names) + 1:
            raise ValueError(
                f"Insufficient training samples. Need at least {len(self.feature_names) + 1} records, "
                f"received {len(samples) if samples else 0}."
            )

        # Build design matrix X (with bias column 1.0) and target vector y
        # X matrix dimensions: N x (P + 1)
        p = len(self.feature_names)
        m = p + 1  # includes bias term

        # Compute X^T X (m x m) and X^T y (m)
        xtx = [[0.0] * m for _ in range(m)]
        xty = [0.0] * m

        for s in samples:
            # Row vector: [1.0, f1, f2, ...]
            row = [1.0] + [float(s[f]) for f in self.feature_names]
            y_val = float(s["target_next_modal_price"])

            for r in range(m):
                xty[r] += row[r] * y_val
                for c in range(m):
                    xtx[r][c] += row[r] * row[c]

        # Add ridge penalty to diagonal (excluding intercept at index 0) for numerical stability
        for i in range(1, m):
            xtx[i][i] += self.ridge_penalty

        # Solve xtx * beta = xty via Gaussian elimination with partial pivoting
        beta = self._solve_linear_system(xtx, xty)

        self.intercept = round(beta[0], 4)
        self.coefficients = {
            feat: round(beta[i + 1], 4) for i, feat in enumerate(self.feature_names)
        }
        self.is_fitted = True
        self.trained_at = datetime.utcnow().isoformat()
        self.training_records_count = len(samples)

        return self

    @staticmethod
    def _solve_linear_system(A: List[List[float]], b: List[float]) -> List[float]:
        """Solves A x = b using Gaussian elimination with partial pivoting."""
        n = len(b)
        # Deep copy to prevent modifying inputs
        M = [row[:] for row in A]
        v = b[:]

        for k in range(n):
            # Partial pivoting: locate row with maximum pivot in column k
            pivot_row = k
            max_val = abs(M[k][k])
            for i in range(k + 1, n):
                if abs(M[i][k]) > max_val:
                    max_val = abs(M[i][k])
                    pivot_row = i

            if max_val < 1e-12:
                raise ValueError("Singular matrix encountered during linear regression fitting.")

            # Swap rows
            if pivot_row != k:
                M[k], M[pivot_row] = M[pivot_row], M[k]
                v[k], v[pivot_row] = v[pivot_row], v[k]

            # Forward elimination
            for i in range(k + 1, n):
                factor = M[i][k] / M[k][k]
                for j in range(k, n):
                    M[i][j] -= factor * M[k][j]
                v[i] -= factor * v[k]

        # Back substitution
        x = [0.0] * n
        for i in range(n - 1, -1, -1):
            sub_sum = sum(M[i][j] * x[j] for j in range(i + 1, n))
            x[i] = (v[i] - sub_sum) / M[i][i]

        return x

    def predict_one(self, **features) -> float:
        """Computes prediction for a single feature dictionary."""
        if not self.is_fitted:
            raise RuntimeError("Model has not been fitted yet.")

        pred = self.intercept
        for feat in self.feature_names:
            if feat not in features:
                raise ValueError(f"Missing required feature '{feat}' for prediction.")
            val = float(features[feat])
            pred += self.coefficients[feat] * val

        return round(max(0.0, pred), 2)

    def predict(self, samples: List[Dict[str, Any]]) -> List[float]:
        """Computes predictions for a batch of samples."""
        if not self.is_fitted:
            raise RuntimeError("Model has not been fitted yet.")

        return [self.predict_one(**s) for s in samples]

    def save(self, file_path: str | Path) -> None:
        """Serializes model parameters and metadata to a JSON file."""
        if not self.is_fitted:
            raise RuntimeError("Cannot save an unfitted model.")

        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "model_name": self.model_name,
            "model_version": self.model_version,
            "feature_names": self.feature_names,
            "ridge_penalty": self.ridge_penalty,
            "intercept": self.intercept,
            "coefficients": self.coefficients,
            "trained_at": self.trained_at,
            "training_records_count": self.training_records_count,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    @classmethod
    def load(cls, file_path: str | Path) -> "LinearRegressionBaseline":
        """Loads and returns a model instance from a serialized JSON file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Model file not found at: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        instance = cls(
            feature_names=data.get("feature_names"),
            ridge_penalty=float(data.get("ridge_penalty", 1e-4)),
        )
        instance.intercept = float(data["intercept"])
        instance.coefficients = {k: float(v) for k, v in data["coefficients"].items()}
        instance.is_fitted = True
        instance.trained_at = data.get("trained_at")
        instance.training_records_count = int(data.get("training_records_count", 0))

        return instance
