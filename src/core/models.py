from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class VoyageStatus(str, Enum):
    """Voyage status enumeration."""

    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MaintenanceType(str, Enum):
    """Maintenance type enumeration."""

    ROUTINE = "routine"
    PREVENTIVE = "preventive"
    EMERGENCY = "emergency"
    OVERHAUL = "overhaul"


class Coordinates(BaseModel):
    """Geographic coordinates with validation."""

    latitude: float = Field(..., ge=-90, le=90, description="Latitude in degrees")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude in degrees")

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, v):
        if not -90 <= v <= 90:
            raise ValueError("Latitude must be between -90 and 90 degrees")
        return v

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, v):
        if not -180 <= v <= 180:
            raise ValueError("Longitude must be between -180 and 180 degrees")
        return v


class WeatherCondition(BaseModel):
    """Weather conditions for route planning."""

    temperature: float = Field(..., description="Temperature in Celsius")
    wind_speed: float = Field(..., ge=0, description="Wind speed in m/s")
    wind_direction: float = Field(
        ..., ge=0, lt=360, description="Wind direction in degrees"
    )
    wave_height: float = Field(..., ge=0, description="Wave height in meters")
    visibility: float = Field(..., ge=0, description="Visibility in kilometers")
    weather_type: str = Field(
        ..., description="Weather type (clear, cloudy, stormy, etc.)"
    )


class WeatherForecast(BaseModel):
    """Weather forecast for the voyage."""

    current_conditions: WeatherCondition
    forecast_data: List[WeatherCondition] = Field(default_factory=list)
    forecast_accuracy: float = Field(0.85, ge=0, le=1, description="Forecast accuracy")


class Waypoint(BaseModel):
    """Route waypoint with timing and conditions."""

    coordinates: Coordinates
    eta: datetime
    speed: float = Field(..., gt=0, description="Speed in knots")
    fuel_rate: float = Field(..., gt=0, description="Fuel consumption rate")
    weather_conditions: Optional[WeatherCondition] = None


class ShipSpecification(BaseModel):
    """Ship specifications for optimization."""

    ship_id: UUID
    name: str
    ship_type: str
    length: float = Field(..., gt=0, description="Ship length in meters")
    width: float = Field(..., gt=0, description="Ship width in meters")
    draft: float = Field(..., gt=0, description="Ship draft in meters")
    gross_tonnage: float = Field(..., gt=0, description="Gross tonnage")
    max_speed: float = Field(..., gt=0, description="Maximum speed in knots")
    fuel_capacity: float = Field(..., gt=0, description="Fuel capacity in tons")
    cargo_capacity: float = Field(..., gt=0, description="Cargo capacity in tons")

    @field_validator("max_speed")
    @classmethod
    def validate_max_speed(cls, v):
        if v > 50:  # Reasonable maximum speed for commercial vessels
            raise ValueError("Maximum speed seems unrealistic for commercial vessels")
        return v


class Route(BaseModel):
    """Optimized route with waypoints."""

    waypoints: List[Coordinates]
    total_distance: float = Field(
        ..., ge=0, description="Total distance in nautical miles"
    )
    estimated_duration: float = Field(
        ..., ge=0, description="Estimated duration in hours"
    )
    alternative_routes: List["Route"] = Field(default_factory=list)
    confidence_score: float = Field(
        ..., ge=0, le=1, description="Route confidence score"
    )


class RouteOptimization(BaseModel):
    """Route optimization result with detailed waypoints."""

    waypoints: List[Waypoint]
    total_distance: float = Field(
        ..., gt=0, description="Total distance in nautical miles"
    )
    estimated_duration: float = Field(..., gt=0, description="Duration in hours")
    confidence_score: float = Field(..., ge=0, le=1, description="Confidence score")
    optimization_factors: Dict[str, float] = Field(default_factory=dict)


class FuelPrediction(BaseModel):
    """Fuel consumption prediction."""

    estimated_consumption: float = Field(
        ..., ge=0, description="Estimated fuel consumption in tons"
    )
    confidence_interval: Dict[str, float] = Field(
        default_factory=lambda: {"lower": 0, "upper": 0}
    )
    factors: Dict[str, float] = Field(default_factory=dict)
    efficiency_score: float = Field(
        ..., ge=0, le=1, description="Fuel efficiency score"
    )


