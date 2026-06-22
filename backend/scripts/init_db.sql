-- NeoFace PostgreSQL Initialization
-- Runs automatically when the postgres container is first created

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Optional: pgvector for ANN search (upgrade path for large deployments)
-- CREATE EXTENSION IF NOT EXISTS "vector";

-- Set timezone
SET timezone = 'UTC';
