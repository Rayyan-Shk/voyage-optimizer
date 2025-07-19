@echo off
REM 🚢 Ship Planning System - Docker Startup Script for Windows
REM This script starts the entire application with one command

echo 🚢 Starting Ship Planning & Optimization System...
echo =================================================

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker is not running. Please start Docker Desktop first.
    pause
    exit /b 1
)

REM Check if .env file exists
if not exist .env (
    echo ⚠️  No .env file found. Creating one from env.example...
    copy env.example .env
    echo ✅ Created .env file. Please update it with your API keys:
    echo    - WEATHER_API_KEY: Get from https://openweathermap.org/api
    echo    - SECRET_KEY: Change to a secure random string
    echo.
    echo After updating .env, run this script again.
    pause
    exit /b 1
)

REM Check if WEATHER_API_KEY is set
findstr /C:"your_openweather_api_key_here" .env >nul
if %errorlevel% equ 0 (
    echo ⚠️  Please update your WEATHER_API_KEY in .env file
    echo    Get a free API key from: https://openweathermap.org/api
    echo.
    echo After updating .env, run this script again.
    pause
    exit /b 1
)

REM Create logs directory
if not exist logs mkdir logs

echo 🧹 Cleaning up any existing containers...
docker-compose down --remove-orphans

echo 🏗️  Building application image...
docker-compose build --no-cache

echo 🚀 Starting all services...
docker-compose up -d postgres redis

echo ⏳ Waiting for database to be ready...
timeout /t 10 /nobreak >nul

echo 🗄️  Initializing database...
docker-compose run --rm db-init

echo 🎯 Starting main application...
docker-compose up -d app

echo ✅ All services started successfully!
echo.
echo 🌐 Application URLs:
echo    • API Documentation: http://localhost:8000/docs
echo    • Health Check: http://localhost:8000/health
echo    • Metrics: http://localhost:8000/metrics
echo    • Root Info: http://localhost:8000/
echo.
echo 📊 Service Status:
docker-compose ps

echo.
echo 📝 To view logs:
echo    • All services: docker-compose logs -f
echo    • App only: docker-compose logs -f app
echo    • Database: docker-compose logs -f postgres
echo    • Cache: docker-compose logs -f redis
echo.
echo 🛑 To stop all services:
echo    • docker-compose down
echo.
echo 🎉 Ship Planning System is ready!
pause 