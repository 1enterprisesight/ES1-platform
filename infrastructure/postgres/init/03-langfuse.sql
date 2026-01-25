-- Create Langfuse database
-- Langfuse will initialize its own schema on first run

CREATE DATABASE langfuse;
GRANT ALL PRIVILEGES ON DATABASE langfuse TO es1_user;

\c langfuse
GRANT ALL ON SCHEMA public TO es1_user;
