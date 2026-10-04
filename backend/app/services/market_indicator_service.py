"""
Mandi Market Indicator Calculation Service.
Derives deterministic market price indicators exclusively from recorded market observations.
Does NOT predict future prices or produce speculative sell recommendations.
"""

from typing import Optional
from sqlalchemy.orm import Session

from app.repositories.market_observation_repository import MarketObservationRepository
from app.schemas.indicators import MarketIndicatorsResponse


class MarketIndicatorService:
    """Calculates deterministic mandi market price indicators."""

    def __init__(self, db: Session):
        self.obs_repo = MarketObservationRepository(db)

    def get_market_indicators(
        self,
        crop_name: Optional[str] = None,
        market_name: Optional[str] = None,
    ) -> MarketIndicatorsResponse:
        """
        Calculates summary price metrics and momentum for a crop/market combination.
        Single observation behavior:
          - price_change = 0.0 (earliest == latest)
          - price_change_percentage = None (no prior comparative baseline exists)
        """
        # ponytail: Fetch all recorded market observations matching filter without truncation
        observations = self.obs_repo.get_all(crop_name=crop_name, market_name=market_name, limit=None)
        count = len(observations)

        if count == 0:
            return MarketIndicatorsResponse(
                crop_name=crop_name,
                market_name=market_name,
                latest_price=None,
                earliest_price=None,
                highest_price=None,
                lowest_price=None,
                average_price=None,
                observation_count=0,
                number_of_observations=0,
                latest_observation_date=None,
                price_change=None,
                price_change_percentage=None,
            )

        # Sort chronologically by observed_date asc, id asc
        sorted_obs = sorted(observations, key=lambda x: (x.observed_date, x.id))
        earliest = sorted_obs[0]
        latest = sorted_obs[-1]

        prices = [o.price for o in observations]
        highest_price = max(prices)
        lowest_price = min(prices)
        avg_price = round(sum(prices) / count, 2)

        # ponytail: Single observation vs multiple observations handling
        if count == 1:
            price_change = 0.0
            price_change_percentage = None
        else:
            price_change = round(latest.price - earliest.price, 2)
            if earliest.price > 0:
                price_change_percentage = round(((latest.price - earliest.price) / earliest.price) * 100, 2)
            else:
                price_change_percentage = None

        return MarketIndicatorsResponse(
            crop_name=crop_name,
            market_name=market_name,
            latest_price=latest.price,
            earliest_price=earliest.price,
            highest_price=highest_price,
            lowest_price=lowest_price,
            average_price=avg_price,
            observation_count=count,
            number_of_observations=count,
            latest_observation_date=latest.observed_date,
            price_change=price_change,
            price_change_percentage=price_change_percentage,
        )
