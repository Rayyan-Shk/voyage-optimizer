#!/usr/bin/env python3
"""
Database initialization script.
Creates all tables and adds sample data for testing.
"""

import asyncio
import sys
from uuid import uuid4
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add src to path
sys.path.append('src')

from src.core.config import settings
from src.data.database import Base
from src.data.schemas import Ship, Voyage, FuelLog, MaintenanceEvent, WeatherData, ModelPerformance


def create_tables():
    """Create all database tables."""
    try:
        engine = create_engine(settings.database_url)
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully")
        return engine
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return None


def add_sample_data(engine):
    """Add sample data for testing."""
    try:
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        # Create sample ship
        ship_id = "12345678-1234-5678-9012-123456789012"
        sample_ship = Ship(
            id=ship_id,
            name="SS Enterprise",
            specs={
                "length": 300,
                "width": 40,
                "max_speed": 25,
                "fuel_capacity": 5000,
                "cargo_capacity": 50000,
                "engine_type": "diesel",
                "crew_capacity": 25
            },
            model_version="v1.0"
        )
        
        # Check if ship already exists
        existing_ship = db.query(Ship).filter(Ship.id == ship_id).first()
        if not existing_ship:
            db.add(sample_ship)
            print(f"✅ Added sample ship: {sample_ship.name}")
        else:
            print(f"ℹ️  Ship {ship_id} already exists")
        
        # Create sample fuel log
        sample_fuel_log = FuelLog(
            id=str(uuid4()),
            ship_id=ship_id,
            timestamp=datetime.utcnow(),
            consumption_rate=2.5,
            efficiency_score=0.85,
            weather_conditions={
                "wind_speed": 15,
                "wave_height": 2.5,
                "temperature": 18
            }
        )
        
        # Check if fuel log exists
        existing_fuel_log = db.query(FuelLog).filter(FuelLog.ship_id == ship_id).first()
        if not existing_fuel_log:
            db.add(sample_fuel_log)
            print("✅ Added sample fuel log")
        else:
            print("ℹ️  Fuel log already exists")
        
        # Create sample maintenance event
        sample_maintenance = MaintenanceEvent(
            id=str(uuid4()),
            ship_id=ship_id,
            event_type="routine_inspection",
            maintenance_type="routine",
            component="engine",
            reasoning="Monthly engine inspection scheduled",
            predicted_date=datetime.utcnow() + timedelta(days=30),
            prediction_accuracy=0.92,
            cost=5000.00,
            urgency_score=0.3
        )
        
        # Check if maintenance event exists
        existing_maintenance = db.query(MaintenanceEvent).filter(MaintenanceEvent.ship_id == ship_id).first()
        if not existing_maintenance:
            db.add(sample_maintenance)
            print("✅ Added sample maintenance event")
        else:
            print("ℹ️  Maintenance event already exists")
        
        # Commit all changes
        db.commit()
        db.close()
        print("✅ Sample data added successfully")
        
    except Exception as e:
        print(f"❌ Error adding sample data: {e}")
        if 'db' in locals():
            db.rollback()
            db.close()


def main():
    """Main function to initialize database."""
    print("🚢 Initializing Ship Planning Database...")
    
    # Create tables
    engine = create_tables()
    if not engine:
        sys.exit(1)
    
    # Add sample data
    add_sample_data(engine)
    
    print("🎉 Database initialization completed!")


if __name__ == "__main__":
    main() 