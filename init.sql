-- 🚢 Ship Planning System - Database Initialization
-- This script runs when PostgreSQL container starts for the first time

-- Create database if it doesn't exist (handled by POSTGRES_DB env var)
-- The database 'ship_planning' is automatically created by the postgres container

-- Create extensions for better performance
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE ship_planning TO ship_user;

-- Connect to the ship_planning database
\c ship_planning;

-- Grant schema permissions
GRANT ALL ON SCHEMA public TO ship_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ship_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ship_user;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ship_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ship_user;

-- Create indexes for better performance (these will be created by SQLAlchemy, but we can prepare)
-- The actual table creation happens in init_db.py via SQLAlchemy

-- Log completion
\echo 'Database initialization completed successfully!' 