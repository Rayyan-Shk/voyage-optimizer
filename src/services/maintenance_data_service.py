from typing import Dict, List, Optional, Any
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
import structlog

from src.data.schemas import Ship, MaintenanceEvent
from src.services.data_validation_service import data_validator
from src.core.exceptions import DatabaseError, ValidationError

logger = structlog.get_logger()


class MaintenanceDataService:
    """
    Centralized service for maintenance data operations.
    Follows separation of concerns and provides consistent data access.
    """
    
    def __init__(self):
        self.logger = structlog.get_logger(__name__)
    
    async def get_ship_usage_data(self, ship_id: UUID, db: Session) -> Dict[str, Any]:
        """
        Get ship usage data for maintenance forecasting.
        
        Args:
            ship_id: Ship identifier
            db: Database session
            
        Returns:
            Dictionary containing ship usage data
            
        Raises:
            DatabaseError: If database operation fails
            ValidationError: If data validation fails
        """
        try:
            # Get ship from database
            ship = db.query(Ship).filter(Ship.id == ship_id).first()
            
            if not ship:
                raise DatabaseError(f"Ship with ID {ship_id} not found")
            
            # Extract usage data from ship record (data stored in JSONB specs field)
            specs = ship.specs or {}
            usage_data = {
                'total_operating_hours': specs.get('total_operating_hours', 8000),
                'recent_operating_hours': self._calculate_recent_operating_hours(ship),
                'average_speed': specs.get('average_speed', 18),
                'engine_load_avg': specs.get('engine_load_avg', 0.7),
                'fuel_efficiency': specs.get('fuel_efficiency', 0.8),
                'weather_severity_avg': specs.get('weather_severity_avg', 0.5),
                'storm_exposure_hours': specs.get('storm_exposure_hours', 100),
                'rough_sea_percentage': specs.get('rough_sea_percentage', 0.3),
                'ship_age_years': self._calculate_ship_age(ship),
                'condition_score': specs.get('condition_score', 0.8),
            }
            
            # Validate the data
            validated_data = data_validator.validate_ship_usage_data(usage_data)
            
            self.logger.info(
                "Ship usage data retrieved",
                ship_id=str(ship_id),
                total_operating_hours=validated_data['total_operating_hours']
            )
            
            return validated_data
            
        except Exception as e:
            self.logger.error("Failed to get ship usage data", ship_id=str(ship_id), error=str(e))
            raise DatabaseError(f"Failed to get ship usage data: {str(e)}")
    
    async def get_historical_maintenance(self, ship_id: UUID, db: Session, 
                                       limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get historical maintenance data for a ship.
        
        Args:
            ship_id: Ship identifier
            db: Database session
            limit: Maximum number of records to return
            
        Returns:
            List of maintenance event dictionaries
            
        Raises:
            DatabaseError: If database operation fails
            ValidationError: If data validation fails
        """
        try:
            # Query maintenance events
            maintenance_events = db.query(MaintenanceEvent).filter(
                MaintenanceEvent.ship_id == ship_id
            ).filter(
                MaintenanceEvent.actual_date.isnot(None)
            ).order_by(
                desc(MaintenanceEvent.actual_date)
            ).limit(limit).all()
            
            # Convert to dictionaries
            maintenance_history = []
            for event in maintenance_events:
                event_dict = {
                    'date': event.actual_date,
                    'event_type': event.maintenance_type,
                    'component': event.component,
                    'cost': float(event.cost) if event.cost else 0.0,
                    'urgency': float(event.urgency_score) if event.urgency_score else 0.5,
                }
                maintenance_history.append(event_dict)
            
            # Validate the data
            validated_history = data_validator.validate_maintenance_history(maintenance_history)
            
            self.logger.info(
                "Historical maintenance data retrieved",
                ship_id=str(ship_id),
                event_count=len(validated_history)
            )
            
            return validated_history
            
        except Exception as e:
            self.logger.error("Failed to get historical maintenance", ship_id=str(ship_id), error=str(e))
            raise DatabaseError(f"Failed to get historical maintenance: {str(e)}")
    
    async def get_ship_specifications(self, ship_id: UUID, db: Session) -> Dict[str, Any]:
        """
        Get ship specifications for fuel prediction.
        
        Args:
            ship_id: Ship identifier
            db: Database session
            
        Returns:
            Dictionary containing ship specifications
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            # Get ship from database
            ship = db.query(Ship).filter(Ship.id == ship_id).first()
            
            if not ship:
                raise DatabaseError(f"Ship with ID {ship_id} not found")
            
            # Extract specifications (data stored in JSONB specs field)
            specs = ship.specs or {}
            specifications = {
                'displacement': specs.get('displacement', 50000),
                'engine_power': specs.get('engine_power', 15000),
                'max_speed': specs.get('max_speed', 22),
                'cargo_capacity': specs.get('cargo_capacity', 30000),
                'age': self._calculate_ship_age(ship),
                'total_operating_hours': specs.get('total_operating_hours', 8000),
            }
            
            self.logger.info(
                "Ship specifications retrieved",
                ship_id=str(ship_id),
                displacement=specifications['displacement']
            )
            
            return specifications
            
        except Exception as e:
            self.logger.error("Failed to get ship specifications", ship_id=str(ship_id), error=str(e))
            raise DatabaseError(f"Failed to get ship specifications: {str(e)}")
    
    async def store_maintenance_prediction(self, ship_id: UUID, prediction_data: Dict[str, Any], 
                                         db: Session) -> None:
        """
        Store maintenance prediction results.
        
        Args:
            ship_id: Ship identifier
            prediction_data: Prediction results
            db: Database session
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            # Store prediction results for tracking accuracy
            for recommendation in prediction_data.get('recommendations', []):
                maintenance_event = MaintenanceEvent(
                    ship_id=ship_id,
                    event_type='prediction',
                    maintenance_type=recommendation.get('maintenance_type', 'routine'),
                    predicted_date=recommendation.get('recommended_date'),
                    component=recommendation.get('component', 'unknown'),
                    reasoning=recommendation.get('reasoning', ''),
                    urgency_score=recommendation.get('urgency_score', 0.5),
                    cost=recommendation.get('estimated_cost', 0.0),
                )
                db.add(maintenance_event)
            
            db.commit()
            
            self.logger.info(
                "Maintenance prediction stored",
                ship_id=str(ship_id),
                prediction_count=len(prediction_data.get('recommendations', []))
            )
            
        except Exception as e:
            db.rollback()
            self.logger.error("Failed to store maintenance prediction", ship_id=str(ship_id), error=str(e))
            raise DatabaseError(f"Failed to store maintenance prediction: {str(e)}")
    
    def _calculate_recent_operating_hours(self, ship: Ship) -> float:
        """Calculate recent operating hours (last 30 days)."""
        # This would typically query voyage/operation logs
        # For now, return a reasonable estimate
        specs = ship.specs or {}
        total_hours = specs.get('total_operating_hours', 8000)
        return min(200, total_hours * 0.025)  # ~2.5% of total hours as recent
    
    def _calculate_ship_age(self, ship: Ship) -> float:
        """Calculate ship age in years."""
        specs = ship.specs or {}
        built_date = specs.get('built_date')
        if built_date:
            # Convert string to datetime if needed
            if isinstance(built_date, str):
                try:
                    built_date = datetime.fromisoformat(built_date.replace('Z', '+00:00'))
                except ValueError:
                    return 10.0  # Default if date parsing fails
            age = (datetime.now() - built_date).days / 365.25
            return max(0, age)
        return 10.0  # Default age if no build date
    
    async def get_maintenance_statistics(self, ship_id: UUID, db: Session) -> Dict[str, Any]:
        """
        Get maintenance statistics for a ship.
        
        Args:
            ship_id: Ship identifier
            db: Database session
            
        Returns:
            Dictionary containing maintenance statistics
        """
        try:
            # Query maintenance events for statistics
            events = db.query(MaintenanceEvent).filter(
                MaintenanceEvent.ship_id == ship_id
            ).filter(
                MaintenanceEvent.actual_date.isnot(None)
            ).all()
            
            if not events:
                return {
                    'total_events': 0,
                    'average_cost': 0.0,
                    'emergency_ratio': 0.0,
                    'last_maintenance_days': 365,
                }
            
            # Calculate statistics
            total_events = len(events)
            total_cost = sum(float(event.cost) if event.cost else 0.0 for event in events)
            average_cost = total_cost / total_events if total_events > 0 else 0.0
            
            emergency_events = sum(1 for event in events if event.maintenance_type == 'emergency')
            emergency_ratio = emergency_events / total_events if total_events > 0 else 0.0
            
            # Last maintenance
            last_event = max(events, key=lambda x: x.actual_date)
            last_maintenance_days = (datetime.now() - last_event.actual_date).days
            
            statistics = {
                'total_events': total_events,
                'average_cost': average_cost,
                'emergency_ratio': emergency_ratio,
                'last_maintenance_days': last_maintenance_days,
            }
            
            self.logger.info(
                "Maintenance statistics calculated",
                ship_id=str(ship_id),
                **statistics
            )
            
            return statistics
            
        except Exception as e:
            self.logger.error("Failed to get maintenance statistics", ship_id=str(ship_id), error=str(e))
            raise DatabaseError(f"Failed to get maintenance statistics: {str(e)}")


# Global instance
maintenance_data_service = MaintenanceDataService() 