-- Flight Tracker Database Initialization
-- This script runs automatically when PostgreSQL container starts

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create indexes for performance
-- (These will be created by SQLAlchemy migrations, but we add some here for base tables)

-- Grant permissions
-- Note: Application user should be created via environment variables

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'Flight Tracker database initialized successfully';
END $$;
