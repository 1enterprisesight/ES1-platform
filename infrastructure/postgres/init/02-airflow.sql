-- Create Airflow database
-- Airflow will initialize its own schema on first run

CREATE DATABASE airflow;
GRANT ALL PRIVILEGES ON DATABASE airflow TO es1_user;

\c airflow
GRANT ALL ON SCHEMA public TO es1_user;
