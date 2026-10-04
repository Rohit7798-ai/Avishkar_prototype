"""
Abstract interface definition for Market / Mandi Rate Providers.
Decoupled entirely from database, ORM, and transport layers.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from app.ingestion.common.types import NormalizedMarketData


class MarketProvider(ABC):
    """
    Contract that every external market/mandi rate provider adapter must fulfill.

    Guarantees:
      - Communicates only with the external market data provider (e.g. Agmarknet, eNAM).
      - Returns strictly validated NormalizedMarketData objects.
      - Never touches SQLAlchemy models, database sessions, or web route logic.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique identifier or moniker for the market data provider."""
        pass

    @abstractmethod
    def fetch_market_observations(
        self,
        crop_name: str,
        market_name: Optional[str] = None,
    ) -> List[NormalizedMarketData]:
        """
        Fetches current or recent mandi trade observations for a crop across specified or all mandis.

        Args:
            crop_name: Target commodity (e.g. "Onion").
            market_name: Optional APMC market yard filter (e.g. "Lasalgaon APMC").

        Returns:
            List[NormalizedMarketData]: Validated market price observations.

        Raises:
            ValueError: If crop_name is invalid or missing.
            RuntimeError: If external communication fails.
        """
        pass
