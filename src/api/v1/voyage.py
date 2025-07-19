from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID, uuid4

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.dependencies import (
    get_cache_service,
    get_current_user,
    get_database_session,
)
from src.core.exceptions import FuelPredictionError, RouteOptimizationError
from src.core.models import (
    AlternativePlan,
    Coordinates,
    Route,
    VoyageHistory,
    VoyagePlanRequest,
    VoyagePlanResponse,
    VoyageStatus,
)
from src.models.fuel_predictor import fuel_predictor
from src.models.maintenance_forecaster import maintenance_forecaster
from src.models.route_optimizer import route_optimizer
from src.services.cache_service import CacheService
from src.utils.weather_client import WeatherClient

logger = structlog.get_logger()
router = APIRouter()


@router.post("/plan-voyage", response_model=VoyagePlanResponse)
async def plan_voyage(
    request: VoyagePlanRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    cache: CacheService = Depends(get_cache_service),
    db: Session = Depends(get_database_session),
):
    """
    🚢 Plan an optimal voyage with AI-powered route optimization.

    This endpoint combines multiple AI models to create the most efficient voyage plan:
    - **Route Optimization**: A* algorithm with ML-enhanced weights
    - **Fuel Prediction**: Gradient boosting with weather integration
    - **Maintenance Forecasting**: Predictive maintenance scheduling

    The system learns from each voyage to continuously improve predictions.
    """
    try:
        logger.info(
            "Planning voyage",
            user_id=current_user["user_id"],
            ship_id=str(request.ship_id),
            origin=f"{request.origin.latitude},{request.origin.longitude}",
            destination=f"{request.destination.latitude},"
            f"{request.destination.longitude}",
        )

        # Check cache first
        cache_key = (
            f"voyage_plan_{request.ship_id}_{request.origin.latitude}_"
            f"{request.origin.longitude}_{request.destination.latitude}_"
            f"{request.destination.longitude}"
        )
        cached_plan = await cache.get_cached_route(
            {
                "ship_id": str(request.ship_id),
                "origin": request.origin.model_dump(),
                "destination": request.destination.model_dump(),
                "departure_time": request.departure_time.isoformat(),
                "cargo_weight": request.cargo_weight,
            }
        )

        if cached_plan:
            logger.info("Returning cached voyage plan", cache_key=cache_key)
            return VoyagePlanResponse(**cached_plan)

        # Get ship specifications (mock data for demo)
        from src.services.maintenance_data_service import maintenance_data_service

        ship_specs = await maintenance_data_service.get_ship_specifications(
            request.ship_id, db
        )

        # Get weather data
        weather_client = WeatherClient()
        weather_data = None
        if request.weather_forecast:
            weather_data = request.weather_forecast.model_dump()
        else:
            # Fetch weather data for the route
            weather_data = await weather_client.get_route_weather(
                request.origin, request.destination
            )

        # Route optimization
        route_optimization = route_optimizer.optimize_route(
            origin=request.origin,
            destination=request.destination,
            ship_specs=ship_specs,
            weather_data=weather_data,
            optimization_preferences=request.optimization_preferences,
        )

        # Fuel prediction
        route_data = {
            "total_distance": route_optimization.total_distance,
            "average_speed": sum(wp.speed for wp in route_optimization.waypoints)
            / len(route_optimization.waypoints),
            "waypoints": [wp.model_dump() for wp in route_optimization.waypoints],
            "cargo_weight": request.cargo_weight,
        }

        fuel_prediction = fuel_predictor.predict(
            ship_specs=ship_specs,
            route_data=route_data,
            weather_conditions=weather_data,
        )

        # Maintenance recommendations
        from src.services.maintenance_data_service import maintenance_data_service

        usage_data = await maintenance_data_service.get_ship_usage_data(
            request.ship_id, db
        )
        historical_maintenance = (
            await maintenance_data_service.get_historical_maintenance(
                request.ship_id, db
            )
        )

        # Update usage data with voyage-specific information
        usage_data.update(
            {
                "recent_operating_hours": route_optimization.estimated_duration,
                "average_speed": route_data["average_speed"],
                "weather_severity_avg": (
                    weather_data.get("weather_severity", 0.5) if weather_data else 0.5
                ),
            }
        )

        maintenance_forecast = maintenance_forecaster.forecast_maintenance(
            ship_id=str(request.ship_id),
            usage_data=usage_data,
            historical_maintenance=historical_maintenance,
        )

        # Generate alternative plans
        alternative_plans = await generate_alternative_plans(
            request, ship_specs, weather_data, route_optimization, fuel_prediction
        )

        # Convert RouteOptimization to Route for response
        route_for_response = Route(
            waypoints=[wp.coordinates for wp in route_optimization.waypoints],
            total_distance=route_optimization.total_distance,
            estimated_duration=route_optimization.estimated_duration,
            confidence_score=route_optimization.confidence_score,
        )

        # Calculate total estimated cost
        total_estimated_cost = (
            fuel_prediction.estimated_consumption * 0.5
        )  # Assume $0.5 per liter
        if maintenance_forecast.recommendations:
            total_estimated_cost += sum(
                rec.estimated_cost for rec in maintenance_forecast.recommendations
            )

        # Calculate overall confidence score
        # Extract confidence from fuel prediction 
        # (use inverse of relative error as confidence)
        fuel_confidence = 1.0 - (
            fuel_prediction.confidence_interval["std_error"]
            / fuel_prediction.estimated_consumption
        )
        fuel_confidence = max(0.0, min(1.0, fuel_confidence))  # Clamp between 0 and 1

        confidence_score = (
            route_optimization.confidence_score * 0.4
            + fuel_confidence * 0.4
            + (
                sum(rec.urgency_score for rec in maintenance_forecast.recommendations)
                / len(maintenance_forecast.recommendations)
                if maintenance_forecast.recommendations
                else 0.8
            )
            * 0.2
        )

        # Create response
        response = VoyagePlanResponse(
            ship_id=request.ship_id,
            route=route_for_response,
            fuel_prediction=fuel_prediction,
            maintenance_recommendations=maintenance_forecast.recommendations,
            alternative_plans=alternative_plans,
            total_estimated_cost=total_estimated_cost,
            confidence_score=min(confidence_score, 1.0),  # Ensure it doesn't exceed 1.0
        )

        # Cache the result
        await cache.cache_route_optimization(
            {
                "ship_id": str(request.ship_id),
                "origin": request.origin.model_dump(),
                "destination": request.destination.model_dump(),
                "departure_time": request.departure_time.isoformat(),
                "cargo_weight": request.cargo_weight,
            },
            response.model_dump(),
        )

        # Store in database (background task)
        background_tasks.add_task(store_voyage_plan, response, db)

        logger.info(
            "Voyage planned successfully",
            voyage_id=str(response.voyage_id),
            total_distance=route_optimization.total_distance,
            estimated_fuel=fuel_prediction.estimated_consumption,
            confidence_score=route_optimization.confidence_score,
        )

        return response

    except RouteOptimizationError as e:
        logger.error("Route optimization failed", error=str(e))
        raise HTTPException(
            status_code=400, detail=f"Route optimization failed: {str(e)}"
        )

    except FuelPredictionError as e:
        logger.error("Fuel prediction failed", error=str(e))
        raise HTTPException(status_code=400, detail=f"Fuel prediction failed: {str(e)}")

    except Exception as e:
        logger.error("Voyage planning failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/plan-history", response_model=List[VoyageHistory])
