-- V001: Extensions and app schema
-- Initial setup for platform database

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Create application schema
CREATE SCHEMA IF NOT EXISTS app;
