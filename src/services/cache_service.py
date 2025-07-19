import hashlib
import json
from typing import Any, Dict, Optional

import redis.asyncio as redis

from src.core.config import settings
from src.core.exceptions import CacheError


class CacheService:
    """
    Intelligent multi-layer caching service with Redis.
    Implements smart invalidation and performance optimization.
    """

    def __init__(self):
        self.redis_client = None
        self.cache_layers = {
            "routes": settings.redis_cache_ttl * 24,  # 24 hours
            "weather": settings.redis_weather_ttl,  # 6 hours
            "predictions": settings.redis_cache_ttl,  # 1 hour
            "ship_specs": settings.redis_cache_ttl * 7,  # 7 days
            "models": settings.model_cache_ttl,  # 30 minutes
        }
        self.key_prefixes = {
            "route": "route:",
            "weather": "weather:",
            "fuel_prediction": "fuel:",
            "maintenance": "maintenance:",
            "ship": "ship:",
            "model": "model:",
        }

    async def initialize(self):
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                retry_on_timeout=True,
                health_check_interval=30,
            )
            await self.redis_client.ping()
        except Exception as e:
            raise CacheError(f"Failed to connect to Redis: {str(e)}")

    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()

    def _generate_key(self, prefix: str, identifier: str) -> str:
        """Generate cache key with prefix."""
        return f"{self.key_prefixes[prefix]}{identifier}"

    def _hash_object(self, obj: Any) -> str:
        """Generate hash for complex objects."""
        if isinstance(obj, dict):
            sorted_str = json.dumps(obj, sort_keys=True)
        else:
            sorted_str = str(obj)
        return hashlib.md5(sorted_str.encode()).hexdigest()

    async def get(self, key: str, prefix: str = None) -> Optional[Any]:
        """Get value from cache."""
        try:
            if prefix:
                key = self._generate_key(prefix, key)

            cached_value = await self.redis_client.get(key)
            if cached_value:
                return json.loads(cached_value)
            return None
        except Exception as e:
            raise CacheError(f"Failed to get cache value: {str(e)}")

    async def set(
        self, key: str, value: Any, ttl: Optional[int] = None, prefix: str = None
    ) -> bool:
        """Set value in cache with TTL."""
        try:
            if prefix:
                key = self._generate_key(prefix, key)
                ttl = ttl or self.cache_layers.get(prefix, settings.cache_default_ttl)

            serialized_value = json.dumps(value, default=str)

            if ttl:
                await self.redis_client.setex(key, ttl, serialized_value)
            else:
                await self.redis_client.set(key, serialized_value)

            return True
        except Exception as e:
            raise CacheError(f"Failed to set cache value: {str(e)}")

    async def delete(self, key: str, prefix: str = None) -> bool:
        """Delete value from cache."""
        try:
            if prefix:
                key = self._generate_key(prefix, key)

            result = await self.redis_client.delete(key)
            return result > 0
        except Exception as e:
            raise CacheError(f"Failed to delete cache value: {str(e)}")

    async def get_or_compute(
        self, key: str, compute_func, ttl: Optional[int] = None, prefix: str = None
    ) -> Any:
        """Get from cache or compute and cache the result."""
        try:
            # Try to get from cache first
            cached_value = await self.get(key, prefix)
            if cached_value is not None:
                return cached_value

            # Compute the value
            computed_value = (
                await compute_func() if callable(compute_func) else compute_func
            )

            # Cache the computed value
            await self.set(key, computed_value, ttl, prefix)

            return computed_value
        except Exception as e:
            raise CacheError(f"Failed to get or compute cache value: {str(e)}")

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching a pattern."""
        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                return await self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            raise CacheError(f"Failed to invalidate cache pattern: {str(e)}")

    async def cache_route_optimization(
        self, route_params: Dict, optimization_result: Dict
    ) -> str:
        """Cache route optimization result."""
        cache_key = self._hash_object(route_params)
        await self.set(cache_key, optimization_result, prefix="route")
        return cache_key

    async def get_cached_route(self, route_params: Dict) -> Optional[Dict]:
        """Get cached route optimization."""
        cache_key = self._hash_object(route_params)
        return await self.get(cache_key, prefix="route")

    async def cache_weather_data(self, location: Dict, weather_data: Dict) -> None:
        """Cache weather data for location."""
        location_key = f"{location['latitude']},{location['longitude']}"
        await self.set(location_key, weather_data, prefix="weather")

    async def get_cached_weather(self, location: Dict) -> Optional[Dict]:
        """Get cached weather data."""
        location_key = f"{location['latitude']},{location['longitude']}"
        return await self.get(location_key, prefix="weather")

    async def cache_fuel_prediction(
        self, prediction_params: Dict, prediction: Dict
    ) -> None:
        """Cache fuel prediction result."""
        cache_key = self._hash_object(prediction_params)
        await self.set(cache_key, prediction, prefix="fuel_prediction")

    async def get_cached_fuel_prediction(
        self, prediction_params: Dict
    ) -> Optional[Dict]:
        """Get cached fuel prediction."""
        cache_key = self._hash_object(prediction_params)
        return await self.get(cache_key, prefix="fuel_prediction")

    async def cache_maintenance_forecast(self, ship_id: str, forecast: Dict) -> None:
        """Cache maintenance forecast for ship."""
        await self.set(ship_id, forecast, prefix="maintenance")

    async def get_cached_maintenance_forecast(self, ship_id: str) -> Optional[Dict]:
        """Get cached maintenance forecast."""
        return await self.get(ship_id, prefix="maintenance")

    async def invalidate_ship_cache(self, ship_id: str) -> None:
        """Invalidate all cache entries for a ship."""
        patterns = [
            f"{self.key_prefixes['route']}*{ship_id}*",
            f"{self.key_prefixes['fuel_prediction']}*{ship_id}*",
            f"{self.key_prefixes['maintenance']}{ship_id}",
            f"{self.key_prefixes['ship']}{ship_id}",
        ]

        for pattern in patterns:
            await self.invalidate_pattern(pattern)

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            info = await self.redis_client.info()
            return {
                "used_memory": info.get("used_memory_human", "N/A"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(
                    info.get("keyspace_hits", 0), info.get("keyspace_misses", 0)
                ),
            }
        except Exception as e:
            raise CacheError(f"Failed to get cache stats: {str(e)}")

    def _calculate_hit_rate(self, hits: int, misses: int) -> float:
        """Calculate cache hit rate."""
        total = hits + misses
        return (hits / total * 100) if total > 0 else 0.0

    async def health_check(self) -> bool:
        """Check if Redis is healthy."""
        try:
            await self.redis_client.ping()
            return True
        except Exception:
            return False


class SmartCacheManager:
    """
    Advanced cache manager with intelligent invalidation and warming.
    """

    def __init__(self, cache_service: CacheService):
        self.cache = cache_service
        self.warming_tasks = {}

    async def warm_cache(self, cache_type: str, data_loader_func) -> None:
        """Warm up cache with frequently accessed data."""
        try:
            if cache_type == "routes":
                await self._warm_popular_routes(data_loader_func)
            elif cache_type == "weather":
                await self._warm_weather_data(data_loader_func)
            elif cache_type == "ships":
                await self._warm_ship_data(data_loader_func)
        except Exception as e:
            raise CacheError(f"Failed to warm cache: {str(e)}")

    async def _warm_popular_routes(self, data_loader_func) -> None:
        """Warm cache with popular routes."""
        popular_routes = await data_loader_func("popular_routes")
        for route in popular_routes:
            await self.cache.cache_route_optimization(route["params"], route["result"])

    async def _warm_weather_data(self, data_loader_func) -> None:
        """Warm cache with current weather data."""
        weather_locations = await data_loader_func("weather_locations")
        for location in weather_locations:
            weather_data = await data_loader_func("weather", location)
            await self.cache.cache_weather_data(location, weather_data)

    async def _warm_ship_data(self, data_loader_func) -> None:
        """Warm cache with ship specifications."""
        ships = await data_loader_func("ships")
        for ship in ships:
            await self.cache.set(ship["id"], ship, prefix="ship")

    async def invalidate_related_cache(self, event_type: str, entity_id: str) -> None:
        """Intelligently invalidate related cache entries."""
        if event_type == "voyage_completed":
            await self.cache.invalidate_ship_cache(entity_id)
        elif event_type == "weather_updated":
            await self.cache.invalidate_pattern(
                f"{self.cache.key_prefixes['weather']}*"
            )
        elif event_type == "model_updated":
            await self.cache.invalidate_pattern(f"{self.cache.key_prefixes['model']}*")
            await self.cache.invalidate_pattern(
                f"{self.cache.key_prefixes['predictions']}*"
            )


# Global cache service instance
cache_service = CacheService()
cache_manager = SmartCacheManager(cache_service)
