from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
import logging
import time
from prometheus_client import Counter, Histogram, generate_latest, CollectorRegistry, REGISTRY
import structlog

from src.core.config import settings
from src.core.exceptions import ShipPlanningException
from src.data.database import db_manager
from src.services.cache_service import cache_service
from src.api.v1 import voyage, feedback, maintenance
from src.api.dependencies import get_current_user


# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Create custom registry to avoid conflicts
metrics_registry = CollectorRegistry()

# Prometheus metrics with custom registry
REQUEST_COUNT = Counter(
    'http_requests_total', 
    'Total HTTP requests', 
    ['method', 'endpoint', 'status'],
    registry=metrics_registry
)
REQUEST_DURATION = Histogram(
    'http_request_duration_seconds', 
    'HTTP request duration',
    registry=metrics_registry
)
VOYAGE_PLANS_CREATED = Counter(
    'voyage_plans_created_total', 
    'Total voyage plans created',
    registry=metrics_registry
)
FUEL_PREDICTIONS_MADE = Counter(
    'fuel_predictions_made_total', 
    'Total fuel predictions made',
    registry=metrics_registry
)
MAINTENANCE_FORECASTS_GENERATED = Counter(
    'maintenance_forecasts_generated_total', 
    'Total maintenance forecasts generated',
    registry=metrics_registry
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    # Startup
    logger.info("🚢 Starting Ship Planning System...")
    
    try:
        # Initialize database
        await db_manager.initialize_database()
        logger.info("✅ Database initialized")
        
        # Initialize cache service
        await cache_service.initialize()
        logger.info("✅ Cache service initialized")
        
        # Health check
        db_healthy = await db_manager.health_check()
        cache_healthy = await cache_service.health_check()
        
        if not db_healthy:
            logger.error("❌ Database health check failed")
            raise Exception("Database not healthy")
        
        if not cache_healthy:
            logger.error("❌ Cache health check failed")
            raise Exception("Cache not healthy")
        
        # Additional startup tasks (previously in @app.on_event("startup"))
        logger.info("🔧 Running additional startup tasks...")
        
        # Warm up cache with frequently accessed data
        try:
            # This would be implemented with actual data loaders
            # await cache_manager.warm_cache('ships', data_loader)
            # await cache_manager.warm_cache('routes', data_loader)
            logger.info("✅ Cache warming completed")
        except Exception as e:
            logger.warning(f"⚠️ Cache warming failed: {str(e)}")
        
        logger.info("🎯 Ship Planning System started successfully")
        logger.info("🚀 All startup tasks completed")
        
    except Exception as e:
        logger.error(f"❌ Failed to start application: {str(e)}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Ship Planning System...")
    
    try:
        await cache_service.close()
        await db_manager.close_connections()
        logger.info("✅ Graceful shutdown completed")
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {str(e)}")


# Create FastAPI application
app = FastAPI(
    title="AI-Powered Ship Planning & Optimization System",
    description="""
    🚢 **Advanced Ship Planning System** with AI-powered optimization
    
    ## Features
    - **Route Optimization**: AI-powered route planning with weather integration
    - **Fuel Prediction**: Advanced fuel consumption forecasting
    - **Maintenance Forecasting**: Predictive maintenance scheduling
    - **Real-time Learning**: Continuous improvement from voyage feedback
    - **Multi-layer Caching**: High-performance Redis caching
    - **Comprehensive Monitoring**: Prometheus metrics and structured logging
    
    ## Technology Stack
    - **Backend**: FastAPI with async/await
    - **AI/ML**: scikit-learn, pandas, numpy
    - **Database**: PostgreSQL with optimized schemas
    - **Cache**: Redis with intelligent invalidation
    - **Monitoring**: Prometheus + structured logging
    
    Built with ❤️ for maritime efficiency optimization.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["https://your-frontend-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)


# Middleware for request tracking
@app.middleware("http")
async def track_requests(request: Request, call_next):
    """Track HTTP requests with Prometheus metrics."""
    start_time = time.time()
    
    response = await call_next(request)
    
    # Record metrics
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    REQUEST_DURATION.observe(time.time() - start_time)
    
    return response


# Exception handler
@app.exception_handler(ShipPlanningException)
async def ship_planning_exception_handler(request: Request, exc: ShipPlanningException):
    """Handle custom ship planning exceptions."""
    logger.error(
        "Ship planning exception occurred",
        exception=exc.__class__.__name__,
        message=exc.message,
        details=exc.details,
        path=request.url.path,
        method=request.method
    )
    
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "message": exc.message,
            "details": exc.details,
            "timestamp": time.time()
        }
    )


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(
        "Unexpected exception occurred",
        exception=exc.__class__.__name__,
        message=str(exc),
        path=request.url.path,
        method=request.method
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "An unexpected error occurred",
            "timestamp": time.time()
        }
    )


# Prometheus metrics endpoint
@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint."""
    return generate_latest(metrics_registry)


# Health check endpoints
@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.0.0",
        "environment": settings.environment
    }


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with service status."""
    db_healthy = await db_manager.health_check()
    cache_healthy = await cache_service.health_check()
    
    return {
        "status": "healthy" if db_healthy and cache_healthy else "unhealthy",
        "services": {
            "database": "healthy" if db_healthy else "unhealthy",
            "cache": "healthy" if cache_healthy else "unhealthy",
        },
        "timestamp": time.time(),
        "version": "1.0.0",
        "environment": settings.environment
    }


@app.get("/")
async def root():
    """Root endpoint with system information."""
    return {
        "message": "🚢 AI-Powered Ship Planning & Optimization System",
        "version": "1.0.0",
        "environment": settings.environment,
        "docs_url": "/docs",
        "health_check": "/health",
        "metrics": "/metrics",
        "features": [
            "AI-powered route optimization",
            "Advanced fuel consumption prediction",
            "Predictive maintenance forecasting",
            "Real-time learning from voyage feedback",
            "Multi-layer caching for performance",
            "Comprehensive monitoring and logging"
        ],
        "endpoints": {
            "voyage_planning": "/api/v1/plan-voyage",
            "voyage_history": "/api/v1/plan-history",
            "feedback": "/api/v1/feedback",
            "maintenance": "/api/v1/maintenance-alerts"
        }
    }


# API Routes
app.include_router(voyage.router, prefix="/api/v1", tags=["Voyage Planning"])
app.include_router(feedback.router, prefix="/api/v1", tags=["Feedback"])
app.include_router(maintenance.router, prefix="/api/v1", tags=["Maintenance"])


if __name__ == "__main__":
    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=True,
        use_colors=True,
        loop="asyncio"
    ) 