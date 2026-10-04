"""
Orchestration service for external market/mandi rate observation ingestion.
Connects MarketProvider Adapter -> Normalized Data -> Validation -> MarketObservationService -> SQLite.
Preserves architectural purity: No database code inside adapters.
"""

from datetime import date
from typing import Any, Dict, Optional, Set, Tuple
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleViolationException
from app.ingestion.bridge import ingest_market_observation
from app.ingestion.market.adapters.ogd_mandi_adapter import OgdMandiAdapter
from app.ingestion.market.base import MarketProvider
from app.repositories.market_observation_repository import MarketObservationRepository
from app.services.market_observation_service import MarketObservationService


class MarketIngestionService:
    """Orchestrates manual synchronization of mandi price observations from external providers."""

    def __init__(
        self,
        db: Session,
        market_provider: Optional[MarketProvider] = None,
    ):
        self.db = db
        self.observation_repo = MarketObservationRepository(db)
        self.observation_service = MarketObservationService(db)
        self.market_provider = market_provider or OgdMandiAdapter()

    def sync_market_data(
        self,
        crop_name: Optional[str] = "Onion",
        market_name: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Manually synchronizes market rate observations for a commodity.

        Args:
            crop_name: Target commodity name (default "Onion").
            market_name: Optional specific APMC market yard filter.
            limit: Maximum records to request.

        Returns:
            Dict containing provider, records_received, records_accepted, records_rejected.
        """
        target_crop = (crop_name or "Onion").strip()
        if not target_crop:
            raise BusinessRuleViolationException("Target crop name cannot be empty.")

        # Query provider adapter
        try:
            records = self.market_provider.fetch_market_observations(
                crop_name=target_crop,
                market_name=market_name,
                limit=limit,
            )
        except Exception as exc:
            raise BusinessRuleViolationException(f"Market provider sync failed: {exc}") from exc

        records_received = len(records)
        records_accepted = 0
        records_rejected = 0
        seen_keys: Set[Tuple[str, str, date]] = set()

        for record in records:
            key = (record.crop_name.lower(), record.market_name.lower(), record.observed_date)

            # Duplicate detection: in-batch duplicate check
            if key in seen_keys:
                records_rejected += 1
                continue

            # Duplicate detection: database-level duplicate check
            existing = self.observation_repo.find_by_crop_market_date(
                crop_name=record.crop_name,
                market_name=record.market_name,
                observed_date=record.observed_date,
            )
            if existing:
                records_rejected += 1
                continue

            try:
                # Ingest through existing observation service and validation layer
                ingest_market_observation(
                    data=record,
                    service=self.observation_service,
                )
                seen_keys.add(key)
                records_accepted += 1
            except Exception:
                records_rejected += 1

        return {
            "provider": self.market_provider.provider_name,
            "records_received": records_received,
            "records_accepted": records_accepted,
            "records_rejected": records_rejected,
        }