async def get_voyage_history(
    ship_id: Optional[UUID] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_database_session),
):
    """
    📊 Get historical voyage plans with performance metrics.

    Returns voyage history with actual vs predicted comparisons for continuous learning.
    """
    try:
        logger.info(
            "Fetching voyage history",
            user_id=current_user["user_id"],
            ship_id=str(ship_id) if ship_id else None,
            limit=limit,
            offset=offset,
        )

        # Mock data for demonstration
        history = []
        for i in range(min(limit, 10)):
            # Create a simple route for mock data
            mock_route = Route(
                waypoints=[
                    Coordinates(latitude=40.7128, longitude=-74.0060),
                    Coordinates(latitude=51.5074, longitude=-0.1278),
                ],
                total_distance=3000.0 + i * 100,
                estimated_duration=150.0 + i * 5,
                confidence_score=0.85 + i * 0.01,
            )

            # Create mock voyage history
            mock_history = VoyageHistory(
                voyage_id=uuid4(),
                ship_id=ship_id or UUID("12345678-1234-5678-9012-123456789012"),
                planned_route=mock_route,
                actual_route=mock_route,  # In real app, this would be different
                planned_fuel=500.0 + i * 20,
                actual_fuel=520.0 + i * 25,  # Slightly higher than planned
                departure_time=datetime.now() - timedelta(days=i * 7),
                arrival_time=datetime.now() - timedelta(days=i * 7 - 5),
                status=VoyageStatus.COMPLETED,
                performance_metrics={
                    "fuel_accuracy": 0.92 - i * 0.02,
                    "time_accuracy": 0.88 + i * 0.01,
                    "route_efficiency": 0.95 - i * 0.01,
                },
            )
            history.append(mock_history)

        return history

    except Exception as e:
        logger.error("Failed to fetch voyage history", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch voyage history")


@router.get("/plan-history/{voyage_id}", response_model=VoyageHistory)
async def get_voyage_details(
    voyage_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_database_session),
):
    """
    🔍 Get detailed information about a specific voyage.
    """
    try:
        logger.info(
            "Fetching voyage details",
            user_id=current_user["user_id"],
            voyage_id=str(voyage_id),
        )

        # Mock data - would fetch from database
        # voyage = db.query(Voyage).filter(Voyage.id == voyage_id).first()
        # if not voyage:
        #     raise HTTPException(status_code=404, detail="Voyage not found")

        # Create mock route for demonstration
        mock_route = Route(
            waypoints=[
                Coordinates(latitude=40.7128, longitude=-74.0060),
                Coordinates(latitude=51.5074, longitude=-0.1278),
            ],
            total_distance=3000.0,
            estimated_duration=150.0,
            confidence_score=0.85,
        )

        # Return mock data for demonstration
        return VoyageHistory(
            voyage_id=voyage_id,
            ship_id=UUID("12345678-1234-5678-9012-123456789012"),
            planned_route=mock_route,
            actual_route=mock_route,
            planned_fuel=500.0,
            actual_fuel=520.0,
            departure_time=datetime.now() - timedelta(days=7),
            arrival_time=datetime.now() - timedelta(days=2),
            status=VoyageStatus.COMPLETED,
            performance_metrics={
                "fuel_accuracy": 0.92,
                "time_accuracy": 0.88,
                "route_efficiency": 0.95,
            },
        )

    except Exception as e:
        logger.error("Failed to fetch voyage details", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch voyage details")


# Helper functions
# Removed duplicate function - now using MaintenanceDataService.get_ship_specifications


async def generate_alternative_plans(
    request: VoyagePlanRequest,
    ship_specs: dict,
    weather_data: dict,
    primary_route: any,
    primary_fuel: any,
) -> List[AlternativePlan]:
    """Generate alternative voyage plans."""
    alternatives = []

    # Speed-optimized alternative
    speed_prefs = {"time": 0.7, "fuel": 0.2, "safety": 0.1}
    speed_route = route_optimizer.optimize_route(
        origin=request.origin,
        destination=request.destination,
        ship_specs=ship_specs,
        weather_data=weather_data,
        optimization_preferences=speed_prefs,
    )

    speed_fuel = fuel_predictor.predict(
        ship_specs=ship_specs,
        route_data={
            "total_distance": speed_route.total_distance,
            "average_speed": sum(wp.speed for wp in speed_route.waypoints)
            / len(speed_route.waypoints),
            "waypoints": [wp.model_dump() for wp in speed_route.waypoints],
            "cargo_weight": request.cargo_weight,
        },
        weather_conditions=weather_data,
    )

    # Convert RouteOptimization to Route
    speed_route_simple = Route(
        waypoints=[wp.coordinates for wp in speed_route.waypoints],
        total_distance=speed_route.total_distance,
        estimated_duration=speed_route.estimated_duration,
        confidence_score=speed_route.confidence_score,
    )

    # Calculate estimated arrival
    departure_time = request.departure_time
    speed_arrival = departure_time + timedelta(hours=speed_route.estimated_duration)

    alternatives.append(
        AlternativePlan(
            plan_id=f"speed_optimized_{uuid4().hex[:8]}",
            route=speed_route_simple,
            fuel_prediction=speed_fuel,
            estimated_arrival=speed_arrival,
            trade_offs={"time_benefit": 0.8, "fuel_cost": 0.6},  # Numeric values
            score=0.85,
        )
    )

    # Fuel-optimized alternative
    fuel_prefs = {"time": 0.2, "fuel": 0.7, "safety": 0.1}
    fuel_route = route_optimizer.optimize_route(
        origin=request.origin,
        destination=request.destination,
        ship_specs=ship_specs,
        weather_data=weather_data,
        optimization_preferences=fuel_prefs,
    )

    fuel_fuel = fuel_predictor.predict(
        ship_specs=ship_specs,
        route_data={
            "total_distance": fuel_route.total_distance,
            "average_speed": sum(wp.speed for wp in fuel_route.waypoints)
            / len(fuel_route.waypoints),
            "waypoints": [wp.model_dump() for wp in fuel_route.waypoints],
            "cargo_weight": request.cargo_weight,
        },
        weather_conditions=weather_data,
    )

    # Convert RouteOptimization to Route
    fuel_route_simple = Route(
        waypoints=[wp.coordinates for wp in fuel_route.waypoints],
        total_distance=fuel_route.total_distance,
        estimated_duration=fuel_route.estimated_duration,
        confidence_score=fuel_route.confidence_score,
    )

    # Calculate estimated arrival
    fuel_arrival = departure_time + timedelta(hours=fuel_route.estimated_duration)

    alternatives.append(
        AlternativePlan(
            plan_id=f"fuel_optimized_{uuid4().hex[:8]}",
            route=fuel_route_simple,
            fuel_prediction=fuel_fuel,
            estimated_arrival=fuel_arrival,
            trade_offs={"fuel_benefit": 0.9, "time_cost": 0.4},  # Numeric values
            score=0.82,
        )
    )

    return alternatives


async def store_voyage_plan(plan: VoyagePlanResponse, db: Session):
    """Store voyage plan in database (background task)."""
    try:
        # This would store the plan in the database
        logger.info("Storing voyage plan", voyage_id=str(plan.voyage_id))
        # db.add(VoyageRecord(**plan.dict()))
        # db.commit()
    except Exception as e:
        logger.error("Failed to store voyage plan", error=str(e))
