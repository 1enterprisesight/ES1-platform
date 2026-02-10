-- Create Airflow database
-- Airflow will initialize its own schema on first run

CREATE DATABASE airflow;
GRANT ALL PRIVILEGES ON DATABASE airflow TO CURRENT_USER;

\c airflow
GRANT ALL ON SCHEMA public TO CURRENT_USER;
