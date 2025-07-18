from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Boolean, Text, 
    ForeignKey, Index, UniqueConstraint, CheckConstraint, DECIMAL
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from uuid import uuid4

from src.data.database import Base


class Ship(Base):
    """Ship table with optimized indexing."""
    __tablename__ = "ships"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    specs = Column(JSONB, nullable=False)
    model_version = Column(String(50), default="v1.0")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    voyages = relationship("Voyage", back_populates="ship", cascade="all, delete-orphan")
    fuel_logs = relationship("FuelLog", back_populates="ship", cascade="all, delete-orphan")
    maintenance_events = relationship("MaintenanceEvent", back_populates="ship", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_ships_name", "name"),
        Index("idx_ships_created_at", "created_at"),
        Index("idx_ships_specs_gin", "specs", postgresql_using="gin"),
    )


class Voyage(Base):
    """Voyage table with event sourcing pattern."""
    __tablename__ = "voyages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    ship_id = Column(UUID(as_uuid=True), ForeignKey("ships.id"), nullable=False)
    status = Column(String(50), default="planned")
    plan_data = Column(JSONB, nullable=False)
    actual_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    ship = relationship("Ship", back_populates="voyages")
    fuel_logs = relationship("FuelLog", back_populates="voyage", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("status IN ('planned', 'in_progress', 'completed', 'cancelled')"),
        Index("idx_voyages_ship_created", "ship_id", "created_at"),
        Index("idx_voyages_status", "status"),
        Index("idx_voyages_completed_at", "completed_at"),
        Index("idx_voyages_plan_data_gin", "plan_data", postgresql_using="gin"),
        Index("idx_voyages_actual_data_gin", "actual_data", postgresql_using="gin"),
    )


