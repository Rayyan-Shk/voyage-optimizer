from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestClassifier
from sklearn.metrics import classification_report, mean_absolute_error
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from src.core.exceptions import InsufficientDataError, MaintenanceForecastError
from src.core.models import (
    MaintenanceForecasting,
    MaintenanceRecommendation,
    MaintenanceType,
)


@dataclass
class MaintenanceEvent:
    """Historical maintenance event data."""

    component: str
    event_type: str
    date: datetime
    cost: float
    urgency: float
    operating_hours: float
    weather_severity: float


class MaintenanceForecaster:
    """
    Advanced maintenance forecasting using time-series analysis and survival analysis.
    Predicts optimal maintenance windows and component failure probabilities.
    """

    def __init__(self):
        """Initialize the maintenance forecaster with ML models."""
        self.failure_model = None
        self.urgency_model = None
        self.cost_model = None
        self.scaler = StandardScaler()
        self.component_models = {}
        self.is_trained = False
        from src.services.model_config_service import model_config

        self.component_categories = model_config.get_component_categories()
        # Define feature order for consistency
        self.feature_order = [
            "total_operating_hours",
            "recent_operating_hours",
            "average_speed",
            "engine_load_avg",
            "fuel_efficiency",
            "weather_severity_avg",
            "storm_exposure_hours",
            "rough_sea_percentage",
            "days_since_last_maintenance",
            "maintenance_frequency",
            "average_maintenance_cost",
            "emergency_maintenance_ratio",
            "month",
            "quarter",
            "is_winter",
            "ship_age_years",
            "condition_score",
        ]
        # Add component-specific features to the order
        for component_category in self.component_categories:
            self.feature_order.append(f"{component_category}_last_maintenance")
            self.feature_order.append(f"{component_category}_failure_history")

        self._initialize_models()

    def _initialize_models(self):
        """Initialize ML models for maintenance forecasting."""
        # Failure probability classifier
        from src.services.model_config_service import model_config

        rf_config = model_config.get_random_forest_config()
        self.failure_model = RandomForestClassifier(**rf_config)

        # Urgency score predictor
        gb_config = model_config.get_gradient_boosting_config()
        self.urgency_model = GradientBoostingRegressor(**gb_config)

        # Cost predictor
        self.cost_model = GradientBoostingRegressor(**gb_config)

        # Train with synthetic data for demonstration
        self._train_with_synthetic_data()

    def _train_with_synthetic_data(self):
        """Train models with synthetic maintenance data."""
        np.random.seed(42)
        n_samples = 500  # Further reduced for faster startup

        # Generate synthetic maintenance events
        events = self._generate_synthetic_events(n_samples)

        # Train models
        self.train(events)

    def _generate_synthetic_events(self, n_samples: int) -> List[MaintenanceEvent]:
        """Generate synthetic maintenance events for training."""
        events = []

        for _ in range(n_samples):
            # Random component
            component = np.random.choice(
                [
                    "Main Engine",
                    "Auxiliary Engine",
                    "Propeller",
                    "Rudder",
                    "Navigation System",
                    "Radar",
                    "Generator",
                    "Pumps",
                    "Hull Plates",
                    "Deck Equipment",
                    "Cargo Crane",
                    "Winch",
                    "Life Boats",
                    "Fire System",
                    "Radio",
                    "GPS",
                ]
            )

            # Operating hours (affects failure probability)
            operating_hours = np.random.exponential(8000)

            # Weather severity (affects component wear)
            weather_severity = np.random.uniform(0.1, 1.0)

            # Age factor
            age_factor = np.random.uniform(0.5, 2.0)

            # Calculate failure probability based on factors
            base_failure_prob = 0.1
            failure_prob = base_failure_prob * (
                1 + operating_hours / 10000 + weather_severity * 0.5 + age_factor * 0.3
            )

            # Determine event type based on failure probability
            if failure_prob > 0.8:
                event_type = "emergency"
                urgency = np.random.uniform(0.8, 1.0)
                cost_multiplier = 3.0
            elif failure_prob > 0.5:
                event_type = "preventive"
                urgency = np.random.uniform(0.4, 0.8)
                cost_multiplier = 1.5
            elif failure_prob > 0.3:
                event_type = "routine"
                urgency = np.random.uniform(0.2, 0.5)
                cost_multiplier = 1.0
            else:
                continue  # Skip low probability events

            # Calculate cost based on component and urgency
            base_cost = np.random.uniform(1000, 50000)
            cost = base_cost * cost_multiplier * (1 + urgency * 0.5)

            # Generate random date
            days_ago = np.random.randint(1, 365)
            event_date = datetime.now() - timedelta(days=days_ago)

            events.append(
                MaintenanceEvent(
                    component=component,
                    event_type=event_type,
                    date=event_date,
                    cost=cost,
                    urgency=urgency,
                    operating_hours=operating_hours,
                    weather_severity=weather_severity,
                )
            )

        return events

    def extract_features(
        self,
        ship_id: str,
        current_date: datetime,
        usage_data: Dict,
        historical_maintenance: List[Dict],
    ) -> Dict:
        """Extract features for maintenance prediction using centralized feature engineering."""
        from src.services.feature_engineering_service import feature_engineer

        return feature_engineer.extract_maintenance_features(
            ship_id, current_date, usage_data, historical_maintenance
        )

    def train(self, maintenance_events: List[MaintenanceEvent]):
        """Train maintenance forecasting models."""
        try:
            # Convert events to features
            features_list = []
            failure_labels = []
            urgency_labels = []
            cost_labels = []

            for event in maintenance_events:
                # Create synthetic features for training
                features = {
                    "total_operating_hours": event.operating_hours,
                    "recent_operating_hours": event.operating_hours * 0.1,
                    "average_speed": np.random.uniform(15, 25),
                    "engine_load_avg": np.random.uniform(0.5, 0.9),
                    "fuel_efficiency": np.random.uniform(0.6, 0.9),
                    "weather_severity_avg": event.weather_severity,
                    "storm_exposure_hours": event.weather_severity * 200,
                    "rough_sea_percentage": event.weather_severity * 0.5,
                    "days_since_last_maintenance": np.random.randint(30, 300),
                    "maintenance_frequency": np.random.uniform(2, 8),
                    "average_maintenance_cost": np.random.uniform(5000, 30000),
                    "emergency_maintenance_ratio": np.random.uniform(0.05, 0.3),
                    "month": event.date.month,
                    "quarter": (event.date.month - 1) // 3 + 1,
                    "is_winter": 1 if event.date.month in [12, 1, 2] else 0,
                    "ship_age_years": np.random.randint(5, 20),
                    "condition_score": np.random.uniform(0.6, 0.95),
                }

                # Add component-specific features
                for component_category in self.component_categories:
                    features[
                        f"{component_category}_last_maintenance"
                    ] = np.random.randint(30, 365)
                    features[
                        f"{component_category}_failure_history"
                    ] = np.random.uniform(0, 1)

                features_list.append(features)

                # Labels
                failure_labels.append(
                    1 if event.event_type in ["emergency", "preventive"] else 0
                )
                urgency_labels.append(event.urgency)
                cost_labels.append(event.cost)

            # Convert to DataFrame with consistent column order
            features_df = pd.DataFrame(features_list)
            features_df = features_df.reindex(columns=self.feature_order, fill_value=0)

            # Split data
            X_train, X_test, y_failure_train, y_failure_test = train_test_split(
                features_df, failure_labels, test_size=0.2, random_state=42
            )

            _, _, y_urgency_train, y_urgency_test = train_test_split(
                features_df, urgency_labels, test_size=0.2, random_state=42
            )

            _, _, y_cost_train, y_cost_test = train_test_split(
                features_df, cost_labels, test_size=0.2, random_state=42
            )

            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)

            # Train models
            self.failure_model.fit(X_train_scaled, y_failure_train)
            self.urgency_model.fit(X_train_scaled, y_urgency_train)
            self.cost_model.fit(X_train_scaled, y_cost_train)

            # Evaluate models
            failure_pred = self.failure_model.predict(X_test_scaled)
            urgency_pred = self.urgency_model.predict(X_test_scaled)
            cost_pred = self.cost_model.predict(X_test_scaled)

            self.model_metrics = {
                "failure_accuracy": np.mean(failure_pred == y_failure_test),
                "urgency_mae": mean_absolute_error(y_urgency_test, urgency_pred),
                "cost_mae": mean_absolute_error(y_cost_test, cost_pred),
                "training_samples": len(X_train),
            }

            self.is_trained = True

        except Exception as e:
            raise MaintenanceForecastError(f"Model training failed: {str(e)}")

    def forecast_maintenance(
        self, ship_id: str, usage_data: Dict, historical_maintenance: List[Dict]
    ) -> MaintenanceForecasting:
        """Forecast maintenance requirements for a ship."""
        if not self.is_trained:
            raise MaintenanceForecastError("Model not trained")

        try:
            current_date = datetime.now()

            # Extract features
            features = self.extract_features(
                ship_id, current_date, usage_data, historical_maintenance
            )

            # Validate and prepare model input
            from src.services.data_validation_service import data_validator

            features_df = data_validator.validate_model_input(
                features, self.feature_order
            )

            # Scale features
            features_scaled = self.scaler.transform(features_df)

            # Generate recommendations for each component category
            recommendations = []
            next_critical_date = None
            min_days_to_maintenance = float("inf")

            for component_category in self.component_categories:
                # Predict failure probability
                failure_prob = self.failure_model.predict_proba(features_scaled)[0][1]

                # Predict urgency
                urgency_score = max(
                    0, min(1, self.urgency_model.predict(features_scaled)[0])
                )

                # Predict cost
                estimated_cost = max(0, self.cost_model.predict(features_scaled)[0])

                # Calculate maintenance window
                days_to_maintenance = self._calculate_maintenance_window(
                    component_category, features, failure_prob, urgency_score
                )

                # Only recommend if maintenance is needed soon
                if days_to_maintenance <= 180:  # Within 6 months
                    maintenance_type = self._determine_maintenance_type(
                        failure_prob, urgency_score
                    )

                    recommended_date = current_date + timedelta(
                        days=days_to_maintenance
                    )

                    reasoning = self._generate_reasoning(
                        component_category, failure_prob, urgency_score, features
                    )

                    # Determine risk level based on urgency score
                    if urgency_score >= 0.8:
                        risk_level = "critical"
                    elif urgency_score >= 0.6:
                        risk_level = "high"
                    elif urgency_score >= 0.4:
                        risk_level = "medium"
                    else:
                        risk_level = "low"

                    recommendation = MaintenanceRecommendation(
                        component=component_category.replace("_", " ").title(),
                        maintenance_type=maintenance_type,
                        recommended_date=recommended_date,
                        urgency_score=urgency_score,
                        estimated_cost=estimated_cost,
                        description=reasoning,  # Use reasoning as description
                        risk_level=risk_level,
                    )

                    recommendations.append(recommendation)

                    # Track next critical date
                    if days_to_maintenance < min_days_to_maintenance:
                        min_days_to_maintenance = days_to_maintenance
                        next_critical_date = recommended_date

            # Sort recommendations by urgency
            recommendations.sort(key=lambda x: x.urgency_score, reverse=True)

            # Calculate overall confidence
            confidence_score = self._calculate_confidence_score(
                features, recommendations
            )

            return MaintenanceForecasting(
                recommendations=recommendations,
                confidence_score=confidence_score,
                next_critical_date=next_critical_date,
            )

        except Exception as e:
            raise MaintenanceForecastError(f"Maintenance forecasting failed: {str(e)}")

    def _calculate_maintenance_window(
        self,
        component_category: str,
        features: Dict,
        failure_prob: float,
        urgency_score: float,
    ) -> int:
        """Calculate optimal maintenance window in days."""
        # Base maintenance intervals by component type
        base_intervals = {
            "engine": 90,
            "propulsion": 120,
            "navigation": 180,
            "electrical": 150,
            "hull": 365,
            "cargo_handling": 120,
            "safety": 180,
            "communication": 240,
        }

        base_interval = base_intervals.get(component_category, 180)

        # Adjust based on failure probability and urgency
        adjustment_factor = 1.0 - (failure_prob * 0.5 + urgency_score * 0.3)

        # Consider operating hours
        operating_hours_factor = features.get("total_operating_hours", 8000) / 8000

        # Consider weather exposure
        weather_factor = 1.0 + features.get("weather_severity_avg", 0.5) * 0.3

        # Calculate final window
        maintenance_window = int(
            base_interval * adjustment_factor / operating_hours_factor / weather_factor
        )

        return max(7, min(365, maintenance_window))  # Clamp between 1 week and 1 year

    def _determine_maintenance_type(
        self, failure_prob: float, urgency_score: float
    ) -> MaintenanceType:
        """Determine maintenance type based on failure probability and urgency."""
        if failure_prob > 0.8 or urgency_score > 0.8:
            return MaintenanceType.EMERGENCY
        elif failure_prob > 0.5 or urgency_score > 0.5:
            return MaintenanceType.PREVENTIVE
        elif failure_prob > 0.3 or urgency_score > 0.3:
            return MaintenanceType.ROUTINE
        else:
            return MaintenanceType.ROUTINE

    def _generate_reasoning(
        self,
        component_category: str,
        failure_prob: float,
        urgency_score: float,
        features: Dict,
    ) -> str:
        """Generate human-readable reasoning for maintenance recommendation."""
        reasons = []

        if failure_prob > 0.7:
            reasons.append("High failure probability detected")

        if urgency_score > 0.7:
            reasons.append("Urgent maintenance required")

        if features.get("days_since_last_maintenance", 0) > 180:
            reasons.append("Extended period since last maintenance")

        if features.get("weather_severity_avg", 0) > 0.7:
            reasons.append("High weather exposure impact")

        if features.get("total_operating_hours", 0) > 10000:
            reasons.append("High operating hours")

        if features.get("emergency_maintenance_ratio", 0) > 0.2:
            reasons.append("History of emergency maintenance")

        if not reasons:
            reasons.append("Routine maintenance schedule")

        return f"{component_category.replace('_', ' ').title()} maintenance recommended due to: {', '.join(reasons)}"

    def _calculate_confidence_score(
        self, features: Dict, recommendations: List[MaintenanceRecommendation]
    ) -> float:
        """Calculate confidence score for maintenance forecasting."""
        base_confidence = 0.8

        # Reduce confidence if insufficient data
        if features.get("days_since_last_maintenance", 0) > 365:
            base_confidence -= 0.2

        # Reduce confidence for high uncertainty
        if features.get("emergency_maintenance_ratio", 0) > 0.3:
            base_confidence -= 0.1

        # Increase confidence with more maintenance history
        maintenance_frequency = features.get("maintenance_frequency", 4)
        if maintenance_frequency > 6:
            base_confidence += 0.1

        # Adjust based on number of recommendations
        if len(recommendations) > 5:
            base_confidence -= 0.1

        return max(0.1, min(1.0, base_confidence))

    def update_model(self, new_events: List[MaintenanceEvent]):
        """Update model with new maintenance events."""
        if not self.is_trained:
            raise MaintenanceForecastError("Model must be trained before updating")

        # For demonstration, retrain with new data
        # In production, use incremental learning
        self.train(new_events)

    def get_model_metrics(self) -> Dict:
        """Get model performance metrics."""
        return getattr(self, "model_metrics", {})

    def save_model(self, filepath: str):
        """Save trained model to file."""
        if not self.is_trained:
            raise MaintenanceForecastError("Model not trained")

        model_data = {
            "failure_model": self.failure_model,
            "urgency_model": self.urgency_model,
            "cost_model": self.cost_model,
            "scaler": self.scaler,
            "model_metrics": getattr(self, "model_metrics", {}),
            "component_categories": self.component_categories,
            "feature_order": self.feature_order,
        }

        joblib.dump(model_data, filepath)

    def load_model(self, filepath: str):
        """Load trained model from file."""
        try:
            model_data = joblib.load(filepath)

            self.failure_model = model_data["failure_model"]
            self.urgency_model = model_data["urgency_model"]
            self.cost_model = model_data["cost_model"]
            self.scaler = model_data["scaler"]
            self.model_metrics = model_data.get("model_metrics", {})
            self.component_categories = model_data.get(
                "component_categories", self.component_categories
            )
            self.feature_order = model_data.get("feature_order", self.feature_order)
            self.is_trained = True

        except Exception as e:
            raise MaintenanceForecastError(f"Failed to load model: {str(e)}")


# Global maintenance forecaster instance
maintenance_forecaster = MaintenanceForecaster()
