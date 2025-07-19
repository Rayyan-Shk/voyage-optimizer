# 🚢 Ship Planning System - Complete API Documentation

## 📋 Overview

This document contains all API endpoints with their exact parameters, payloads, and usage examples.

**Base URL**: `http://localhost:8000`
**Authentication**: All endpoints (except health) require: `Authorization: Bearer demo_token`
**Environment Variable**: Set `DEBUG=true` for testing

---

## 🗺️ Voyage Planning APIs

### 1. Plan Voyage

**Endpoint**: `POST /api/v1/plan-voyage`
**Description**: Create optimized voyage plan with AI-powered route optimization

**Headers**:

```json
{
  "Content-Type": "application/json",
  "Authorization": "Bearer demo_token"
}
```

**Request Body**:

```json
{
  "ship_id": "12345678-1234-5678-9012-123456789012",
  "origin": {
    "latitude": 40.7128,
    "longitude": -74.006
  },
  "destination": {
    "latitude": 51.5074,
    "longitude": -0.1278
  },
  "departure_time": "2025-01-15T10:00:00Z",
  "cargo_weight": 25000,
  "optimization_preferences": {
    "time": 0.4,
    "fuel": 0.4,
    "safety": 0.2
  }
}
```

**cURL Example**:

```bash
curl -X POST "http://localhost:8000/api/v1/plan-voyage" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer demo_token" \
  -d '{
    "ship_id": "12345678-1234-5678-9012-123456789012",
    "origin": {"latitude": 40.7128, "longitude": -74.0060},
    "destination": {"latitude": 51.5074, "longitude": -0.1278"},
    "departure_time": "2025-01-15T10:00:00Z",
    "cargo_weight": 25000,
    "optimization_preferences": {"time": 0.4, "fuel": 0.4, "safety": 0.2}
  }'
  
```

**Response**: `200 OK` with `VoyagePlanResponse` object

---

### 2. Get Voyage History

**Endpoint**: `GET /api/v1/plan-history`
**Description**: Retrieve all historical voyage plans for analysis

**Query Parameters** (all optional):

- `ship_id` (UUID): Filter by specific ship
- `limit` (int): Number of records to return (default: 50)
- `offset` (int): Number of records to skip (default: 0)

**Headers**:

```json
{
  "Authorization": "Bearer demo_token"
}
```

**cURL Examples**:

```bash
# Get all voyage history
curl -X GET "http://localhost:8000/api/v1/plan-history" \
  -H "Authorization: Bearer demo_token"

# Get voyage history for specific ship
curl -X GET "http://localhost:8000/api/v1/plan-history?ship_id=12345678-1234-5678-9012-123456789012" \
  -H "Authorization: Bearer demo_token"

# Get voyage history with pagination
curl -X GET "http://localhost:8000/api/v1/plan-history?limit=10&offset=20" \
  -H "Authorization: Bearer demo_token"
```

**Response**: `200 OK` with array of `VoyageHistory` objects

---

### 3. Get Specific Voyage Details

**Endpoint**: `GET /api/v1/plan-history/{voyage_id}`
**Description**: Get detailed information about a specific voyage

**Path Parameters**:

- `voyage_id` (UUID): The voyage ID to retrieve

**Headers**:

```json
{
  "Authorization": "Bearer demo_token"
}
```

**cURL Example**:

```bash
curl -X GET "http://localhost:8000/api/v1/plan-history/12345678-1234-5678-9012-123456789012" \
  -H "Authorization: Bearer demo_token"
```

**Response**: `200 OK` with `VoyageHistory` object

---

## 🔧 Maintenance Management APIs

### 1. Get Maintenance Alerts

**Endpoint**: `GET http://localhost:8000/api/v1/maintenance-alerts?ship_id=12345678-1234-5678-9012-123456789012`
**Description**: Get predictive maintenance alerts for a ship

**Query Parameters** (required):

- `ship_id` (UUID): Ship ID to get alerts for

**Headers**:

```json
{
  "Authorization": "Bearer demo_token"
}
```

**cURL Example**:

```bash
curl -X GET "http://localhost:8000/api/v1/maintenance-alerts?ship_id=12345678-1234-5678-9012-123456789012" \
  -H "Authorization: Bearer demo_token"
```

**Response**: `200 OK` with `MaintenanceForecasting` object

---

### 2. Get Component Maintenance Alerts

**Endpoint**: `GET /api/v1/maintenance-alerts/{ship_id}/component/{component}`
**Description**: Get maintenance alerts for a specific ship component

**Path Parameters**:

- `ship_id` (UUID): Ship ID
- `component` (string): Component name (e.g., "engine", "propulsion", "navigation")

