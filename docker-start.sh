#!/bin/bash

# 🚢 Ship Planning System - Docker Startup Script
# This script starts the entire application with one command

set -e

echo "🚢 Starting Ship Planning & Optimization System..."
echo "================================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating one from env.example..."
    cp env.example .env
    echo "✅ Created .env file. Please update it with your API keys:"
    echo "   - WEATHER_API_KEY: Get from https://openweathermap.org/api"
    echo "   - SECRET_KEY: Change to a secure random string"
    echo ""
    echo "After updating .env, run this script again."
    exit 1
fi

# Check if WEATHER_API_KEY is set
if grep -q "your_openweather_api_key_here" .env; then
    echo "⚠️  Please update your WEATHER_API_KEY in .env file"
    echo "   Get a free API key from: https://openweathermap.org/api"
    echo ""
    echo "After updating .env, run this script again."
    exit 1
fi

# Create logs directory
mkdir -p logs

echo "🧹 Cleaning up any existing containers..."
docker-compose down --remove-orphans

echo "🏗️  Building application image..."
docker-compose build --no-cache

echo "🚀 Starting all services..."
docker-compose up -d postgres redis

echo "⏳ Waiting for database to be ready..."
sleep 10

echo "🗄️  Initializing database..."
docker-compose run --rm db-init

echo "🎯 Starting main application..."
docker-compose up -d app

echo "✅ All services started successfully!"
echo ""
echo "🌐 Application URLs:"
echo "   • API Documentation: http://localhost:8000/docs"
echo "   • Health Check: http://localhost:8000/health"
echo "   • Metrics: http://localhost:8000/metrics"
echo "   • Root Info: http://localhost:8000/"
echo ""
echo "📊 Service Status:"
docker-compose ps

echo ""
echo "📝 To view logs:"
echo "   • All services: docker-compose logs -f"
echo "   • App only: docker-compose logs -f app"
echo "   • Database: docker-compose logs -f postgres"
echo "   • Cache: docker-compose logs -f redis"
echo ""
echo "🛑 To stop all services:"
echo "   • docker-compose down"
echo ""
echo "🎉 Ship Planning System is ready!" 