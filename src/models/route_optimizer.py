import heapq
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler

from src.core.exceptions import InsufficientDataError, RouteOptimizationError
from src.core.models import Coordinates, RouteOptimization, Waypoint, WeatherCondition


@dataclass
class RouteNode:
    """Node in the route graph."""

    coordinates: Coordinates
    port_name: str
    port_type: str  # 'major', 'minor', 'waypoint'
    services: List[str]


@dataclass
class RouteEdge:
    """Edge in the route graph with dynamic weights."""

    start: RouteNode
    end: RouteNode
    base_distance: float
    base_time: float
    weight: float
    weather_factor: float = 1.0
    traffic_factor: float = 1.0


class MaritimeGraph:
    """Maritime route graph with intelligent path finding."""

    def __init__(self):
        self.nodes: Dict[str, RouteNode] = {}
        self.edges: Dict[str, List[RouteEdge]] = {}
        self.major_ports = self._load_major_ports()
        self._build_graph()

    def _load_major_ports(self) -> List[Dict]:
        """Load major ports data (simplified for demo)."""
        return [
            {"name": "Shanghai", "lat": 31.2304, "lon": 121.4737, "type": "major"},
            {"name": "Singapore", "lat": 1.2966, "lon": 103.7764, "type": "major"},
            {"name": "Rotterdam", "lat": 51.9244, "lon": 4.4777, "type": "major"},
            {"name": "Los Angeles", "lat": 33.7701, "lon": -118.1937, "type": "major"},
            {"name": "Hamburg", "lat": 53.5511, "lon": 9.9937, "type": "major"},
            {"name": "Dubai", "lat": 25.2048, "lon": 55.2708, "type": "major"},
            {"name": "Hong Kong", "lat": 22.3193, "lon": 114.1694, "type": "major"},
            {"name": "Busan", "lat": 35.1796, "lon": 129.0756, "type": "major"},
        ]

    def _build_graph(self):
        """Build the maritime route graph."""
        # Add major ports as nodes
        for port in self.major_ports:
            node = RouteNode(
                coordinates=Coordinates(latitude=port["lat"], longitude=port["lon"]),
                port_name=port["name"],
                port_type=port["type"],
                services=["fuel", "maintenance", "cargo"],
            )
            self.nodes[port["name"]] = node

        # Connect all major ports (simplified - in reality, use shipping lanes)
        for port1 in self.major_ports:
            for port2 in self.major_ports:
                if port1["name"] != port2["name"]:
                    distance = self._calculate_distance(
                        port1["lat"], port1["lon"], port2["lat"], port2["lon"]
                    )

                    edge = RouteEdge(
                        start=self.nodes[port1["name"]],
                        end=self.nodes[port2["name"]],
                        base_distance=distance,
                        base_time=distance / 20,  # Assume 20 knots average speed
                        weight=distance,
                    )

                    if port1["name"] not in self.edges:
                        self.edges[port1["name"]] = []
                    self.edges[port1["name"]].append(edge)

    def _calculate_distance(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """Calculate great circle distance between two points."""
        R = 3440.065  # Earth's radius in nautical miles

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))

        return R * c

    def find_nearest_port(self, coordinates: Coordinates) -> str:
        """Find the nearest major port to given coordinates."""
        min_distance = float("inf")
        nearest_port = None

        for port_name, node in self.nodes.items():
            distance = self._calculate_distance(
                coordinates.latitude,
                coordinates.longitude,
                node.coordinates.latitude,
                node.coordinates.longitude,
            )
            if distance < min_distance:
                min_distance = distance
                nearest_port = port_name

        return nearest_port

    def get_neighbors(self, node_name: str) -> List[RouteEdge]:
        """Get neighboring nodes for a given node."""
        return self.edges.get(node_name, [])


