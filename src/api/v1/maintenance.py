from datetime import datetime, timedelta
from typing import List
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.dependencies import (
    get_cache_service,
    get_current_user,
    get_database_session,
)
from src.core.exceptions import MaintenanceForecastError
from src.core.models import (
    APIResponse,
    MaintenanceForecasting,
    MaintenanceRecommendation,
)
from src.models.maintenance_forecaster import maintenance_forecaster
from src.services.cache_service import CacheService

logger = structlog.get_logger()
router = APIRouter()


@router.get("/maintenance-alerts", response_model=MaintenanceForecasting)
async def get_maintenance_alerts(
    ship_id: UUID,
    current_user: dict = Depends(get_current_user),
    cache: CacheService = Depends(get_cache_service),
    db: Session = Depends(get_database_session),
):
    """
    🔧 Get predictive maintenance alerts for a ship.

    Uses AI to forecast maintenance needs based on:
    - **Operating Hours**: Engine usage and wear patterns
    - **Weather Exposure**: Environmental impact on components
    - **Historical Data**: Past maintenance events and failures
    - **Usage Patterns**: Operational stress factors

    Returns prioritized maintenance recommendations with optimal scheduling.
    """
    try:
        logger.info(
            "Generating maintenance alerts",
            user_id=current_user["user_id"],
            ship_id=str(ship_id),
        )

        # Check cache first
        cached_forecast = await cache.get_cached_maintenance_forecast(str(ship_id))
        if cached_forecast:
            logger.info("Returning cached maintenance forecast", ship_id=str(ship_id))
            return MaintenanceForecasting(**cached_forecast)

        # Get ship usage data
        from src.services.maintenance_data_service import maintenance_data_service

        usage_data = await maintenance_data_service.get_ship_usage_data(ship_id, db)

        # Get historical maintenance data
        historical_maintenance = (
            await maintenance_data_service.get_historical_maintenance(ship_id, db)
        )

        # Generate maintenance forecast
        forecast = maintenance_forecaster.forecast_maintenance(
            ship_id=str(ship_id),
            usage_data=usage_data,
            historical_maintenance=historical_maintenance,
        )

        # Cache the result
        await cache.cache_maintenance_forecast(str(ship_id), forecast.model_dump())

        logger.info(
            "Maintenance forecast generated",
            ship_id=str(ship_id),
            recommendations_count=len(forecast.recommendations),
            confidence_score=forecast.confidence_score,
            next_critical_date=forecast.next_critical_date.isoformat()
            if forecast.next_critical_date
            else None,
        )

        return forecast

    except MaintenanceForecastError as e:
        logger.error("Maintenance forecasting failed", error=str(e))
        raise HTTPException(
            status_code=400, detail=f"Maintenance forecasting failed: {str(e)}"
        )

    except Exception as e:
        logger.error(
            "Failed to generate maintenance alerts", error=str(e), exc_info=True
        )
        raise HTTPException(
            status_code=500, detail="Failed to generate maintenance alerts"
        )


@router.get(
    "/maintenance-alerts/{ship_id}/component/{component}",
    response_model=List[MaintenanceRecommendation],
)
async def get_component_maintenance_alerts(
    ship_id: UUID,
    component: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_database_session),
):
    """
    🔍 Get maintenance alerts for a specific ship component.

    Returns detailed maintenance recommendations for a particular component.
    """
    try:
        logger.info(
            "Getting component maintenance alerts",
            user_id=current_user["user_id"],
            ship_id=str(ship_id),
            component=component,
        )

        # Get full maintenance forecast
        from src.services.maintenance_data_service import maintenance_data_service

        usage_data = await maintenance_data_service.get_ship_usage_data(ship_id, db)
        historical_maintenance = (
            await maintenance_data_service.get_historical_maintenance(ship_id, db)
        )

        forecast = maintenance_forecaster.forecast_maintenance(
            ship_id=str(ship_id),
            usage_data=usage_data,
            historical_maintenance=historical_maintenance,
        )

        # Filter recommendations for specific component
        component_recommendations = [
            rec
            for rec in forecast.recommendations
            if component.lower() in rec.component.lower()
        ]

        logger.info(
            "Component maintenance alerts retrieved",
            ship_id=str(ship_id),
            component=component,
            recommendations_count=len(component_recommendations),
        )

        return component_recommendations

    except Exception as e:
        logger.error("Failed to get component maintenance alerts", error=str(e))
        raise HTTPException(
            status_code=500, detail="Failed to get component maintenance alerts"
        )


