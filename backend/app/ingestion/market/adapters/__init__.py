"""
Market provider adapters package.
"""

from app.ingestion.market.adapters.sample_market_adapter import SampleMarketAdapter
from app.ingestion.market.adapters.ogd_mandi_adapter import OgdMandiAdapter

__all__ = [
    "SampleMarketAdapter",
    "OgdMandiAdapter",
]
