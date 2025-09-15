-- VNB Digitaler Database Initialization
-- PostgreSQL 16 compatible
-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
-- Create schema
CREATE SCHEMA IF NOT EXISTS vnb_digitaler;
-- Set search path
SET search_path TO vnb_digitaler,
    public;
-- Grant permissions to admin user
GRANT ALL PRIVILEGES ON SCHEMA vnb_digitaler TO vnb_admin;
