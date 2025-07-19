from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Smart configuration management with validation and type safety."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        protected_namespaces=(),
    )

    # Database
    database_url: str = Field(..., description="PostgreSQL connection URL")
    database_pool_size: int = Field(20, description="Database connection pool size")
    database_max_overflow: int = Field(30, description="Max overflow connections")

    # Redis
    redis_url: str = Field(
        "redis://localhost:6379/0", description="Redis connection URL"
    )
    redis_cache_ttl: int = Field(3600, description="Default cache TTL in seconds")
    redis_weather_ttl: int = Field(21600, description="Weather cache TTL in seconds")

    # External APIs
    weather_api_key: str = Field(..., description="OpenWeatherMap API key")
    weather_api_url: str = Field(
        "https://api.openweathermap.org/data/2.5", description="Weather API base URL"
    )

    # ML Models
    model_retrain_threshold: float = Field(
        0.85, description="Accuracy threshold for retraining"
    )
    model_cache_ttl: int = Field(1800, description="Model prediction cache TTL")
    model_version: str = Field("v1.0", description="Current model version")
    enable_continuous_learning: bool = Field(
        True, description="Enable continuous learning"
    )

    # Performance
    max_concurrent_requests: int = Field(100, description="Max concurrent API requests")
    api_timeout: int = Field(30, description="API request timeout in seconds")
    cache_default_ttl: int = Field(1800, description="Default cache TTL")

    # Logging
    log_level: str = Field("INFO", description="Logging level")
    log_format: str = Field("json", description="Log format (json/text)")

    # Security
    secret_key: str = Field(..., description="Secret key for JWT tokens")
    api_version: str = Field("v1", description="API version")

    # Development
    debug: bool = Field(False, description="Debug mode")
    environment: str = Field("development", description="Environment name")

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    @property
    def database_config(self) -> dict:
        """Get database configuration."""
        return {
            "url": self.database_url,
            "pool_size": self.database_pool_size,
            "max_overflow": self.database_max_overflow,
        }

    @property
    def redis_config(self) -> dict:
        """Get Redis configuration."""
        return {
            "url": self.redis_url,
            "cache_ttl": self.redis_cache_ttl,
            "weather_ttl": self.redis_weather_ttl,
        }


# Global settings instance
settings = Settings()
