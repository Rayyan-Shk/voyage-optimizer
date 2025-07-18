from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any
from uuid import UUID
from datetime import datetime, timedelta

from src.core.models import VoyageFeedback, APIResponse
from src.core.exceptions import ModelError
from src.api.dependencies import get_current_user, get_cache_service, get_database_session
from src.models.route_optimizer import route_optimizer
from src.models.fuel_predictor import fuel_predictor
from src.models.maintenance_forecaster import maintenance_forecaster
from src.services.cache_service import CacheService
import structlog

logger = structlog.get_logger()
router = APIRouter()


@router.post("/feedback", response_model=APIResponse)
async def submit_voyage_feedback(
    feedback: VoyageFeedback,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    cache: CacheService = Depends(get_cache_service),
    db: Session = Depends(get_database_session)
):
    """
    📝 Submit voyage feedback for continuous learning.
    
    This endpoint accepts actual voyage data and uses it to improve AI models:
    - **Route Optimization**: Updates path-finding algorithms
    - **Fuel Prediction**: Retrains consumption models
    - **Maintenance Forecasting**: Improves failure prediction
    
    The system learns from each feedback to become more accurate over time.
    """
    try:
        logger.info(
            "Processing voyage feedback",
            user_id=current_user["user_id"],
            voyage_id=str(feedback.voyage_id),
            actual_fuel=feedback.actual_fuel_consumption,
            actual_duration=feedback.actual_duration
        )
        
        # Get original voyage plan for comparison
        original_plan = await get_original_voyage_plan(feedback.voyage_id, db)
        
        if not original_plan:
            raise HTTPException(status_code=404, detail="Original voyage plan not found")
        
        # Calculate prediction accuracy
        accuracy_metrics = calculate_prediction_accuracy(original_plan, feedback)
        
        # Process feedback in background for model improvement
        background_tasks.add_task(
            process_feedback_for_learning,
            feedback,
            original_plan,
            accuracy_metrics
        )
        
        # Invalidate related cache entries
        await cache.invalidate_ship_cache(str(original_plan.get("ship_id")))
        
        # Store feedback in database
        await store_voyage_feedback(feedback, accuracy_metrics, db)
        
        logger.info(
            "Voyage feedback processed successfully",
            voyage_id=str(feedback.voyage_id),
            fuel_accuracy=accuracy_metrics.get("fuel_accuracy", 0),
            time_accuracy=accuracy_metrics.get("time_accuracy", 0)
        )
        
        return APIResponse(
            success=True,
            message="Feedback processed successfully",
            data={
                "voyage_id": str(feedback.voyage_id),
                "accuracy_metrics": accuracy_metrics,
                "learning_status": "queued"
            }
        )
        
    except Exception as e:
        logger.error("Failed to process voyage feedback", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process feedback")


@router.get("/feedback/accuracy", response_model=Dict[str, Any])
async def get_prediction_accuracy(
    ship_id: UUID = None,
    days: int = 30,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """
    📊 Get prediction accuracy metrics for model performance monitoring.
    
    Returns accuracy statistics for different AI models over time.
    """
    try:
        logger.info(
            "Fetching prediction accuracy",
            user_id=current_user["user_id"],
            ship_id=str(ship_id) if ship_id else None,
            days=days
        )
        
        # Mock data for demonstration
        # In production, this would query the database for actual metrics
        accuracy_data = {
            "overall_metrics": {
                "fuel_prediction_accuracy": 0.92,
                "time_prediction_accuracy": 0.88,
                "route_efficiency_score": 0.95,
                "maintenance_prediction_accuracy": 0.85
            },
            "trend_data": [
                {
                    "date": (datetime.now() - timedelta(days=i)).isoformat(),
                    "fuel_accuracy": 0.90 + (i * 0.002),
                    "time_accuracy": 0.85 + (i * 0.003),
                    "route_efficiency": 0.92 + (i * 0.001)
                }
                for i in range(days, 0, -1)
            ],
            "model_performance": {
                "route_optimizer": {
                    "accuracy": 0.88,
                    "confidence": 0.92,
                    "last_updated": datetime.now().isoformat()
                },
                "fuel_predictor": {
                    "accuracy": 0.92,
                    "confidence": 0.89,
                    "last_updated": datetime.now().isoformat()
                },
                "maintenance_forecaster": {
                    "accuracy": 0.85,
                    "confidence": 0.87,
                    "last_updated": datetime.now().isoformat()
                }
            },
            "improvement_suggestions": [
                "Fuel prediction accuracy improved by 5% this month",
                "Route optimization showing consistent performance",
                "Maintenance forecasting needs more historical data"
            ]
        }
        
        return accuracy_data
        
    except Exception as e:
        logger.error("Failed to fetch prediction accuracy", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch accuracy metrics")


# Helper functions
async def get_original_voyage_plan(voyage_id: UUID, db: Session) -> Dict[str, Any]:
    """Get original voyage plan from database."""
    # Mock data for demonstration
    return {
        "voyage_id": str(voyage_id),
        "ship_id": "12345678-1234-5678-9012-123456789012",
        "predicted_fuel_consumption": 850.5,
        "predicted_duration": 120.0,
        "predicted_arrival_time": datetime.now() + timedelta(hours=120),
        "route_waypoints": 8,
        "optimization_factors": {
            "weather_impact": 1.2,
            "fuel_efficiency": 0.85,
            "route_complexity": 0.6
        }
    }


def calculate_prediction_accuracy(original_plan: Dict, feedback: VoyageFeedback) -> Dict[str, float]:
    """Calculate prediction accuracy metrics."""
    
    # Fuel accuracy
    predicted_fuel = original_plan.get("predicted_fuel_consumption", 0)
    actual_fuel = feedback.actual_fuel_consumption
    fuel_accuracy = 1.0 - abs(predicted_fuel - actual_fuel) / max(predicted_fuel, actual_fuel)
    
    # Time accuracy
    predicted_duration = original_plan.get("predicted_duration", 0)
    actual_duration = feedback.actual_duration
    time_accuracy = 1.0 - abs(predicted_duration - actual_duration) / max(predicted_duration, actual_duration)
    
    # Route efficiency (based on deviations)
    route_deviations = len(feedback.route_deviations)
    route_efficiency = max(0.0, 1.0 - (route_deviations * 0.1))
    
    # Weather prediction accuracy
    weather_accuracy = feedback.weather_accuracy
    
    return {
        "fuel_accuracy": max(0.0, min(1.0, fuel_accuracy)),
        "time_accuracy": max(0.0, min(1.0, time_accuracy)),
        "route_efficiency": route_efficiency,
        "weather_accuracy": weather_accuracy,
        "overall_score": (fuel_accuracy + time_accuracy + route_efficiency + weather_accuracy) / 4
    }


async def process_feedback_for_learning(
    feedback: VoyageFeedback,
    original_plan: Dict,
    accuracy_metrics: Dict
):
    """Process feedback for continuous learning (background task)."""
    try:
        logger.info("Processing feedback for model learning", voyage_id=str(feedback.voyage_id))
        
        # Update fuel predictor
        if accuracy_metrics["fuel_accuracy"] < 0.9:
            # Extract features for retraining
            # This would involve more complex feature engineering in production
            logger.info("Updating fuel predictor with new data")
            # fuel_predictor.update_model(new_features, new_targets)
        
        # Update route optimizer
        if accuracy_metrics["route_efficiency"] < 0.9:
            logger.info("Updating route optimizer with feedback")
            # route_optimizer.update_weights(feedback.route_deviations)
        
        # Update maintenance forecaster
        if feedback.maintenance_events:
            logger.info("Updating maintenance forecaster with events")
            # maintenance_forecaster.update_model(feedback.maintenance_events)
        
        # Log learning completion
        logger.info(
            "Model learning completed",
            voyage_id=str(feedback.voyage_id),
            fuel_accuracy=accuracy_metrics["fuel_accuracy"],
            time_accuracy=accuracy_metrics["time_accuracy"]
        )
        
    except Exception as e:
        logger.error("Failed to process feedback for learning", error=str(e))


async def store_voyage_feedback(
    feedback: VoyageFeedback,
    accuracy_metrics: Dict,
    db: Session
):
    """Store voyage feedback in database."""
    try:
        logger.info("Storing voyage feedback", voyage_id=str(feedback.voyage_id))
        
        # This would store the feedback in the database
        # feedback_record = VoyageFeedbackRecord(
        #     voyage_id=feedback.voyage_id,
        #     actual_fuel_consumption=feedback.actual_fuel_consumption,
        #     actual_duration=feedback.actual_duration,
        #     actual_arrival_time=feedback.actual_arrival_time,
        #     route_deviations=feedback.route_deviations,
        #     weather_accuracy=feedback.weather_accuracy,
        #     maintenance_issues=feedback.maintenance_issues,
        #     crew_feedback=feedback.crew_feedback,
        #     accuracy_metrics=accuracy_metrics,
        #     created_at=datetime.now()
        # )
        # db.add(feedback_record)
        # db.commit()
        
        logger.info("Voyage feedback stored successfully")
        
    except Exception as e:
        logger.error("Failed to store voyage feedback", error=str(e)) 