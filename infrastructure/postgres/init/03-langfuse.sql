-- Create Langfuse database
-- Langfuse will initialize its own schema on first run

CREATE DATABASE langfuse;
GRANT ALL PRIVILEGES ON DATABASE langfuse TO CURRENT_USER;

\c langfuse
GRANT ALL ON SCHEMA public TO CURRENT_USER;
