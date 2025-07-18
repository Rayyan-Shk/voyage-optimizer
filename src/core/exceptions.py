from typing import Any, Dict, Optional


class ShipPlanningException(Exception):
    """Base exception for ship planning system."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(ShipPlanningException):
    """Raised when input validation fails."""
    pass


class ModelError(ShipPlanningException):
    """Raised when ML model operations fail."""
    pass


class DatabaseError(ShipPlanningException):
    """Raised when database operations fail."""
    pass


class CacheError(ShipPlanningException):
    """Raised when cache operations fail."""
    pass


class ExternalAPIError(ShipPlanningException):
    """Raised when external API calls fail."""
    pass


class RouteOptimizationError(ModelError):
    """Raised when route optimization fails."""
    pass


class FuelPredictionError(ModelError):
    """Raised when fuel prediction fails."""
    pass


class MaintenanceForecastError(ModelError):
    """Raised when maintenance forecasting fails."""
    pass


class WeatherDataError(ExternalAPIError):
    """Raised when weather data retrieval fails."""
    pass


class InsufficientDataError(ShipPlanningException):
    """Raised when insufficient data for predictions."""
    pass


class ModelNotTrainedError(ModelError):
    """Raised when trying to use untrained model."""
    pass


class FeatureEngineeringError(ModelError):
    """Raised when feature engineering fails."""
    pass