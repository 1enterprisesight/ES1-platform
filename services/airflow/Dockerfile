FROM apache/airflow:3.1.7-python3.12

USER airflow

RUN pip install --no-cache-dir \
    apache-airflow-providers-amazon==9.21.0 \
    apache-airflow-providers-postgres==6.5.3 \
    sqlmodel==0.0.37 \
    pytest==9.0.2 \
    "testcontainers[postgres]==4.14.1" \
    "psycopg[binary]==3.3.3"

COPY plugins/ /opt/airflow/plugins/
