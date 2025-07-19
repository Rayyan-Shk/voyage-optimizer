from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import MetaData, create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from src.core.config import settings

# Database engine with optimized configuration
engine = create_engine(
    settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.debug,
    future=True,
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

# Base class for all models
Base = declarative_base()

# Metadata for migrations
metadata = MetaData()


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[SessionLocal, None]:
    """
    Async context manager for database sessions.
    Ensures proper cleanup and error handling.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()  # Remove await - this is synchronous SQLAlchemy
    except Exception:
        session.rollback()  # Remove await - this is synchronous SQLAlchemy
        raise
    finally:
        session.close()  # Remove await - this is synchronous SQLAlchemy


def get_db():
    """
    Dependency for FastAPI to get database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class DatabaseManager:
    """
    Database connection manager with health checks and reconnection logic.
    """

    def __init__(self):
        self.engine = engine
        self.session_factory = SessionLocal

    async def health_check(self) -> bool:
        """Check database connectivity."""
        try:
            with self.session_factory() as session:
                result = session.execute(text("SELECT 1"))
                result.fetchone()  # Actually fetch the result
                return True
        except Exception as e:
            print(f"Database health check failed: {e}")  # Debug output
            return False

    async def initialize_database(self):
        """Initialize database tables."""
        Base.metadata.create_all(bind=self.engine)

    async def close_connections(self):
        """Close all database connections."""
        self.engine.dispose()


# Global database manager instance
db_manager = DatabaseManager()
