"""
Basic health check tests for the Ship Planning System.
These tests ensure the CI workflow works correctly.
"""
import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


def test_environment_setup():
    """Test that basic environment setup works."""
    # Test that we can import core modules
    from src.core.config import Settings
    from src.core.exceptions import ShipPlanningException

    # Test basic configuration
    settings = Settings(
        database_url="postgresql://test:test@localhost:5432/test",
        weather_api_key="test_key",
        secret_key="test_secret",
    )

    assert settings.database_url == "postgresql://test:test@localhost:5432/test"
    assert settings.weather_api_key == "test_key"
    assert settings.secret_key == "test_secret"


def test_basic_imports():
    """Test that all core modules can be imported."""
    try:
        from src.api.v1 import feedback, maintenance, voyage
        from src.core import config, exceptions, models
        from src.data import database, schemas
        from src.models import fuel_predictor, maintenance_forecaster, route_optimizer
        from src.services import cache_service, data_validation_service
        from src.utils import weather_client

        # If we get here, all imports work
        assert True
    except ImportError as e:
        pytest.fail(f"Import failed: {e}")


@patch("src.data.database.db_manager")
def test_app_creation(mock_db_manager):
    """Test that the FastAPI app can be created."""
    # Mock the database manager
    mock_db_manager.initialize = MagicMock()
    mock_db_manager.close = MagicMock()

    # Set required environment variables
    os.environ.update(
        {
            "DATABASE_URL": "postgresql://test:test@localhost:5432/test",
            "WEATHER_API_KEY": "test_key",
            "SECRET_KEY": "test_secret",
            "DEBUG": "true",
        }
    )

    try:
        from main import app

        client = TestClient(app)

        # Test that the app responds to basic requests
        response = client.get("/")
        assert response.status_code == 200

        # Test health endpoint
        response = client.get("/health")
        assert response.status_code == 200

    except Exception as e:
        pytest.fail(f"App creation failed: {e}")


def test_basic_calculations():
    """Test basic mathematical operations used in the system."""
    import numpy as np
    import pandas as pd

    # Test numpy operations
    arr = np.array([1, 2, 3, 4, 5])
    assert np.mean(arr) == 3.0
    assert np.sum(arr) == 15

    # Test pandas operations
    df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    assert len(df) == 3
    assert df["a"].sum() == 6
    assert df["b"].mean() == 5.0


def test_model_imports():
    """Test that ML models can be imported and initialized."""
    try:
        from src.models.fuel_predictor import FuelPredictor
        from src.models.maintenance_forecaster import MaintenanceForecaster
        from src.models.route_optimizer import RouteOptimizer

        # Test basic model initialization
        fuel_predictor = FuelPredictor()
        assert fuel_predictor is not None

        maintenance_forecaster = MaintenanceForecaster()
        assert maintenance_forecaster is not None

        route_optimizer = RouteOptimizer()
        assert route_optimizer is not None

    except Exception as e:
        pytest.fail(f"Model import/initialization failed: {e}")


@pytest.mark.asyncio
async def test_async_functionality():
    """Test that async functionality works correctly."""
    import asyncio

    async def sample_async_function():
        await asyncio.sleep(0.01)  # Minimal delay
        return "async_result"

    result = await sample_async_function()
    assert result == "async_result"


def test_pydantic_models():
    """Test that Pydantic models work correctly."""
    from datetime import datetime
    from uuid import uuid4

    from src.core.models import Coordinates, VoyagePlanRequest

    # Test Coordinates model
    coords = Coordinates(latitude=40.7128, longitude=-74.0060)
    assert coords.latitude == 40.7128
    assert coords.longitude == -74.0060

    # Test VoyagePlanRequest model
    test_ship_id = uuid4()
    request = VoyagePlanRequest(
        ship_id=test_ship_id,
        origin=Coordinates(latitude=40.7128, longitude=-74.0060),
        destination=Coordinates(latitude=51.5074, longitude=-0.1278),
        departure_time=datetime.now(),
        cargo_weight=25000,
    )

    assert request.ship_id == test_ship_id
    assert request.cargo_weight == 25000
    assert isinstance(request.origin, Coordinates)
    assert isinstance(request.destination, Coordinates)


if __name__ == "__main__":
    pytest.main([__file__])
