from typing import Dict, Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

from src.core.exceptions import FuelPredictionError
from src.core.models import FuelPrediction


class FuelPredictor:
    """
    Advanced fuel consumption prediction using gradient boosting with
    feature engineering.
    Incorporates weather conditions, ship specifications, and route characteristics.
    """

    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        from src.services.model_config_service import model_config

        poly_config = model_config.get_feature_engineering_config()
        self.poly_features = PolynomialFeatures(
            degree=poly_config["polynomial_degree"],
            include_bias=poly_config["include_bias"],
        )
        self.feature_names = []
        self.model_metrics = {}
        self.is_trained = False
        self._initialize_model()

    def _initialize_model(self):
        """Initialize the gradient boosting model with optimal
        hyperparameters."""
        from src.services.model_config_service import model_config

        gb_config = model_config.get_gradient_boosting_config()
        self.model = GradientBoostingRegressor(**gb_config)

        # Train with synthetic data for demonstration
        self._train_with_synthetic_data()

    def _train_with_synthetic_data(self):
        """Train model with synthetic data for demonstration purposes."""
        # Generate synthetic training data
        np.random.seed(42)
        n_samples = 500  # Further reduced for faster startup

        # Generate features
        features = self._generate_synthetic_features(n_samples)

        # Generate synthetic fuel consumption based on realistic relationships
        fuel_consumption = self._generate_synthetic_fuel_consumption(features)

        # Train the model
        self.train(features, fuel_consumption)

    def _generate_synthetic_features(self, n_samples: int) -> pd.DataFrame:
        """Generate synthetic feature data for training."""
        data = {
            # Ship specifications
            "displacement": np.random.normal(50000, 15000, n_samples),
            "engine_power": np.random.normal(15000, 5000, n_samples),
            "max_speed": np.random.normal(22, 3, n_samples),
            "cargo_weight": np.random.normal(25000, 10000, n_samples),
            "ship_age": np.random.randint(1, 25, n_samples),
            # Route characteristics
            "distance": np.random.normal(3000, 1500, n_samples),
            "average_speed": np.random.normal(18, 4, n_samples),
            "port_calls": np.random.randint(1, 8, n_samples),
            "route_complexity": np.random.uniform(0.1, 1.0, n_samples),
            # Weather conditions
            "avg_wind_speed": np.random.normal(12, 6, n_samples),
            "avg_wave_height": np.random.normal(2.5, 1.5, n_samples),
            "avg_temperature": np.random.normal(20, 15, n_samples),
            "weather_severity": np.random.uniform(0.1, 1.0, n_samples),
            "headwind_percentage": np.random.uniform(0.2, 0.8, n_samples),
            # Operational factors
            "cargo_density": np.random.uniform(0.3, 1.0, n_samples),
            "fuel_efficiency_rating": np.random.uniform(0.5, 1.0, n_samples),
            "maintenance_score": np.random.uniform(0.6, 1.0, n_samples),
        }

        # Ensure realistic constraints
        data["displacement"] = np.clip(data["displacement"], 10000, 150000)
        data["engine_power"] = np.clip(data["engine_power"], 5000, 50000)
        data["max_speed"] = np.clip(data["max_speed"], 10, 35)
        data["cargo_weight"] = np.clip(
            data["cargo_weight"], 0, data["displacement"] * 0.8
        )
        data["distance"] = np.clip(data["distance"], 100, 15000)
        data["average_speed"] = np.clip(data["average_speed"], 8, data["max_speed"])
        data["avg_wind_speed"] = np.clip(data["avg_wind_speed"], 0, 40)
        data["avg_wave_height"] = np.clip(data["avg_wave_height"], 0, 12)

        return pd.DataFrame(data)

    def _generate_synthetic_fuel_consumption(
        self, features: pd.DataFrame
    ) -> np.ndarray:
        """Generate realistic synthetic fuel consumption data."""
        # Base consumption factors
        base_consumption = (
            features["distance"] * 0.1
            + features["displacement"] * 0.0001  # Distance factor
            + features["engine_power"] * 0.0002  # Ship size factor
            + features["average_speed"] ** 2  # Engine power factor
            * 0.5  # Speed factor (quadratic)
        )

        # Weather impact
        weather_impact = (
            features["avg_wind_speed"] * 0.3
            + features["avg_wave_height"] * 0.5
            + features["weather_severity"] * 20
            + features["headwind_percentage"] * 15
        )

        # Cargo impact
        cargo_impact = (
            features["cargo_weight"] * 0.0003 + features["cargo_density"] * 10
        )

        # Operational efficiency
        efficiency_factor = (
            features["fuel_efficiency_rating"] * 0.8
            + features["maintenance_score"] * 0.6
            + (1.0 / (features["ship_age"] + 1)) * 0.4
        )

        # Port calls penalty
        port_penalty = features["port_calls"] * 5

        # Combine all factors
        fuel_consumption = (
            base_consumption + weather_impact + cargo_impact + port_penalty
        ) / efficiency_factor

        # Add realistic noise
        noise = np.random.normal(0, fuel_consumption * 0.05)
        fuel_consumption += noise

        # Ensure positive values
        return np.clip(fuel_consumption, 10, 10000)

    def extract_features(
        self,
        ship_specs: Dict,
        route_data: Dict,
        weather_conditions: Optional[Dict] = None,
    ) -> Dict:
        """Extract features for fuel prediction using centralized feature engineering."""
        from src.services.feature_engineering_service import feature_engineer

        features = feature_engineer.extract_fuel_features(
            ship_specs, route_data, weather_conditions
        )

        # Add fuel-specific features
        features["fuel_efficiency_rating"] = ship_specs.get(
            "fuel_efficiency_rating", 0.8
        )
        features["maintenance_score"] = ship_specs.get("maintenance_score", 0.85)

        return features

    # Removed duplicate method - now in FeatureEngineeringService
    def _calculate_route_complexity_REMOVED(self, route_data: Dict) -> float:
        """Calculate route complexity score."""
        waypoints = route_data.get("waypoints", [])
        if len(waypoints) < 2:
            return 0.1

        # Calculate based on number of waypoints and direction changes
        complexity = len(waypoints) / 10.0  # Normalize by typical number of waypoints

        # Add penalty for direction changes (simplified)
        direction_changes = max(0, len(waypoints) - 2)
        complexity += direction_changes * 0.1

        return min(1.0, complexity)

    # Removed duplicate method - now in FeatureEngineeringService
    def _calculate_weather_severity_REMOVED(self, weather_conditions: Dict) -> float:
        """Calculate overall weather severity score."""
        wind_speed = weather_conditions.get("wind_speed", 12)
        wave_height = weather_conditions.get("wave_height", 2.5)
        precipitation = weather_conditions.get("precipitation", 0)
        visibility = weather_conditions.get("visibility", 10)

        # Normalize factors
        wind_factor = min(1.0, wind_speed / 30)
        wave_factor = min(1.0, wave_height / 8)
        precip_factor = min(1.0, precipitation / 50)
        visibility_factor = max(0.0, 1.0 - visibility / 10)

        # Weighted average
        severity = (
            wind_factor * 0.3
            + wave_factor * 0.4
            + precip_factor * 0.2
            + visibility_factor * 0.1
        )

        return severity

    def train(self, features: pd.DataFrame, fuel_consumption: np.ndarray):
        """Train the fuel prediction model."""
        try:
            # Store feature names
            self.feature_names = list(features.columns)

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                features, fuel_consumption, test_size=0.2, random_state=42
            )

            # Feature engineering
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)

            # Add polynomial features
            X_train_poly = self.poly_features.fit_transform(X_train_scaled)
            X_test_poly = self.poly_features.transform(X_test_scaled)

            # Train model
            self.model.fit(X_train_poly, y_train)

            # Evaluate model
            y_pred = self.model.predict(X_test_poly)

            self.model_metrics = {
                "mae": mean_absolute_error(y_test, y_pred),
                "r2": r2_score(y_test, y_pred),
                "mape": np.mean(np.abs((y_test - y_pred) / y_test)) * 100,
                "training_samples": len(X_train),
                "test_samples": len(X_test),
            }

            self.is_trained = True

        except Exception as e:
            raise FuelPredictionError(f"Model training failed: {str(e)}")

    def predict(
        self,
        ship_specs: Dict,
        route_data: Dict,
        weather_conditions: Optional[Dict] = None,
    ) -> FuelPrediction:
        """Predict fuel consumption for a voyage."""
        if not self.is_trained:
            raise FuelPredictionError("Model not trained")

        try:
            # Extract features
            features = self.extract_features(ship_specs, route_data, weather_conditions)

            # Validate and prepare model input
            from src.services.data_validation_service import data_validator

            feature_df = data_validator.validate_model_input(
                features, self.feature_names
            )

            # Scale features
            features_scaled = self.scaler.transform(feature_df)

            # Add polynomial features
            features_poly = self.poly_features.transform(features_scaled)

            # Make prediction
            prediction = self.model.predict(features_poly)[0]

            # Calculate confidence interval
            confidence_interval = self._calculate_confidence_interval(features_poly)

            # Calculate contributing factors
            contributing_factors = self._calculate_contributing_factors(features)

            # Calculate efficiency score
            efficiency_score = self._calculate_efficiency_score(features, prediction)

            return FuelPrediction(
                estimated_consumption=max(0, prediction),
                confidence_interval=confidence_interval,
                factors=contributing_factors,
                efficiency_score=efficiency_score,
            )

        except Exception as e:
            raise FuelPredictionError(f"Fuel prediction failed: {str(e)}")

    def _calculate_confidence_interval(
        self, features_poly: np.ndarray
    ) -> Dict[str, float]:
        """Calculate confidence interval for prediction."""
        # Simplified confidence interval calculation
        # In production, use more sophisticated methods like quantile regression

        prediction = self.model.predict(features_poly)[0]

        # Estimate uncertainty based on model performance
        mae = self.model_metrics.get("mae", prediction * 0.1)

        # Calculate bounds
        lower_bound = max(0, prediction - 1.96 * mae)
        upper_bound = prediction + 1.96 * mae

        return {"lower": lower_bound, "upper": upper_bound, "std_error": mae}

    def _calculate_contributing_factors(self, features: Dict) -> Dict[str, float]:
        """Calculate contribution of different factors to fuel consumption."""
        # Calculate relative impacts (simplified)
        factors = {
            "distance": min(40, features["distance"] / 100),
            "speed": min(25, (features["average_speed"] ** 2) / 20),
            "weather": min(20, features["weather_severity"] * 20),
            "cargo": min(15, features["cargo_density"] * 15),
            "ship_efficiency": max(0, 20 - features["fuel_efficiency_rating"] * 20),
            "route_complexity": min(10, features["route_complexity"] * 10),
        }

        # Normalize to sum to 100
        total = sum(factors.values())
        if total > 0:
            factors = {k: (v / total) * 100 for k, v in factors.items()}

        return factors

    def _calculate_efficiency_score(self, features: Dict, prediction: float) -> float:
        """Calculate fuel efficiency score."""
        # Baseline consumption for comparison
        baseline_consumption = (
            features["distance"] * features["displacement"] * 0.00001
            + features["average_speed"] ** 2 * 0.5
        )

        if baseline_consumption <= 0:
            return 0.5

        # Calculate efficiency relative to baseline
        efficiency_ratio = baseline_consumption / prediction

        # Normalize to 0-1 scale
        efficiency_score = min(1.0, max(0.0, efficiency_ratio))

        return efficiency_score

    def update_model(
        self, new_features: pd.DataFrame, new_fuel_consumption: np.ndarray
    ):
        """Update model with new data (incremental learning)."""
        if not self.is_trained:
            raise FuelPredictionError("Model must be trained before updating")

        try:
            # For demonstration, retrain with combined data
            # In production, use online learning algorithms

            # Scale new features
            new_features_scaled = self.scaler.transform(new_features)
            new_features_poly = self.poly_features.transform(new_features_scaled)

            # Simple incremental update (in production, use more sophisticated methods)
            self.model.fit(new_features_poly, new_fuel_consumption)

            # Update metrics
            predictions = self.model.predict(new_features_poly)
            new_mae = mean_absolute_error(new_fuel_consumption, predictions)

            # Update model metrics (exponential moving average)
            alpha = 0.1
            self.model_metrics["mae"] = (1 - alpha) * self.model_metrics[
                "mae"
            ] + alpha * new_mae

        except Exception as e:
            raise FuelPredictionError(f"Model update failed: {str(e)}")

    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance from the trained model."""
        if not self.is_trained:
            raise FuelPredictionError("Model not trained")

        # Get feature importance from gradient boosting
        importances = self.model.feature_importances_

        # Map to original feature names (simplified for polynomial features)
        feature_importance = {}
        for i, importance in enumerate(importances[: len(self.feature_names)]):
            feature_importance[self.feature_names[i]] = importance

        # Sort by importance
        sorted_importance = dict(
            sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
        )

        return sorted_importance

    def save_model(self, filepath: str):
        """Save trained model to file."""
        if not self.is_trained:
            raise FuelPredictionError("Model not trained")

        model_data = {
            "model": self.model,
            "scaler": self.scaler,
            "poly_features": self.poly_features,
            "feature_names": self.feature_names,
            "model_metrics": self.model_metrics,
        }

        joblib.dump(model_data, filepath)

    def load_model(self, filepath: str):
        """Load trained model from file."""
        try:
            model_data = joblib.load(filepath)

            self.model = model_data["model"]
            self.scaler = model_data["scaler"]
            self.poly_features = model_data["poly_features"]
            self.feature_names = model_data["feature_names"]
            self.model_metrics = model_data["model_metrics"]
            self.is_trained = True

        except Exception as e:
            raise FuelPredictionError(f"Failed to load model: {str(e)}")

    def get_model_metrics(self) -> Dict:
        """Get model performance metrics."""
        return self.model_metrics.copy()


# Global fuel predictor instance
fuel_predictor = FuelPredictor()