**Headers**:

```json
{
  "Authorization": "Bearer demo_token"
}
```

**cURL Example**:

```bash
curl -X GET "http://localhost:8000/api/v1/maintenance-alerts/12345678-1234-5678-9012-123456789012/component/engine" \
  -H "Authorization: Bearer demo_token"
```

**Response**: `200 OK` with array of `MaintenanceRecommendation` objects

---

### 3. Schedule Maintenance

**Endpoint**: `POST /api/v1/maintenance-alerts/{ship_id}/schedule`
**Description**: Schedule maintenance based on AI recommendations

**Path Parameters**:

- `ship_id` (UUID): Ship ID

**Query Parameters** (required):

- `recommendation_id` (string): Recommendation ID to schedule
- `scheduled_date` (datetime): When to schedule the maintenance

**Headers**:

```json
{
  "Authorization": "Bearer demo_token"
}
```

**cURL Example**:

```bash
curl -X POST "http://localhost:8000/api/v1/maintenance-alerts/12345678-1234-5678-9012-123456789012/schedule?recommendation_id=rec_123&scheduled_date=2025-02-15T10:00:00Z" \
  -H "Authorization: Bearer demo_token"
```

**Response**: `200 OK` with `APIResponse` object

---

### 4. Get Maintenance History

**Endpoint**: `GET /api/v1/maintenance-alerts/history/{ship_id}`
**Description**: View maintenance history for a ship

**Path Parameters**:

- `ship_id` (UUID): Ship ID

**Query Parameters** (optional):

- `limit` (int): Number of records to return (default: 50)
- `offset` (int): Number of records to skip (default: 0)

**Headers**:

```json
{
  "Authorization": "Bearer demo_token"
}
```

**cURL Example**:

```bash
curl -X GET "http://localhost:8000/api/v1/maintenance-alerts/history/12345678-1234-5678-9012-123456789012" \
  -H "Authorization: Bearer demo_token"
```

**Response**: `200 OK` with array of maintenance history objects

---

### 5. Get Maintenance Analytics

**Endpoint**: `GET /api/v1/maintenance-alerts/analytics/{ship_id}`
**Description**: Get maintenance analytics and insights for a ship

**Path Parameters**:

- `ship_id` (UUID): Ship ID

**Headers**:

```json
{
  "Authorization": "Bearer demo_token"
}
```

**cURL Example**:

```bash
curl -X GET "http://localhost:8000/api/v1/maintenance-alerts/analytics/12345678-1234-5678-9012-123456789012" \
  -H "Authorization: Bearer demo_token"
```

**Response**: `200 OK` with analytics object

---

## 📝 Feedback & Learning APIs

### 1. Submit Voyage Feedback

**Endpoint**: `POST /api/v1/feedback`
**Description**: Submit voyage feedback for continuous learning

**Headers**:

```json
{
  "Content-Type": "application/json",
  "Authorization": "Bearer demo_token"
}
```

**Request Body**:

```json
{
  "voyage_id": "98462b53-253e-497f-b3cf-ad40aca62770",
  "ship_id": "12345678-1234-5678-9012-123456789012",
  "actual_fuel_consumption": 650.5,
  "actual_duration": 245.2,
  "route_deviations": [
    {
      "latitude": 41.0,
      "longitude": -73.5
    }
  ],
  "weather_accuracy": 0.85,
  "maintenance_events": [],
  "overall_satisfaction": 4,
  "comments": "Route was efficient but could be improved for weather conditions"
}
```

**cURL Example**:

```bash
curl -X POST "http://localhost:8000/api/v1/feedback" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer demo_token" \
  -d '{
    "voyage_id": "98462b53-253e-497f-b3cf-ad40aca62770",
    "ship_id": "12345678-1234-5678-9012-123456789012",
    "actual_fuel_consumption": 650.5,
    "actual_duration": 245.2,
    "route_deviations": [],
    "weather_accuracy": 0.85,
    "maintenance_events": [],
    "overall_satisfaction": 4,
    "comments": "Route was efficient"
  }'
```

**Response**: `200 OK` with `APIResponse` object

---

### 2. Get Prediction Accuracy

**Endpoint**: `GET /api/v1/feedback/accuracy`
**Description**: Get prediction accuracy metrics for model performance monitoring

**Query Parameters** (optional):

- `ship_id` (UUID): Filter by specific ship
- `days` (int): Number of days to look back (default: 30)

**Headers**:

```json
{
  "Authorization": "Bearer demo_token"
}
```

**cURL Examples**:

