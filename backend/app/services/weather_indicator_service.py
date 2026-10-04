"""
Farm Weather Indicator Calculation Service.
Derives statistical weather indicators exclusively from recorded weather measurements.
Does NOT fabricate missing data or invoke external weather APIs.
"""

from sqlalchemy.orm import Session

from app.core.exceptions import EntityNotFoundException
from app.repositories.farm_repository import FarmRepository
from app.repositories.weather_observation_repository import WeatherObservationRepository
from app.schemas.indicators import WeatherIndicatorsResponse


class WeatherIndicatorService:
    """Calculates deterministic farm weather indicators."""

    def __init__(self, db: Session):
        self.farm_repo = FarmRepository(db)
        self.obs_repo = WeatherObservationRepository(db)

    def get_farm_weather_indicators(self, farm_id: int) -> WeatherIndicatorsResponse:
        """
        Calculates weather statistics based on empirical farm weather observations.
        Raises EntityNotFoundException if the farm does not exist.
        """
        farm = self.farm_repo.get_by_id(farm_id)
        if not farm:
            raise EntityNotFoundException("Farm", farm_id)

        # ponytail: Fetch all recorded weather observations for farm without pagination truncation
        observations = self.obs_repo.get_by_farm_id(farm_id, limit=None)
        count = len(observations)

        if count == 0:
            return WeatherIndicatorsResponse(
                farm_id=farm_id,
                latest_temperature=None,
                latest_humidity=None,
                latest_rainfall=None,
                latest_wind_speed=None,
                latest_observed_at=None,
                latest_observation_timestamp=None,
                observation_count=0,
                number_of_observations=0,
                average_temperature=None,
                total_rainfall=None,
                average_humidity=None,
                average_wind_speed=None,
            )

        # Observations from repository are ordered by observed_at desc, id desc
        latest = observations[0]
        avg_temp = round(sum(o.temperature for o in observations) / count, 2)
        total_rain = round(sum(o.rainfall for o in observations), 2)
        avg_humidity = round(sum(o.humidity for o in observations) / count, 2)
        avg_wind = round(sum(o.wind_speed for o in observations) / count, 2)

        return WeatherIndicatorsResponse(
            farm_id=farm_id,
            latest_temperature=latest.temperature,
            latest_humidity=latest.humidity,
            latest_rainfall=latest.rainfall,
            latest_wind_speed=latest.wind_speed,
            latest_observed_at=latest.observed_at,
            latest_observation_timestamp=latest.observed_at,
            observation_count=count,
            number_of_observations=count,
            average_temperature=avg_temp,
            total_rainfall=total_rain,
            average_humidity=avg_humidity,
            average_wind_speed=avg_wind,
        )
