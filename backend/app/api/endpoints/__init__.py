"""
API Endpoints Package.
"""

from app.api.endpoints import health, farmers, farms, crops, crop_observations, weather_observations, market_observations, indicators, decisions, sync, predictions, explanations, recommendations, validation, observation_reminders

__all__ = [
    "health",
    "farmers",
    "farms",
    "crops",
    "crop_observations",
    "weather_observations",
    "market_observations",
    "indicators",
    "decisions",
    "sync",
    "predictions",
    "explanations",
    "recommendations",
    "validation",
    "observation_reminders",
]