```bash
# Get overall accuracy metrics
curl -X GET "http://localhost:8000/api/v1/feedback/accuracy" \
  -H "Authorization: Bearer demo_token"

# Get accuracy for specific ship
curl -X GET "http://localhost:8000/api/v1/feedback/accuracy?ship_id=12345678-1234-5678-9012-123456789012" \
  -H "Authorization: Bearer demo_token"

# Get accuracy for last 7 days
curl -X GET "http://localhost:8000/api/v1/feedback/accuracy?days=7" \
  -H "Authorization: Bearer demo_token"
```

**Response**: `200 OK` with accuracy metrics object

---

## 🏥 Health & Monitoring APIs

### 1. Basic Health Check

**Endpoint**: `GET /health`
**Description**: Basic health check - is the service running?

**No authentication required**

**cURL Example**:

```bash
curl -X GET "http://localhost:8000/health"
```

**Response**: `200 OK` with basic health status

---

### 2. Detailed Health Check

**Endpoint**: `GET /health/detailed`
**Description**: Detailed system status (database, cache, external services)

**No authentication required**

**cURL Example**:

```bash
curl -X GET "http://localhost:8000/health/detailed"
```

**Response**: `200 OK` with detailed service status

---

### 3. Prometheus Metrics

**Endpoint**: `GET /metrics`
**Description**: Prometheus metrics for monitoring and alerting

**No authentication required**

**cURL Example**:

```bash
curl -X GET "http://localhost:8000/metrics"
```

**Response**: `200 OK` with Prometheus metrics in text format

---

### 4. Root Endpoint

**Endpoint**: `GET /`
**Description**: Root endpoint with system information and available endpoints

**No authentication required**

**cURL Example**:

```bash
curl -X GET "http://localhost:8000/"
```

**Response**: `200 OK` with system information and endpoint list

---

## 🎯 Quick Test Commands

### Test All Core APIs:

```bash
# 1. Plan a voyage
curl -X POST "http://localhost:8000/api/v1/plan-voyage" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer demo_token" \
  -d '{"ship_id": "12345678-1234-5678-9012-123456789012", "origin": {"latitude": 40.7128, "longitude": -74.0060}, "destination": {"latitude": 51.5074, "longitude": -0.1278}, "departure_time": "2025-01-15T10:00:00Z", "cargo_weight": 25000, "optimization_preferences": {"time": 0.4, "fuel": 0.4, "safety": 0.2}}'

# 2. Get voyage history
curl -X GET "http://localhost:8000/api/v1/plan-history" \
  -H "Authorization: Bearer demo_token"

# 3. Get maintenance alerts (FIXED - with required ship_id parameter)
curl -X GET "http://localhost:8000/api/v1/maintenance-alerts?ship_id=12345678-1234-5678-9012-123456789012" \
  -H "Authorization: Bearer demo_token"

# 4. Submit feedback
curl -X POST "http://localhost:8000/api/v1/feedback" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer demo_token" \
  -d '{"voyage_id": "98462b53-253e-497f-b3cf-ad40aca62770", "ship_id": "12345678-1234-5678-9012-123456789012", "actual_fuel_consumption": 650.5, "actual_duration": 245.2, "route_deviations": [], "weather_accuracy": 0.85, "maintenance_events": [], "overall_satisfaction": 4, "comments": "Test feedback"}'

# 5. Get prediction accuracy (FIXED - with optional parameters)
curl -X GET "http://localhost:8000/api/v1/feedback/accuracy" \
  -H "Authorization: Bearer demo_token"

# 6. Health checks
curl -X GET "http://localhost:8000/health"
curl -X GET "http://localhost:8000/health/detailed"
curl -X GET "http://localhost:8000/metrics"
```

---

## 🚨 Common Issues & Solutions

### 1. 422 Unprocessable Entity

**Issue**: Missing required parameters
**Solution**: Check the parameter requirements in this documentation

### 2. 401 Unauthorized

**Issue**: Missing or invalid authentication
**Solution**: Add `Authorization: Bearer demo_token` header and set `DEBUG=true`

### 3. 500 Internal Server Error

**Issue**: Server-side error
**Solution**: Check server logs for detailed error messages

### 4. 404 Not Found

**Issue**: Wrong endpoint URL
**Solution**: Verify the endpoint URL against this documentation

---

## 📊 Sample Ship ID for Testing

Use this ship ID for all tests: `12345678-1234-5678-9012-123456789012`

This ship exists in the database with sample data and will work with all endpoints.

---

## 🔧 Environment Setup

Before testing, ensure:

1. Server is running: `python main.py`
2. Environment variable is set: `DEBUG=true`
3. Database is initialized: `python init_db.py`
4. All required services are running (PostgreSQL, Redis)

---

_Last updated: 2025-01-18_
_Version: 1.0.0_
