-- Create Langflow database
-- Langflow will initialize its own schema on first run

CREATE DATABASE langflow;
GRANT ALL PRIVILEGES ON DATABASE langflow TO CURRENT_USER;

\c langflow
GRANT ALL ON SCHEMA public TO CURRENT_USER;
