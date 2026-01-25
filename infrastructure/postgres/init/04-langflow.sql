-- Create Langflow database
-- Langflow will initialize its own schema on first run

CREATE DATABASE langflow;
GRANT ALL PRIVILEGES ON DATABASE langflow TO es1_user;

\c langflow
GRANT ALL ON SCHEMA public TO es1_user;
