"""
Historical Validation Service.
Caches and serves the precomputed walk-forward validation report.
Ensures zero model training or expensive walk-forward calculations occur inside HTTP request lifecycles.
"""

from pathlib import Path
from typing import Optional

from app.ml.validation.historical_validator import run_walk_forward_validation
from app.schemas.validation import HistoricalValidationResponse

_CACHED_REPORT: Optional[HistoricalValidationResponse] = None


class ValidationService:
    """Manages retrieval of historical validation reports with in-memory caching."""

    def __init__(self, dataset_path: Optional[str | Path] = None):
        self.dataset_path = dataset_path

    def get_historical_validation_report(self) -> HistoricalValidationResponse:
        """
        Returns the precomputed historical walk-forward validation report.
        Reuses cached result to guarantee zero training or heavy walk-forward computation in the HTTP request.
        """
        global _CACHED_REPORT
        if _CACHED_REPORT is None:
            _CACHED_REPORT = run_walk_forward_validation(self.dataset_path)
        return _CACHED_REPORT

    @classmethod
    def warm_cache(cls, dataset_path: Optional[str | Path] = None) -> HistoricalValidationResponse:
        """Explicitly warms the cache ahead of time."""
        global _CACHED_REPORT
        _CACHED_REPORT = run_walk_forward_validation(dataset_path)
        return _CACHED_REPORT

    @classmethod
    def clear_cache(cls) -> None:
        """Clears the cached report (for testing or dataset updates)."""
        global _CACHED_REPORT
        _CACHED_REPORT = None