class RouteOptimizer:
    """
    Intelligent route optimizer using A* algorithm with ML-enhanced edge weights.
    """

    def __init__(self):
        self.graph = MaritimeGraph()
        self.weather_impact_model = None
        self.fuel_efficiency_model = None
        self.scaler = StandardScaler()
        self._initialize_models()

    def _initialize_models(self):
        """Initialize ML models for route optimization."""
        # These would be trained on historical data
        self.weather_impact_model = GradientBoostingRegressor(
            n_estimators=100, learning_rate=0.1, max_depth=6, random_state=42
        )

        self.fuel_efficiency_model = GradientBoostingRegressor(
            n_estimators=100, learning_rate=0.1, max_depth=6, random_state=42
        )

        # Initialize with dummy data (in production, load from database)
        self._train_dummy_models()

    def _train_dummy_models(self):
        """Train models with dummy data for demonstration."""
        # Generate synthetic training data
        np.random.seed(42)
        n_samples = 1000

        # Features: wind_speed, wave_height, temperature, distance
        X = np.random.rand(n_samples, 4)
        X[:, 0] *= 30  # wind_speed (0-30 m/s)
        X[:, 1] *= 10  # wave_height (0-10 m)
        X[:, 2] = X[:, 2] * 40 - 10  # temperature (-10 to 30°C)
        X[:, 3] *= 5000  # distance (0-5000 nm)

        # Synthetic weather impact (higher values = more impact)
        y_weather = (
            X[:, 0] * 0.1
            + X[:, 1] * 0.2
            + np.abs(X[:, 2] - 15) * 0.05
            + np.random.normal(0, 0.1, n_samples)
        )

        # Synthetic fuel efficiency (lower values = better efficiency)
        y_fuel = (
            X[:, 0] * 0.05
            + X[:, 1] * 0.1
            + X[:, 3] * 0.0001
            + np.random.normal(0, 0.05, n_samples)
        )

        X_scaled = self.scaler.fit_transform(X)

        self.weather_impact_model.fit(X_scaled, y_weather)
        self.fuel_efficiency_model.fit(X_scaled, y_fuel)

    def optimize_route(
        self,
        origin: Coordinates,
        destination: Coordinates,
        ship_specs: Dict,
        weather_data: Optional[Dict] = None,
        optimization_preferences: Dict = None,
    ) -> RouteOptimization:
        """
        Optimize route using A* algorithm with ML-enhanced weights.
        """
        try:
            # Find nearest ports to origin and destination
            origin_port = self.graph.find_nearest_port(origin)
            destination_port = self.graph.find_nearest_port(destination)

            if not origin_port or not destination_port:
                raise RouteOptimizationError("Could not find suitable ports for route")

            # Update edge weights based on current conditions
            self._update_edge_weights(
                ship_specs, weather_data, optimization_preferences
            )

            # Find optimal path using A*
            path = self._astar_search(origin_port, destination_port)

            if not path:
                raise RouteOptimizationError("No viable route found")

            # Generate waypoints with timing and speed optimization
            waypoints = self._generate_waypoints(
                path, origin, destination, ship_specs, weather_data
            )

            # Calculate route metrics
            total_distance = sum(edge.base_distance for edge in path)
            estimated_duration = sum(edge.base_time for edge in path)

            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(path, weather_data)

            return RouteOptimization(
                waypoints=waypoints,
                total_distance=total_distance,
                estimated_duration=estimated_duration,
                confidence_score=confidence_score,
                optimization_factors={
                    "weather_impact": np.mean([edge.weather_factor for edge in path]),
                    "fuel_efficiency": self._calculate_fuel_efficiency(
                        path, ship_specs
                    ),
                    "route_complexity": len(path) / 10.0,  # Normalized complexity
                },
            )

        except Exception as e:
            raise RouteOptimizationError(f"Route optimization failed: {str(e)}")

    def _update_edge_weights(
        self,
        ship_specs: Dict,
        weather_data: Optional[Dict],
        optimization_preferences: Optional[Dict],
    ):
        """Update edge weights based on current conditions."""
        if not optimization_preferences:
            optimization_preferences = {"time": 0.4, "fuel": 0.4, "safety": 0.2}

        for node_name, edges in self.graph.edges.items():
            for edge in edges:
                # Base weight is distance
                base_weight = edge.base_distance

                # Apply weather impact
                if weather_data:
                    weather_factor = self._calculate_weather_impact(edge, weather_data)
                    edge.weather_factor = weather_factor
                else:
                    weather_factor = 1.0

                # Apply fuel efficiency factor
                fuel_factor = self._calculate_fuel_efficiency_factor(edge, ship_specs)

                # Apply safety factor (simplified)
                safety_factor = 1.0  # Could be enhanced with piracy data, etc.

                # Combine factors based on preferences
                edge.weight = (
                    base_weight
                    * (
                        optimization_preferences.get("time", 0.4) * 1.0
                        + optimization_preferences.get("fuel", 0.4) * fuel_factor
                        + optimization_preferences.get("safety", 0.2) * safety_factor
                    )
                    * weather_factor
                )

    def _calculate_weather_impact(self, edge: RouteEdge, weather_data: Dict) -> float:
        """Calculate weather impact on route segment."""
        try:
            # Simplified weather impact calculation
            # In production, this would use detailed weather forecasts along the route
            avg_wind_speed = weather_data.get("wind_speed", 10)
            avg_wave_height = weather_data.get("wave_height", 2)
            temperature = weather_data.get("temperature", 20)

            features = np.array(
                [[avg_wind_speed, avg_wave_height, temperature, edge.base_distance]]
            )
            features_scaled = self.scaler.transform(features)

            impact = self.weather_impact_model.predict(features_scaled)[0]
            return max(0.5, min(2.0, 1.0 + impact))  # Clamp between 0.5 and 2.0

        except Exception:
            return 1.0  # Default to no impact if calculation fails

    def _calculate_fuel_efficiency_factor(
        self, edge: RouteEdge, ship_specs: Dict
    ) -> float:
        """Calculate fuel efficiency factor for route segment."""
        try:
            # Simplified fuel efficiency calculation
            engine_power = ship_specs.get("engine_power", 10000)
            displacement = ship_specs.get("displacement", 50000)

            # Normalize factors
            power_factor = engine_power / 10000
            displacement_factor = displacement / 50000

            # Simple efficiency calculation
            efficiency = 1.0 / (power_factor * displacement_factor)
            return max(0.5, min(2.0, efficiency))

        except Exception:
            return 1.0

    def _astar_search(self, start: str, goal: str) -> List[RouteEdge]:
        """A* pathfinding algorithm implementation."""
        open_set = [(0, start, [])]
        closed_set = set()

        while open_set:
            current_cost, current_node, path = heapq.heappop(open_set)

            if current_node in closed_set:
                continue

            closed_set.add(current_node)

            if current_node == goal:
                return path

            for edge in self.graph.get_neighbors(current_node):
                if edge.end.port_name in closed_set:
                    continue

                new_cost = current_cost + edge.weight
                new_path = path + [edge]

                # Heuristic: distance to goal
                heuristic = self.graph._calculate_distance(
                    edge.end.coordinates.latitude,
                    edge.end.coordinates.longitude,
                    self.graph.nodes[goal].coordinates.latitude,
                    self.graph.nodes[goal].coordinates.longitude,
                )

                priority = new_cost + heuristic
                heapq.heappush(open_set, (priority, edge.end.port_name, new_path))

        return []  # No path found

    def _generate_waypoints(
        self,
        path: List[RouteEdge],
        origin: Coordinates,
        destination: Coordinates,
        ship_specs: Dict,
        weather_data: Optional[Dict],
    ) -> List[Waypoint]:
        """Generate detailed waypoints with timing and speed optimization."""
        waypoints = []
        current_time = datetime.utcnow()

        # Add origin waypoint
        initial_speed = self._calculate_optimal_speed(None, ship_specs, weather_data)
        initial_fuel_rate = self._calculate_fuel_rate(
            initial_speed, ship_specs, weather_data
        )

        waypoints.append(
            Waypoint(
                coordinates=origin,
                eta=current_time,
                speed=initial_speed,
                fuel_rate=initial_fuel_rate,
            )
        )

        # Add intermediate waypoints
        for edge in path:
            # Calculate optimal speed for this segment
            optimal_speed = self._calculate_optimal_speed(
                edge, ship_specs, weather_data
            )

            # Calculate ETA
            segment_time = edge.base_distance / optimal_speed
            current_time += timedelta(hours=segment_time)

            # Calculate fuel consumption rate
            fuel_rate = self._calculate_fuel_rate(
                optimal_speed, ship_specs, weather_data
            )

            waypoints.append(
                Waypoint(
                    coordinates=edge.end.coordinates,
                    eta=current_time,
                    speed=max(0.1, optimal_speed),  # Ensure speed > 0
                    fuel_rate=max(0.1, fuel_rate),  # Ensure fuel_rate > 0
                    weather_conditions=self._get_weather_for_location(
                        edge.end.coordinates, weather_data
                    ),
                )
            )

        # Add destination waypoint if different from last port
        if path:
            last_edge = path[-1]
            if (
                last_edge.end.coordinates.latitude != destination.latitude
                or last_edge.end.coordinates.longitude != destination.longitude
            ):
                # Calculate final segment
                final_distance = self.graph._calculate_distance(
                    last_edge.end.coordinates.latitude,
                    last_edge.end.coordinates.longitude,
                    destination.latitude,
                    destination.longitude,
                )

                final_speed = self._calculate_optimal_speed(
                    None, ship_specs, weather_data
                )
                final_time = final_distance / final_speed
                current_time += timedelta(hours=final_time)

                final_fuel_rate = self._calculate_fuel_rate(
                    final_speed, ship_specs, weather_data
                )
                waypoints.append(
                    Waypoint(
                        coordinates=destination,
                        eta=current_time,
                        speed=max(0.1, final_speed),  # Ensure speed > 0
                        fuel_rate=max(0.1, final_fuel_rate),  # Ensure fuel_rate > 0
                    )
                )

        return waypoints

    def _calculate_optimal_speed(
        self, edge: Optional[RouteEdge], ship_specs: Dict, weather_data: Optional[Dict]
    ) -> float:
        """Calculate optimal speed for a route segment."""
        max_speed = ship_specs.get("max_speed", 25)

        # Weather-based speed adjustment
        if weather_data:
            wind_speed = weather_data.get("wind_speed", 10)
            wave_height = weather_data.get("wave_height", 2)

            # Reduce speed in harsh conditions
            weather_factor = max(0.6, 1.0 - (wind_speed / 50) - (wave_height / 20))
            optimal_speed = max_speed * weather_factor
        else:
            optimal_speed = max_speed * 0.85  # Conservative default

        return min(max_speed, max(5, optimal_speed))  # Clamp between 5 and max_speed

    def _calculate_fuel_rate(
        self, speed: float, ship_specs: Dict, weather_data: Optional[Dict]
    ) -> float:
        """Calculate fuel consumption rate at given speed."""
        engine_power = ship_specs.get("engine_power", 10000)
        displacement = ship_specs.get("displacement", 50000)

        # Simplified fuel consumption model (cubic relationship with speed)
        base_consumption = (
            (speed**3) * (engine_power / 10000) * (displacement / 50000) * 0.1
        )

        # Weather impact on fuel consumption
        if weather_data:
            wind_speed = weather_data.get("wind_speed", 10)
            wave_height = weather_data.get("wave_height", 2)
            weather_impact = 1.0 + (wind_speed / 100) + (wave_height / 50)
            base_consumption *= weather_impact

        return base_consumption

    def _get_weather_for_location(
        self, coordinates: Coordinates, weather_data: Optional[Dict]
    ) -> Optional[WeatherCondition]:
        """Get weather conditions for a specific location."""
        if not weather_data:
            return None

        # Determine weather type based on conditions
        wind_speed = weather_data.get("wind_speed", 10)
        wave_height = weather_data.get("wave_height", 2)
        visibility = weather_data.get("visibility", 10)

        # Simple weather type classification
        if wind_speed > 20 or wave_height > 6:
            weather_type = "stormy"
        elif wind_speed > 15 or wave_height > 4:
            weather_type = "rough"
        elif visibility < 5:
            weather_type = "foggy"
        elif wind_speed < 5 and wave_height < 1:
            weather_type = "calm"
        else:
            weather_type = "moderate"

        return WeatherCondition(
            temperature=weather_data.get("temperature", 20),
            wind_speed=wind_speed,
            wind_direction=weather_data.get("wind_direction", 180),
            wave_height=wave_height,
            visibility=visibility,
            weather_type=weather_type,
        )

    def _calculate_confidence_score(
        self, path: List[RouteEdge], weather_data: Optional[Dict]
    ) -> float:
        """Calculate confidence score for the route optimization."""
        base_confidence = 0.8

        # Reduce confidence for longer routes
        route_length = len(path)
        length_penalty = min(0.2, route_length * 0.02)

        # Reduce confidence if no weather data
        weather_penalty = 0.1 if not weather_data else 0.0

        # Reduce confidence for high weather impact
        weather_impact_penalty = 0.0
        if weather_data:
            avg_weather_impact = np.mean([edge.weather_factor for edge in path])
            weather_impact_penalty = max(0, (avg_weather_impact - 1.0) * 0.2)

        confidence = (
            base_confidence - length_penalty - weather_penalty - weather_impact_penalty
        )
        return max(0.1, min(1.0, confidence))

    def _calculate_fuel_efficiency(
        self, path: List[RouteEdge], ship_specs: Dict
    ) -> float:
        """Calculate overall fuel efficiency score for the route."""
        total_distance = sum(edge.base_distance for edge in path)
        if total_distance == 0:
            return 1.0

        # Simplified efficiency calculation
        engine_efficiency = ship_specs.get("engine_power", 10000) / ship_specs.get(
            "displacement", 50000
        )
        route_efficiency = 1.0 / (1.0 + len(path) * 0.1)  # Penalty for complex routes

        return min(1.0, engine_efficiency * route_efficiency)


# Global route optimizer instance
route_optimizer = RouteOptimizer()
