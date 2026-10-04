"""
Centralized API router.
Mounts root operational endpoints (health) and versioned v1 CRUD routes.
"""

from fastapi import APIRouter
from app.api.endpoints import health, farmers, farms, crops, crop_observations, weather_observations, market_observations, indicators, decisions, sync, predictions, explanations, recommendations, validation, observation_reminders

api_router = APIRouter()

# Root operational endpoints: /api/health
api_router.include_router(health.router, tags=["Health"])

# Versioned API routes: /api/v1/...
v1_router = APIRouter(prefix="/v1")
v1_router.include_router(farmers.router)
v1_router.include_router(farms.router)
v1_router.include_router(crops.router)
v1_router.include_router(crop_observations.router)
v1_router.include_router(weather_observations.router)
v1_router.include_router(market_observations.router)
v1_router.include_router(indicators.router)
v1_router.include_router(decisions.router)
v1_router.include_router(sync.router)
v1_router.include_router(predictions.router)
v1_router.include_router(explanations.router)
v1_router.include_router(recommendations.router)
v1_router.include_router(validation.router)
v1_router.include_router(observation_reminders.router)

api_router.include_router(v1_router)
