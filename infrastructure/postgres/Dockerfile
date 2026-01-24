# PostgreSQL with pgvector extension
# Using official pgvector image for simplicity and reliability

FROM pgvector/pgvector:pg16

LABEL org.opencontainers.image.source="https://github.com/1enterprisesight/ES1-platform"
LABEL org.opencontainers.image.description="PostgreSQL 16 with pgvector extension"

# Copy initialization scripts
COPY init/ /docker-entrypoint-initdb.d/

# Default environment variables
ENV POSTGRES_DB=es1_platform \
    POSTGRES_USER=es1_user
