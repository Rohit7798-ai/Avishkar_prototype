from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Schema for service health check response."""
    status: str = Field(default="ok", description="Current health status of the service")
    service: str = Field(default="farmer-decision-system", description="Service identifier name")

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "ok",
                "service": "farmer-decision-system"
            }
        }
    }


class ReadinessResponse(BaseModel):
    """Schema for service readiness check response."""
    status: str = Field(..., description="Readiness status ('ready' or 'unavailable')")
    database: str = Field(..., description="Database connectivity status ('connected' or 'disconnected')")
    environment: str = Field(..., description="Active runtime environment")

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "ready",
                "database": "connected",
                "environment": "development"
            }
        }
    }
