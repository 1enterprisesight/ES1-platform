# PostgreSQL with pgvector extension for AI/ML workloads
# Dedicated database for vectors, embeddings, and ML data
# Separate from platform database for isolation and scaling

FROM pgvector/pgvector:pg16

LABEL org.opencontainers.image.source="https://github.com/1enterprisesight/ES1-platform"
LABEL org.opencontainers.image.description="PostgreSQL 16 with pgvector for AI/ML workloads"

# Copy initialization scripts
COPY init/ /docker-entrypoint-initdb.d/

# Default environment variables
ENV POSTGRES_DB=aiml \
    POSTGRES_USER=aiml_user

# Optimize for vector workloads
# These can be overridden via docker-compose environment
ENV POSTGRES_INITDB_ARGS="--data-checksums"