class MaintenanceRecommendation(BaseModel):
    """Maintenance recommendation."""

    component: str
    maintenance_type: MaintenanceType
    urgency_score: float = Field(..., ge=0, le=1, description="Urgency score (0-1)")
    estimated_cost: float = Field(..., ge=0, description="Estimated cost in USD")
    recommended_date: datetime
    description: str
    risk_level: str = Field(..., description="Risk level (low, medium, high, critical)")


class MaintenanceAlert(BaseModel):
    """Maintenance alert with predictions."""

    ship_id: UUID
    alerts: List[MaintenanceRecommendation]
    overall_risk_score: float = Field(..., ge=0, le=1, description="Overall risk score")
    next_critical_date: Optional[datetime] = None


class MaintenanceForecasting(BaseModel):
    """Maintenance forecasting result."""

    recommendations: List[MaintenanceRecommendation]
    confidence_score: float = Field(
        ..., ge=0, le=1, description="Forecasting confidence score"
    )
    next_critical_date: Optional[datetime] = None


class VoyagePlanRequest(BaseModel):
    """Request for voyage planning."""

    ship_id: UUID
    origin: Coordinates
    destination: Coordinates
    departure_time: datetime
    cargo_weight: float = Field(..., ge=0, description="Cargo weight in tons")
    weather_forecast: Optional[WeatherForecast] = None
    optimization_preferences: Dict[str, float] = Field(
        default_factory=lambda: {"time": 0.4, "fuel": 0.4, "safety": 0.2}
    )

    @field_validator("departure_time")
    @classmethod
    def validate_departure_time(cls, v):
        # For demo purposes, skip past date validation
        # In production, you would want proper validation
        return v

    @model_validator(mode="after")
    def validate_optimization_preferences(self):
        prefs = self.optimization_preferences
        if prefs and abs(sum(prefs.values()) - 1.0) > 0.01:
            raise ValueError("Optimization preferences must sum to 1.0")
        return self


class AlternativePlan(BaseModel):
    """Alternative voyage plan."""

    plan_id: str
    route: Route
    fuel_prediction: FuelPrediction
    estimated_arrival: datetime
    trade_offs: Dict[str, float] = Field(default_factory=dict)
    score: float = Field(..., ge=0, le=1, description="Overall plan score")


class VoyagePlanResponse(BaseModel):
    """Response for voyage planning."""

    voyage_id: UUID = Field(default_factory=uuid4)
    ship_id: UUID
    route: Route
    fuel_prediction: FuelPrediction
    maintenance_recommendations: List[MaintenanceRecommendation] = Field(
        default_factory=list
    )
    alternative_plans: List[AlternativePlan] = Field(default_factory=list)
    total_estimated_cost: float = Field(
        ..., ge=0, description="Total estimated cost in USD"
    )
    confidence_score: float = Field(
        ..., ge=0, le=1, description="Overall confidence score"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)


class VoyageHistory(BaseModel):
    """Historical voyage data."""

    voyage_id: UUID
    ship_id: UUID
    planned_route: Route
    actual_route: Optional[Route] = None
    planned_fuel: float
    actual_fuel: Optional[float] = None
    departure_time: datetime
    arrival_time: Optional[datetime] = None
    status: VoyageStatus
    performance_metrics: Dict[str, float] = Field(default_factory=dict)


class VoyageFeedback(BaseModel):
    """Voyage feedback for model improvement."""

    voyage_id: UUID
    ship_id: UUID
    actual_fuel_consumption: float = Field(
        ..., ge=0, description="Actual fuel consumption in tons"
    )
    actual_duration: float = Field(..., ge=0, description="Actual duration in hours")
    route_deviations: List[Coordinates] = Field(default_factory=list)
    weather_accuracy: float = Field(
        0.85, ge=0, le=1, description="Weather forecast accuracy"
    )
    maintenance_events: List[MaintenanceRecommendation] = Field(default_factory=list)
    overall_satisfaction: float = Field(
        ..., ge=1, le=5, description="Overall satisfaction (1-5)"
    )
    comments: Optional[str] = None

    @field_validator("actual_fuel_consumption")
    @classmethod
    def validate_fuel_consumption(cls, v):
        if v <= 0:
            raise ValueError("Fuel consumption must be positive")
        return v


class APIResponse(BaseModel):
    """Standard API response wrapper."""

    success: bool = True
    message: str = "Operation completed successfully"
    data: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Update forward references
Route.model_rebuild()
