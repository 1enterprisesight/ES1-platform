-- Create mlflow database for ML experiment tracking
CREATE DATABASE mlflow;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE mlflow TO CURRENT_USER;