@router.post("/maintenance-alerts/{ship_id}/schedule", response_model=APIResponse)
async def schedule_maintenance(
    ship_id: UUID,
    recommendation_id: str,
    scheduled_date: datetime,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_database_session),
):
    """
    📅 Schedule maintenance based on AI recommendations.

    Allows users to schedule maintenance activities based on AI forecasts.
    """
    try:
        logger.info(
            "Scheduling maintenance",
            user_id=current_user["user_id"],
            ship_id=str(ship_id),
            recommendation_id=recommendation_id,
            scheduled_date=scheduled_date.isoformat(),
        )

        # In production, this would:
        # 1. Validate the recommendation exists
        # 2. Check scheduling conflicts
        # 3. Create maintenance work order
        # 4. Update maintenance schedule
        # 5. Send notifications

        # Mock response for demonstration
        return APIResponse(
            success=True,
            message="Maintenance scheduled successfully",
            data={
                "ship_id": str(ship_id),
                "recommendation_id": recommendation_id,
                "scheduled_date": scheduled_date.isoformat(),
                "status": "scheduled",
            },
        )

    except Exception as e:
        logger.error("Failed to schedule maintenance", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to schedule maintenance")


@router.get("/maintenance-alerts/history/{ship_id}", response_model=List[dict])
async def get_maintenance_history(
    ship_id: UUID,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_database_session),
):
    """
    📋 Get maintenance history for a ship.

    Returns historical maintenance events with prediction accuracy metrics.
    """
    try:
        logger.info(
            "Fetching maintenance history",
            user_id=current_user["user_id"],
            ship_id=str(ship_id),
            limit=limit,
            offset=offset,
        )

        # Mock data for demonstration
        history = []
        for i in range(min(limit, 10)):
            event = {
                "id": f"maint_{i}",
                "ship_id": str(ship_id),
                "component": ["Engine", "Propulsion", "Navigation", "Electrical"][
                    i % 4
                ],
                "maintenance_type": ["routine", "preventive", "emergency"][i % 3],
                "scheduled_date": (datetime.now() - timedelta(days=i * 30)).isoformat(),
                "completed_date": (
                    datetime.now() - timedelta(days=i * 30 - 2)
                ).isoformat(),
                "cost": 5000 + (i * 1000),
                "predicted_accurately": i % 3 != 0,
                "prediction_accuracy": 0.8 + (i * 0.02),
                "description": f"Routine maintenance for "
                f"{['Engine', 'Propulsion', 'Navigation', 'Electrical'][i % 4]}",
            }
            history.append(event)

        return history

    except Exception as e:
        logger.error("Failed to fetch maintenance history", error=str(e))
        raise HTTPException(
            status_code=500, detail="Failed to Fetch the Maintanence History"
        )


@router.get("/maintenance-alerts/analytics/{ship_id}", response_model=dict)
async def get_maintenance_analytics(
    ship_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_database_session),
):
    """
    📊 Get maintenance analytics and insights for a ship.

    Returns analytics on maintenance patterns, costs, and prediction accuracy.
    """
    try:
        logger.info(
            "Generating maintenance analytics",
            user_id=current_user["user_id"],
            ship_id=str(ship_id),
        )

        # Mock analytics data
        analytics = {
            "summary": {
                "total_maintenance_events": 45,
                "preventive_maintenance_ratio": 0.65,
                "average_cost_per_event": 8500,
                "prediction_accuracy": 0.87,
                "cost_savings_from_predictions": 125000,
            },
            "trends": {
                "monthly_costs": [
                    {"month": "2024-01", "cost": 15000, "events": 3},
                    {"month": "2024-02", "cost": 12000, "events": 2},
                    {"month": "2024-03", "cost": 18000, "events": 4},
                    {"month": "2024-04", "cost": 9000, "events": 2},
                ],
                "component_breakdown": {
                    "Engine": {"events": 15, "cost": 45000, "avg_interval": 90},
                    "Propulsion": {"events": 12, "cost": 36000, "avg_interval": 120},
                    "Navigation": {"events": 8, "cost": 24000, "avg_interval": 180},
                    "Electrical": {"events": 10, "cost": 30000, "avg_interval": 150},
                },
            },
            "predictions": {
                "next_30_days": {
                    "expected_events": 2,
                    "estimated_cost": 15000,
                    "critical_components": ["Engine", "Propulsion"],
                },
                "next_90_days": {
                    "expected_events": 6,
                    "estimated_cost": 45000,
                    "critical_components": ["Engine", "Propulsion", "Navigation"],
                },
            },
            "recommendations": [
                "Consider increasing preventive maintenance frequency for "
                "Engine components",
                "Navigation system showing consistent performance - "
                "maintain current schedule",
                "Electrical systems may benefit from condition-based monitoring",
            ],
        }

        return analytics

    except Exception as e:
        logger.error("Failed to generate maintenance analytics", error=str(e))
        raise HTTPException(
            status_code=500, detail="Failed to generate maintenance analytics"
        )


# Removed duplicate helper functions - now using MaintenanceDataService
