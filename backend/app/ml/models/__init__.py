"""
ML Models Package.
"""

from app.ml.models.baseline import NaivePersistenceModel
from app.ml.models.linear_regression import LinearRegressionBaseline

__all__ = [
    "NaivePersistenceModel",
    "LinearRegressionBaseline",
]
