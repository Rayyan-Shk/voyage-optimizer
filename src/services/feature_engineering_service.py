from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import structlog

from src.core.exceptions import FeatureEngineeringError
from src.services.data_validation_service import data_validator

logger = structlog.get_logger()


class FeatureEngineeringService:
    """
    Centralized feature engineering service for ML models.
    Applies DRY principles and ensures consistent feature extraction across the application.
    """

    def __init__(self):
        self.logger = structlog.get_logger(__name__)
        from src.services.model_config_service import model_config

        self.component_categories = model_config.get_component_categories()

    def extract_maintenance_features(
        self,
        ship_id: str,
        current_date: datetime,
        usage_data: Dict[str, Any],
        historical_maintenance: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Extract features for maintenance forecasting.

        Args:
            ship_id: Ship identifier
            current_date: Current date for feature extraction
            usage_data: Ship usage data
            historical_maintenance: Historical maintenance records

        Returns:
            Dictionary of extracted features

        Raises:
            FeatureEngineeringError: If feature extraction fails
        """
        try:
            # Validate input data
            validated_usage = data_validator.validate_ship_usage_data(usage_data)
            validated_maintenance = data_validator.validate_maintenance_history(
                historical_maintenance
            )

            features = {}

            # Ship usage features
            features.update(self._extract_usage_features(validated_usage))

            # Weather exposure features
            features.update(self._extract_weather_features(validated_usage))

            # Maintenance history features
            features.update(
                self._extract_maintenance_history_features(
                    validated_maintenance, current_date
                )
            )

            # Component-specific features
            features.update(
                self._extract_component_features(validated_maintenance, current_date)
            )

            # Temporal features
            features.update(self._extract_temporal_features(current_date))

            # Ship condition features
            features.update(self._extract_condition_features(validated_usage))

            self.logger.info(
                "Maintenance features extracted",
                ship_id=ship_id,
                feature_count=len(features),
            )

            return features

        except Exception as e:
            self.logger.error("Maintenance feature extraction failed", error=str(e))
            raise FeatureEngineeringError(
                f"Failed to extract maintenance features: {str(e)}"
            )

    def extract_fuel_features(
        self,
        ship_specs: Dict[str, Any],
        route_data: Dict[str, Any],
        weather_conditions: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Extract features for fuel consumption prediction.

        Args:
            ship_specs: Ship specifications
            route_data: Route information
            weather_conditions: Weather conditions (optional)

        Returns:
            Dictionary of extracted features

        Raises:
            FeatureEngineeringError: If feature extraction fails
        """
        try:
            features = {}

            # Ship specification features
            features.update(self._extract_ship_spec_features(ship_specs))

            # Route characteristics features
            features.update(self._extract_route_features(route_data))

            # Cargo features
            features.update(self._extract_cargo_features(ship_specs, route_data))

            # Weather features
            features.update(
                self._extract_weather_condition_features(weather_conditions)
            )

            self.logger.info("Fuel features extracted", feature_count=len(features))

            return features

        except Exception as e:
            self.logger.error("Fuel feature extraction failed", error=str(e))
            raise FeatureEngineeringError(f"Failed to extract fuel features: {str(e)}")

    def _extract_usage_features(self, usage_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract ship usage features."""
        return {
            "total_operating_hours": usage_data.get("total_operating_hours", 8000),
            "recent_operating_hours": usage_data.get("recent_operating_hours", 200),
            "average_speed": usage_data.get("average_speed", 18),
            "engine_load_avg": usage_data.get("engine_load_avg", 0.7),
            "fuel_efficiency": usage_data.get("fuel_efficiency", 0.8),
        }

    def _extract_weather_features(self, usage_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract weather exposure features."""
        return {
            "weather_severity_avg": usage_data.get("weather_severity_avg", 0.5),
            "storm_exposure_hours": usage_data.get("storm_exposure_hours", 100),
            "rough_sea_percentage": usage_data.get("rough_sea_percentage", 0.3),
        }

    def _extract_maintenance_history_features(
        self, maintenance_history: List[Dict[str, Any]], current_date: datetime
    ) -> Dict[str, Any]:
        """Extract maintenance history features."""
        return {
            "days_since_last_maintenance": self._calculate_days_since_last_maintenance(
                maintenance_history, current_date
            ),
            "maintenance_frequency": self._calculate_maintenance_frequency(
                maintenance_history
            ),
            "average_maintenance_cost": self._calculate_average_maintenance_cost(
                maintenance_history
            ),
            "emergency_maintenance_ratio": self._calculate_emergency_ratio(
                maintenance_history
            ),
        }

    def _extract_component_features(
        self, maintenance_history: List[Dict[str, Any]], current_date: datetime
    ) -> Dict[str, Any]:
        """Extract component-specific features."""
        features = {}

        for component_category in self.component_categories:
            features[f"{component_category}_last_maintenance"] = (
                self._get_component_last_maintenance(
                    maintenance_history, component_category, current_date
                )
            )
            features[f"{component_category}_failure_history"] = (
                self._get_component_failure_history(
                    maintenance_history, component_category
                )
            )

        return features

    def _extract_temporal_features(self, current_date: datetime) -> Dict[str, Any]:
        """Extract temporal features."""
        return {
            "month": current_date.month,
            "quarter": (current_date.month - 1) // 3 + 1,
            "is_winter": 1 if current_date.month in [12, 1, 2] else 0,
        }

    def _extract_condition_features(self, usage_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract ship condition features."""
        return {
            "ship_age_years": usage_data.get("ship_age_years", 10),
            "condition_score": usage_data.get("condition_score", 0.8),
        }

    def _extract_ship_spec_features(self, ship_specs: Dict[str, Any]) -> Dict[str, Any]:
        """Extract ship specification features."""
        return {
            "displacement": ship_specs.get("displacement", 50000),
            "engine_power": ship_specs.get("engine_power", 15000),
            "max_speed": ship_specs.get("max_speed", 22),
            "cargo_capacity": ship_specs.get("cargo_capacity", 30000),
            "ship_age": ship_specs.get("age", 10),
        }

    def _extract_route_features(self, route_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract route characteristics features."""
        return {
            "distance": route_data.get("total_distance", 3000),
            "average_speed": route_data.get("average_speed", 18),
            "port_calls": len(route_data.get("waypoints", [])),
            "route_complexity": self._calculate_route_complexity(route_data),
        }

    def _extract_cargo_features(
        self, ship_specs: Dict[str, Any], route_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract cargo-related features."""
        cargo_weight = route_data.get("cargo_weight", 25000)
        cargo_capacity = ship_specs.get("cargo_capacity", 30000)

        return {
            "cargo_weight": cargo_weight,
            "cargo_density": cargo_weight / cargo_capacity if cargo_capacity > 0 else 0,
        }

    def _extract_weather_condition_features(
        self, weather_conditions: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract weather condition features."""
        if weather_conditions:
            return {
                "avg_wind_speed": weather_conditions.get("wind_speed", 12),
                "avg_wave_height": weather_conditions.get("wave_height", 2.5),
                "avg_temperature": weather_conditions.get("temperature", 20),
                "weather_severity": self._calculate_weather_severity(
                    weather_conditions
                ),
                "headwind_percentage": weather_conditions.get(
                    "headwind_percentage", 0.5
                ),
            }
        else:
            # Default weather conditions
            return {
                "avg_wind_speed": 12,
                "avg_wave_height": 2.5,
                "avg_temperature": 20,
                "weather_severity": 0.5,
                "headwind_percentage": 0.5,
            }

    def _calculate_days_since_last_maintenance(
        self, maintenance_history: List[Dict[str, Any]], current_date: datetime
    ) -> int:
        """Calculate days since last maintenance."""
        if not maintenance_history:
            return 365  # Default if no history

        last_maintenance = max(
            maintenance_history, key=lambda x: x.get("date", datetime.min)
        )
        last_date = last_maintenance.get("date", current_date - timedelta(days=365))

        return (current_date - last_date).days

    def _calculate_maintenance_frequency(
        self, maintenance_history: List[Dict[str, Any]]
    ) -> float:
        """Calculate maintenance frequency (events per year)."""
        if len(maintenance_history) < 2:
            return 4.0  # Default frequency

        # Sort by date
        sorted_history = sorted(
            maintenance_history, key=lambda x: x.get("date", datetime.min)
        )

        # Calculate time span
        first_date = sorted_history[0].get("date", datetime.now())
        last_date = sorted_history[-1].get("date", datetime.now())
        time_span_years = max(1, (last_date - first_date).days / 365.25)

        return len(maintenance_history) / time_span_years

    def _calculate_average_maintenance_cost(
        self, maintenance_history: List[Dict[str, Any]]
    ) -> float:
        """Calculate average maintenance cost."""
        if not maintenance_history:
            return 10000.0  # Default cost

        costs = [event.get("cost", 0) for event in maintenance_history]
        return np.mean(costs) if costs else 10000.0

    def _calculate_emergency_ratio(
        self, maintenance_history: List[Dict[str, Any]]
    ) -> float:
        """Calculate ratio of emergency maintenance events."""
        if not maintenance_history:
            return 0.1  # Default ratio

        emergency_count = sum(
            1 for event in maintenance_history if event.get("event_type") == "emergency"
        )

        return emergency_count / len(maintenance_history)

    def _get_component_last_maintenance(
        self,
        maintenance_history: List[Dict[str, Any]],
        component_category: str,
        current_date: datetime,
    ) -> int:
        """Get days since last maintenance for specific component category."""
        component_events = [
            event
            for event in maintenance_history
            if component_category.lower() in event.get("component", "").lower()
        ]

        if not component_events:
            return 365  # Default if no component history

        last_event = max(component_events, key=lambda x: x.get("date", datetime.min))
        last_date = last_event.get("date", current_date - timedelta(days=365))

        return (current_date - last_date).days

    def _get_component_failure_history(
        self, maintenance_history: List[Dict[str, Any]], component_category: str
    ) -> float:
        """Get failure history score for specific component category."""
        component_events = [
            event
            for event in maintenance_history
            if component_category.lower() in event.get("component", "").lower()
        ]

        if not component_events:
            return 0.1  # Default low failure score

        # Calculate failure score based on emergency events
        emergency_count = sum(
            1 for event in component_events if event.get("event_type") == "emergency"
        )

        failure_score = emergency_count / len(component_events)

        # Adjust based on recency
        for event in component_events:
            if event.get("event_type") == "emergency":
                days_ago = (datetime.now() - event.get("date", datetime.now())).days
                if days_ago < 180:  # Recent emergency
                    failure_score += 0.1

        return min(1.0, failure_score)

    def _calculate_route_complexity(self, route_data: Dict[str, Any]) -> float:
        """Calculate route complexity score."""
        waypoints = route_data.get("waypoints", [])
        if len(waypoints) < 2:
            return 0.5  # Default complexity

        # Simple complexity based on number of waypoints and distance
        base_complexity = min(1.0, len(waypoints) / 10)
        distance_factor = min(1.0, route_data.get("total_distance", 3000) / 10000)

        return (base_complexity + distance_factor) / 2

    def _calculate_weather_severity(self, weather_conditions: Dict[str, Any]) -> float:
        """Calculate weather severity score."""
        wind_speed = weather_conditions.get("wind_speed", 12)
        wave_height = weather_conditions.get("wave_height", 2.5)

        # Normalize to 0-1 scale
        wind_severity = min(1.0, wind_speed / 30)  # 30 m/s max
        wave_severity = min(1.0, wave_height / 10)  # 10 m max

        return (wind_severity + wave_severity) / 2


# Global instance
feature_engineer = FeatureEngineeringService()
