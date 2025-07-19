from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd
import structlog
from pydantic import BaseModel, Field, field_validator

from src.core.exceptions import ValidationError

logger = structlog.get_logger()


class ShipUsageDataValidator(BaseModel):
    """Validation schema for ship usage data."""

    total_operating_hours: float = Field(ge=0, le=100000, default=8000)
    recent_operating_hours: float = Field(ge=0, le=10000, default=200)
    average_speed: float = Field(ge=0, le=50, default=18)
    engine_load_avg: float = Field(ge=0, le=1, default=0.7)
    fuel_efficiency: float = Field(ge=0, le=1, default=0.8)
    weather_severity_avg: float = Field(ge=0, le=1, default=0.5)
    storm_exposure_hours: float = Field(ge=0, le=10000, default=100)
    rough_sea_percentage: float = Field(ge=0, le=1, default=0.3)
    ship_age_years: float = Field(ge=0, le=50, default=10)
    condition_score: float = Field(ge=0, le=1, default=0.8)


class MaintenanceHistoryValidator(BaseModel):
    """Validation schema for maintenance history records."""

    date: datetime
    event_type: str = Field(pattern=r"^(routine|preventive|emergency|overhaul)$")
    component: str = Field(min_length=1, max_length=200)
    cost: float = Field(ge=0, default=0)
    urgency: Optional[float] = Field(ge=0, le=1, default=None)

    @field_validator("date")
    @classmethod
    def validate_date(cls, v):
        if v > datetime.now():
            raise ValueError("Maintenance date cannot be in the future")
        if v < datetime.now() - timedelta(days=3650):  # 10 years ago
            raise ValueError("Maintenance date too old (>10 years)")
        return v


class DataValidationService:
    """
    Centralized data validation service for ML models.
    Applies DRY principles and ensures consistent validation across the application.
    """

    def __init__(self):
        self.logger = structlog.get_logger(__name__)

    def validate_ship_usage_data(self, usage_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and clean ship usage data.

        Args:
            usage_data: Raw ship usage data dictionary

        Returns:
            Validated and cleaned usage data

        Raises:
            ValidationError: If validation fails
        """
        try:
            # Apply validation schema
            validated_data = ShipUsageDataValidator(**usage_data)

            # Additional business logic validation
            if (
                validated_data.recent_operating_hours
                > validated_data.total_operating_hours
            ):
                self.logger.warning(
                    "Recent operating hours exceed total, adjusting",
                    recent=validated_data.recent_operating_hours,
                    total=validated_data.total_operating_hours,
                )
                validated_data.recent_operating_hours = min(
                    validated_data.recent_operating_hours,
                    validated_data.total_operating_hours,
                )

            # Check for anomalies
            if validated_data.fuel_efficiency < 0.3:
                self.logger.warning(
                    "Very low fuel efficiency detected",
                    efficiency=validated_data.fuel_efficiency,
                )

            if validated_data.condition_score < 0.5:
                self.logger.warning(
                    "Poor ship condition detected",
                    condition=validated_data.condition_score,
                )

            return validated_data.model_dump()

        except Exception as e:
            self.logger.error("Ship usage data validation failed", error=str(e))
            raise ValidationError(f"Invalid ship usage data: {str(e)}")

    def validate_maintenance_history(
        self, maintenance_history: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Validate and clean maintenance history data.

        Args:
            maintenance_history: List of maintenance event dictionaries

        Returns:
            Validated and cleaned maintenance history

        Raises:
            ValidationError: If validation fails
        """
        try:
            validated_history = []

            for i, event in enumerate(maintenance_history):
                try:
                    # Apply validation schema
                    validated_event = MaintenanceHistoryValidator(**event)
                    validated_history.append(validated_event.model_dump())

                except Exception as e:
                    self.logger.warning(
                        "Skipping invalid maintenance event",
                        event_index=i,
                        error=str(e),
                    )
                    continue

            # Sort by date
            validated_history.sort(key=lambda x: x["date"])

            # Check for duplicates
            unique_events = []
            seen_events = set()

            for event in validated_history:
                event_key = (event["date"], event["component"], event["event_type"])
                if event_key not in seen_events:
                    unique_events.append(event)
                    seen_events.add(event_key)
                else:
                    self.logger.warning(
                        "Duplicate maintenance event removed", event=event_key
                    )

            self.logger.info(
                "Maintenance history validated",
                original_count=len(maintenance_history),
                validated_count=len(unique_events),
            )

            return unique_events

        except Exception as e:
            self.logger.error("Maintenance history validation failed", error=str(e))
            raise ValidationError(f"Invalid maintenance history: {str(e)}")

    def validate_feature_data(
        self, features: Dict[str, Any], required_features: List[str]
    ) -> Dict[str, Any]:
        """
        Validate feature data for ML models.

        Args:
            features: Feature dictionary
            required_features: List of required feature names

        Returns:
            Validated feature dictionary

        Raises:
            ValidationError: If validation fails
        """
        try:
            validated_features = {}

            # Check for required features
            missing_features = [f for f in required_features if f not in features]
            if missing_features:
                raise ValidationError(f"Missing required features: {missing_features}")

            # Validate each feature
            for feature_name, value in features.items():
                if value is None:
                    self.logger.warning(
                        f"Null value for feature {feature_name}, setting to 0"
                    )
                    validated_features[feature_name] = 0.0
                elif isinstance(value, (int, float)):
                    if np.isnan(value) or np.isinf(value):
                        self.logger.warning(
                            f"Invalid numeric value for feature {feature_name}, setting to 0"
                        )
                        validated_features[feature_name] = 0.0
                    else:
                        validated_features[feature_name] = float(value)
                else:
                    try:
                        validated_features[feature_name] = float(value)
                    except (ValueError, TypeError):
                        self.logger.warning(
                            f"Cannot convert feature {feature_name} to float, setting to 0"
                        )
                        validated_features[feature_name] = 0.0

            return validated_features

        except Exception as e:
            self.logger.error("Feature validation failed", error=str(e))
            raise ValidationError(f"Invalid feature data: {str(e)}")

    def validate_model_input(
        self, data: Union[Dict, pd.DataFrame], expected_columns: List[str]
    ) -> pd.DataFrame:
        """
        Validate and prepare model input data.

        Args:
            data: Input data as dictionary or DataFrame
            expected_columns: Expected column names in order

        Returns:
            Validated DataFrame with correct column order

        Raises:
            ValidationError: If validation fails
        """
        try:
            # Convert to DataFrame if needed
            if isinstance(data, dict):
                df = pd.DataFrame([data])
            else:
                df = data.copy()

            # Ensure all expected columns exist
            for col in expected_columns:
                if col not in df.columns:
                    self.logger.warning(
                        f"Missing column {col}, adding with default value 0"
                    )
                    df[col] = 0.0

            # Reorder columns to match expected order
            df = df.reindex(columns=expected_columns, fill_value=0.0)

            # Validate data types
            for col in df.columns:
                if not pd.api.types.is_numeric_dtype(df[col]):
                    try:
                        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
                    except Exception:
                        self.logger.warning(
                            f"Cannot convert column {col} to numeric, filling with 0"
                        )
                        df[col] = 0.0

            # Check for infinite or NaN values
            df = df.replace([np.inf, -np.inf], 0.0).fillna(0.0)

            return df

        except Exception as e:
            self.logger.error("Model input validation failed", error=str(e))
            raise ValidationError(f"Invalid model input: {str(e)}")


# Global instance
data_validator = DataValidationService()