class FuelLog(Base):
    """Time-series fuel consumption data."""
    __tablename__ = "fuel_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    ship_id = Column(UUID(as_uuid=True), ForeignKey("ships.id"), nullable=False)
    voyage_id = Column(UUID(as_uuid=True), ForeignKey("voyages.id"), nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    consumption_rate = Column(DECIMAL(10, 4), nullable=False)
    efficiency_score = Column(DECIMAL(5, 4), nullable=True)
    weather_conditions = Column(JSONB, nullable=True)
    
    # Relationships
    ship = relationship("Ship", back_populates="fuel_logs")
    voyage = relationship("Voyage", back_populates="fuel_logs")
    
    # Optimized for time-series queries
    __table_args__ = (
        Index("idx_fuel_logs_ship_timestamp", "ship_id", "timestamp"),
        Index("idx_fuel_logs_voyage_timestamp", "voyage_id", "timestamp"),
        Index("idx_fuel_logs_timestamp", "timestamp"),
        Index("idx_fuel_logs_weather_gin", "weather_conditions", postgresql_using="gin"),
        CheckConstraint("consumption_rate > 0"),
        CheckConstraint("efficiency_score >= 0 AND efficiency_score <= 1"),
    )


class MaintenanceEvent(Base):
    """Maintenance events with prediction accuracy tracking."""
    __tablename__ = "maintenance_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    ship_id = Column(UUID(as_uuid=True), ForeignKey("ships.id"), nullable=False)
    event_type = Column(String(100), nullable=False)
    maintenance_type = Column(String(50), nullable=False)
    predicted_date = Column(DateTime(timezone=True), nullable=True)
    actual_date = Column(DateTime(timezone=True), nullable=True)
    prediction_accuracy = Column(DECIMAL(5, 4), nullable=True)
    cost = Column(DECIMAL(12, 2), nullable=True)
    component = Column(String(200), nullable=False)
    reasoning = Column(Text, nullable=True)
    urgency_score = Column(DECIMAL(3, 2), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    ship = relationship("Ship", back_populates="maintenance_events")
    
    # Constraints and indexes
    __table_args__ = (
        CheckConstraint("maintenance_type IN ('routine', 'preventive', 'emergency', 'overhaul')"),
        CheckConstraint("prediction_accuracy >= 0 AND prediction_accuracy <= 1"),
        CheckConstraint("urgency_score >= 0 AND urgency_score <= 1"),
        CheckConstraint("cost >= 0"),
        Index("idx_maintenance_ship_date", "ship_id", "actual_date"),
        Index("idx_maintenance_predicted_date", "predicted_date"),
        Index("idx_maintenance_type", "maintenance_type"),
        Index("idx_maintenance_component", "component"),
        Index("idx_maintenance_urgency", "urgency_score"),
    )


class ModelPerformance(Base):
    """Model performance tracking and versioning."""
    __tablename__ = "model_performance"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    model_name = Column(String(100), nullable=False)
    version = Column(String(50), nullable=False)
    accuracy_metrics = Column(JSONB, nullable=False)
    training_data_size = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    
    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint("model_name", "version", name="uq_model_version"),
        Index("idx_model_performance_name_version", "model_name", "version"),
        Index("idx_model_performance_created_at", "created_at"),
        Index("idx_model_performance_active", "is_active"),
        Index("idx_model_performance_metrics_gin", "accuracy_metrics", postgresql_using="gin"),
        CheckConstraint("training_data_size > 0"),
    )


class WeatherData(Base):
    """Weather data cache for optimization."""
    __tablename__ = "weather_data"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    location_hash = Column(String(64), nullable=False)  # Hash of lat/lon for indexing
    latitude = Column(DECIMAL(10, 8), nullable=False)
    longitude = Column(DECIMAL(11, 8), nullable=False)
    forecast_data = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    # Optimized for location-based queries
    __table_args__ = (
        Index("idx_weather_location_hash", "location_hash"),
        Index("idx_weather_coordinates", "latitude", "longitude"),
        Index("idx_weather_expires_at", "expires_at"),
        Index("idx_weather_forecast_gin", "forecast_data", postgresql_using="gin"),
        CheckConstraint("latitude >= -90 AND latitude <= 90"),
        CheckConstraint("longitude >= -180 AND longitude <= 180"),
    )


class RouteCache(Base):
    """Pre-computed route optimizations cache."""
    __tablename__ = "route_cache"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    route_hash = Column(String(64), nullable=False, unique=True)
    origin_lat = Column(DECIMAL(10, 8), nullable=False)
    origin_lon = Column(DECIMAL(11, 8), nullable=False)
    destination_lat = Column(DECIMAL(10, 8), nullable=False)
    destination_lon = Column(DECIMAL(11, 8), nullable=False)
    ship_type = Column(String(100), nullable=False)
    route_data = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used = Column(DateTime(timezone=True), server_default=func.now())
    usage_count = Column(Integer, default=1)
    
    # Optimized for route lookups
    __table_args__ = (
        Index("idx_route_cache_hash", "route_hash"),
        Index("idx_route_cache_origin", "origin_lat", "origin_lon"),
        Index("idx_route_cache_destination", "destination_lat", "destination_lon"),
        Index("idx_route_cache_ship_type", "ship_type"),
        Index("idx_route_cache_last_used", "last_used"),
        Index("idx_route_cache_usage_count", "usage_count"),
        CheckConstraint("origin_lat >= -90 AND origin_lat <= 90"),
        CheckConstraint("origin_lon >= -180 AND origin_lon <= 180"),
        CheckConstraint("destination_lat >= -90 AND destination_lat <= 90"),
        CheckConstraint("destination_lon >= -180 AND destination_lon <= 180"),
        CheckConstraint("usage_count > 0"),
    )


# Partitioning helper for large tables (PostgreSQL specific)
class PartitionedTable:
    """Base class for partitioned tables."""
    
    @classmethod
    def create_partition(cls, table_name: str, start_date: str, end_date: str):
        """Create a partition for date range."""
        return f"""
        CREATE TABLE {table_name}_{start_date}_{end_date} 
        PARTITION OF {table_name}
        FOR VALUES FROM ('{start_date}') TO ('{end_date}');
        """ 