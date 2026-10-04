"""
Sample reference market provider adapter demonstrating external payload transformation.
Contains zero database logic, zero SQLAlchemy imports, and zero FastAPI logic.
"""

from datetime import date
from typing import Any, Dict, List, Optional

from app.ingestion.common.types import NormalizedMarketData
from app.ingestion.market.base import MarketProvider


class SampleMarketAdapter(MarketProvider):
    """
    Reference adapter illustrating how raw external provider payloads
    (e.g., from an Agmarknet or eNAM API record) are parsed, mapped,
    and transformed into NormalizedMarketData.
    """

    def __init__(self, provider_name: str = "sample_mandi_source"):
        self._provider_name = provider_name

    @property
    def provider_name(self) -> str:
        return self._provider_name

    def transform_raw_record(self, raw_record: Dict[str, Any]) -> NormalizedMarketData:
        """
        Pure adapter transformation logic: converts foreign dictionary keys into NormalizedMarketData.

        Example raw format:
          {
             "Commodity": "Onion",
             "Market": "Lasalgaon APMC",
             "Arrival_Date": "2026-10-02",
             "Modal_Price": 1950.0,
             "Price_Unit": "Rs/Quintal"
          }
        """
        obs_date = raw_record.get("Arrival_Date") or raw_record.get("observed_date") or date.today()
        if isinstance(obs_date, str):
            obs_date = date.fromisoformat(obs_date)

        return NormalizedMarketData(
            crop_name=str(raw_record.get("Commodity", raw_record.get("crop_name", ""))),
            market_name=str(raw_record.get("Market", raw_record.get("market_name", ""))),
            observed_date=obs_date,
            price=float(raw_record.get("Modal_Price", raw_record.get("price", 0.0))),
            unit=str(raw_record.get("Price_Unit", raw_record.get("unit", "Rs/Quintal"))),
        )

    def fetch_market_observations(
        self,
        crop_name: str,
        market_name: Optional[str] = None,
    ) -> List[NormalizedMarketData]:
        # For Milestone 7 (no external network calls permitted), demonstrates contract compliance.
        synthetic_raw = {
            "Commodity": crop_name,
            "Market": market_name or "Lasalgaon APMC",
            "Arrival_Date": date.today().isoformat(),
            "Modal_Price": 1850.0,
            "Price_Unit": "Rs/Quintal",
        }
        return [self.transform_raw_record(synthetic_raw)]
