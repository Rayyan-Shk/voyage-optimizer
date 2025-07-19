from typing import Dict, Any
from dataclasses import dataclass
import structlog

logger = structlog.get_logger()


@dataclass
class ModelHyperparameters:
    """Centralized model hyperparameters configuration."""
    
    # Random Forest parameters
    rf_n_estimators: int = 20
    rf_max_depth: int = 5
    rf_min_samples_split: int = 20
    rf_min_samples_leaf: int = 10
    rf_random_state: int = 42
    
    # Gradient Boosting parameters
    gb_n_estimators: int = 20
    gb_learning_rate: float = 0.2
    gb_max_depth: int = 4
    gb_min_samples_split: int = 20
    gb_min_samples_leaf: int = 10
    gb_subsample: float = 0.8
    gb_random_state: int = 42
    gb_validation_fraction: float = 0.1
    gb_n_iter_no_change: int = 3
    gb_tol: float = 1e-2
    
    # Training parameters
    test_size: float = 0.2
    random_state: int = 42
    
    # Feature engineering parameters
    polynomial_degree: int = 2
    
    # Synthetic data parameters
    synthetic_samples: int = 500
    synthetic_random_state: int = 42


class ModelConfigService:
    """
    Centralized model configuration service.
    Provides consistent configuration across all ML models.
    """
    
    def __init__(self):
        self.logger = structlog.get_logger(__name__)
        self.hyperparameters = ModelHyperparameters()
    
    def get_random_forest_config(self) -> Dict[str, Any]:
        """Get Random Forest configuration."""
        return {
            'n_estimators': self.hyperparameters.rf_n_estimators,
            'max_depth': self.hyperparameters.rf_max_depth,
            'min_samples_split': self.hyperparameters.rf_min_samples_split,
            'min_samples_leaf': self.hyperparameters.rf_min_samples_leaf,
            'random_state': self.hyperparameters.rf_random_state,
            'class_weight': 'balanced'
        }
    
    def get_gradient_boosting_config(self) -> Dict[str, Any]:
        """Get Gradient Boosting configuration."""
        return {
            'n_estimators': self.hyperparameters.gb_n_estimators,
            'learning_rate': self.hyperparameters.gb_learning_rate,
            'max_depth': self.hyperparameters.gb_max_depth,
            'min_samples_split': self.hyperparameters.gb_min_samples_split,
            'min_samples_leaf': self.hyperparameters.gb_min_samples_leaf,
            'subsample': self.hyperparameters.gb_subsample,
            'random_state': self.hyperparameters.gb_random_state,
            'validation_fraction': self.hyperparameters.gb_validation_fraction,
            'n_iter_no_change': self.hyperparameters.gb_n_iter_no_change,
            'tol': self.hyperparameters.gb_tol
        }
    
    def get_training_config(self) -> Dict[str, Any]:
        """Get training configuration."""
        return {
            'test_size': self.hyperparameters.test_size,
            'random_state': self.hyperparameters.random_state
        }
    
    def get_feature_engineering_config(self) -> Dict[str, Any]:
        """Get feature engineering configuration."""
        return {
            'polynomial_degree': self.hyperparameters.polynomial_degree,
            'include_bias': False
        }
    
    def get_synthetic_data_config(self) -> Dict[str, Any]:
        """Get synthetic data generation configuration."""
        return {
            'n_samples': self.hyperparameters.synthetic_samples,
            'random_state': self.hyperparameters.synthetic_random_state
        }
    
    def update_hyperparameters(self, **kwargs) -> None:
        """Update hyperparameters dynamically."""
        for key, value in kwargs.items():
            if hasattr(self.hyperparameters, key):
                setattr(self.hyperparameters, key, value)
                self.logger.info(f"Updated hyperparameter {key} to {value}")
            else:
                self.logger.warning(f"Unknown hyperparameter: {key}")
    
    def get_component_categories(self) -> list:
        """Get standard component categories."""
        return [
            'engine', 'propulsion', 'navigation', 'electrical', 
            'hull', 'cargo_handling', 'safety', 'communication'
        ]
    
    def get_maintenance_intervals(self) -> Dict[str, int]:
        """Get base maintenance intervals by component type."""
        return {
            'engine': 90,
            'propulsion': 120,
            'navigation': 180,
            'electrical': 150,
            'hull': 365,
            'cargo_handling': 120,
            'safety': 180,
            'communication': 240
        }
    
    def get_default_ship_specs(self) -> Dict[str, Any]:
        """Get default ship specifications."""
        return {
            'displacement': 50000,
            'engine_power': 15000,
            'max_speed': 22,
            'cargo_capacity': 30000,
            'age': 10,
            'total_operating_hours': 8000,
            'fuel_efficiency_rating': 0.8,
            'maintenance_score': 0.85
        }
    
    def get_default_weather_conditions(self) -> Dict[str, Any]:
        """Get default weather conditions."""
        return {
            'wind_speed': 12,
            'wave_height': 2.5,
            'temperature': 20,
            'weather_severity': 0.5,
            'headwind_percentage': 0.5
        }


# Global instance
model_config = ModelConfigService() 