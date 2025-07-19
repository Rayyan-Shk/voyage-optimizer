import asyncio
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import httpx
import structlog

from src.core.config import settings
from src.core.exceptions import WeatherDataError
from src.core.models import Coordinates, WeatherCondition

logger = structlog.get_logger()


class WeatherClient:
    """
    Intelligent weather client with caching and error handling.
    Integrates with external weather APIs to provide route-specific forecasts.
    """

    def __init__(self):
        self.base_url = settings.weather_api_url
        self.api_key = settings.weather_api_key
        self.client = httpx.AsyncClient(timeout=30.0)
        self.cache = {}  # Simple in-memory cache
        self.cache_ttl = 3600  # 1 hour

    async def get_weather(self, coordinates: Coordinates) -> Optional[Dict]:
        """Get current weather for specific coordinates."""
        try:
            # Generate cache key
            cache_key = f"weather_{coordinates.latitude}_{coordinates.longitude}"

            # Check cache first
            if cache_key in self.cache:
                cached_data, timestamp = self.cache[cache_key]
                if datetime.now().timestamp() - timestamp < self.cache_ttl:
                    logger.debug("Returning cached weather data", cache_key=cache_key)
                    return cached_data

            # Make API request
            url = f"{self.base_url}/weather"
            params = {
                "lat": coordinates.latitude,
                "lon": coordinates.longitude,
                "appid": self.api_key,
                "units": "metric",
            }

            logger.info(
                "Fetching weather data",
                lat=coordinates.latitude,
                lon=coordinates.longitude,
            )

            response = await self.client.get(url, params=params)
            response.raise_for_status()

            weather_data = response.json()

            # Transform to our format
            transformed_data = self._transform_weather_data(weather_data)

            # Cache the result
            self.cache[cache_key] = (transformed_data, datetime.now().timestamp())

            logger.info("Weather data fetched successfully", cache_key=cache_key)
            return transformed_data

        except httpx.HTTPStatusError as e:
            logger.error(f"Weather API HTTP error: {e.response.status_code}")
            return self._get_fallback_weather(coordinates)

        except httpx.RequestError as e:
            logger.error(f"Weather API request error: {str(e)}")
            return self._get_fallback_weather(coordinates)

        except Exception as e:
            logger.error(f"Weather API error: {str(e)}")
            return self._get_fallback_weather(coordinates)

    async def get_forecast(
        self, coordinates: Coordinates, days: int = 5
    ) -> Optional[Dict]:
        """Get weather forecast for specific coordinates."""
        try:
            cache_key = (
                f"forecast_{coordinates.latitude}_{coordinates.longitude}_{days}"
            )

            # Check cache
            if cache_key in self.cache:
                cached_data, timestamp = self.cache[cache_key]
                if datetime.now().timestamp() - timestamp < self.cache_ttl:
                    return cached_data

            # Make API request
            url = f"{self.base_url}/forecast"
            params = {
                "lat": coordinates.latitude,
                "lon": coordinates.longitude,
                "appid": self.api_key,
                "units": "metric",
                "cnt": days * 8,  # 8 forecasts per day (3-hour intervals)
            }

            logger.info(
                "Fetching weather forecast",
                lat=coordinates.latitude,
                lon=coordinates.longitude,
                days=days,
            )

            response = await self.client.get(url, params=params)
            response.raise_for_status()

            forecast_data = response.json()

            # Transform to our format
            transformed_data = self._transform_forecast_data(forecast_data)

            # Cache the result
            self.cache[cache_key] = (transformed_data, datetime.now().timestamp())

            return transformed_data

        except Exception as e:
            logger.error(f"Weather forecast error: {str(e)}")
            return self._get_fallback_forecast(coordinates, days)

    async def get_route_weather(
        self, origin: Coordinates, destination: Coordinates
    ) -> Optional[Dict]:
        """Get weather conditions along a route."""
        try:
            logger.info(
                "Fetching route weather",
                origin_lat=origin.latitude,
                origin_lon=origin.longitude,
                dest_lat=destination.latitude,
                dest_lon=destination.longitude,
            )

            # Generate waypoints along the route
            waypoints = self._generate_route_waypoints(origin, destination)

            # Get weather for each waypoint
            weather_tasks = [self.get_weather(wp) for wp in waypoints]
            weather_results = await asyncio.gather(
                *weather_tasks, return_exceptions=True
            )

            # Filter out exceptions and process results
            valid_weather = [w for w in weather_results if isinstance(w, dict)]

            if not valid_weather:
                logger.warning("No valid weather data for route")
                return self._get_fallback_route_weather(origin, destination)

            # Aggregate weather data
            aggregated_weather = self._aggregate_route_weather(valid_weather)

            logger.info(
                "Route weather fetched successfully", waypoints_count=len(waypoints)
            )
            return aggregated_weather

        except Exception as e:
            logger.error(f"Route weather error: {str(e)}")
            return self._get_fallback_route_weather(origin, destination)

    def _transform_weather_data(self, raw_data: Dict) -> Dict:
        """Transform external API data to our format."""
        try:
            main = raw_data.get("main", {})
            weather = raw_data.get("weather", [{}])[0]
            wind = raw_data.get("wind", {})

            return {
                "temperature": main.get("temp", 20),
                "humidity": main.get("humidity", 60),
                "pressure": main.get("pressure", 1013),
                "wind_speed": wind.get("speed", 10),
                "wind_direction": wind.get("deg", 180),
                "weather_description": weather.get("description", "clear"),
                "visibility": raw_data.get("visibility", 10000) / 1000,  # Convert to km
                "wave_height": 2.0,  # Default value (would need marine weather API)
                "precipitation": 0.0,  # Default value
                "weather_severity": self._calculate_weather_severity(raw_data),
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Weather data transformation error: {str(e)}")
            return self._get_default_weather()

    def _transform_forecast_data(self, raw_data: Dict) -> Dict:
        """Transform forecast data to our format."""
        try:
            forecast_list = raw_data.get("list", [])
            conditions = []

            for item in forecast_list:
                main = item.get("main", {})
                weather = item.get("weather", [{}])[0]
                wind = item.get("wind", {})

                condition = {
                    "datetime": item.get("dt_txt", ""),
                    "temperature": main.get("temp", 20),
                    "wind_speed": wind.get("speed", 10),
                    "wind_direction": wind.get("deg", 180),
                    "wave_height": 2.0,  # Default
                    "visibility": 10.0,  # Default
                    "precipitation": item.get("rain", {}).get("3h", 0),
                    "weather_description": weather.get("description", "clear"),
                }
                conditions.append(condition)

            return {
                "location": {
                    "latitude": raw_data.get("city", {}).get("coord", {}).get("lat", 0),
                    "longitude": raw_data.get("city", {})
                    .get("coord", {})
                    .get("lon", 0),
                },
                "conditions": conditions,
                "forecast_duration_hours": len(conditions) * 3,
            }

        except Exception as e:
            logger.error(f"Forecast data transformation error: {str(e)}")
            return {"conditions": [], "forecast_duration_hours": 0}

    def _generate_route_waypoints(
        self, origin: Coordinates, destination: Coordinates, num_points: int = 5
    ) -> List[Coordinates]:
        """Generate waypoints along a route for weather sampling."""
        waypoints = []

        for i in range(num_points):
            ratio = i / (num_points - 1) if num_points > 1 else 0

            lat = origin.latitude + (destination.latitude - origin.latitude) * ratio
            lon = origin.longitude + (destination.longitude - origin.longitude) * ratio

            waypoints.append(Coordinates(latitude=lat, longitude=lon))

        return waypoints

    def _aggregate_route_weather(self, weather_data: List[Dict]) -> Dict:
        """Aggregate weather data from multiple waypoints."""
        if not weather_data:
            return self._get_default_weather()

        # Calculate averages
        avg_temp = sum(w.get("temperature", 20) for w in weather_data) / len(
            weather_data
        )
        avg_wind_speed = sum(w.get("wind_speed", 10) for w in weather_data) / len(
            weather_data
        )
        avg_wave_height = sum(w.get("wave_height", 2) for w in weather_data) / len(
            weather_data
        )
        avg_visibility = sum(w.get("visibility", 10) for w in weather_data) / len(
            weather_data
        )
        max_precipitation = max(w.get("precipitation", 0) for w in weather_data)

        # Calculate overall weather severity
        severity_scores = [w.get("weather_severity", 0.5) for w in weather_data]
        avg_severity = sum(severity_scores) / len(severity_scores)

        return {
            "temperature": avg_temp,
            "wind_speed": avg_wind_speed,
            "wave_height": avg_wave_height,
            "visibility": avg_visibility,
            "precipitation": max_precipitation,
            "weather_severity": avg_severity,
            "wind_direction": weather_data[0].get(
                "wind_direction", 180
            ),  # Use first waypoint
            "route_weather_variation": max(severity_scores) - min(severity_scores),
            "timestamp": datetime.now().isoformat(),
        }

    def _calculate_weather_severity(self, weather_data: Dict) -> float:
        """Calculate weather severity score (0-1)."""
        try:
            main = weather_data.get("main", {})
            wind = weather_data.get("wind", {})
            weather = weather_data.get("weather", [{}])[0]

            # Wind factor
            wind_speed = wind.get("speed", 0)
            wind_factor = min(1.0, wind_speed / 25)  # Normalize to 25 m/s max

            # Weather condition factor
            weather_main = weather.get("main", "").lower()
            condition_factor = 0.0
            if weather_main in ["thunderstorm", "snow"]:
                condition_factor = 1.0
            elif weather_main in ["rain", "drizzle"]:
                condition_factor = 0.6
            elif weather_main in ["mist", "fog"]:
                condition_factor = 0.4
            elif weather_main in ["clouds"]:
                condition_factor = 0.2

            # Visibility factor
            visibility = weather_data.get("visibility", 10000)
            visibility_factor = max(0.0, 1.0 - visibility / 10000)

            # Combined severity
            severity = (
                wind_factor * 0.4 + condition_factor * 0.4 + visibility_factor * 0.2
            )

            return min(1.0, severity)

        except Exception:
            return 0.5  # Default moderate severity

    def _get_fallback_weather(self, coordinates: Coordinates) -> Dict:
        """Get fallback weather data when API fails."""
        logger.warning(
            "Using fallback weather data",
            lat=coordinates.latitude,
            lon=coordinates.longitude,
        )
        return self._get_default_weather()

    def _get_fallback_forecast(self, coordinates: Coordinates, days: int) -> Dict:
        """Get fallback forecast data when API fails."""
        logger.warning("Using fallback forecast data")
        conditions = []

        for i in range(days * 8):  # 8 forecasts per day
            future_time = datetime.now() + timedelta(hours=i * 3)
            conditions.append(
                {
                    "datetime": future_time.isoformat(),
                    "temperature": 20,
                    "wind_speed": 10,
                    "wind_direction": 180,
                    "wave_height": 2.0,
                    "visibility": 10.0,
                    "precipitation": 0.0,
                    "weather_description": "clear",
                }
            )

        return {
            "location": {
                "latitude": coordinates.latitude,
                "longitude": coordinates.longitude,
            },
            "conditions": conditions,
            "forecast_duration_hours": days * 24,
        }

    def _get_fallback_route_weather(
        self, origin: Coordinates, destination: Coordinates
    ) -> Dict:
        """Get fallback route weather data."""
        logger.warning("Using fallback route weather data")
        return self._get_default_weather()

    def _get_default_weather(self) -> Dict:
        """Get default weather conditions."""
        return {
            "temperature": 20,
            "humidity": 60,
            "pressure": 1013,
            "wind_speed": 10,
            "wind_direction": 180,
            "weather_description": "clear",
            "visibility": 10.0,
            "wave_height": 2.0,
            "precipitation": 0.0,
            "weather_severity": 0.3,
            "timestamp": datetime.now().isoformat(),
        }

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
