# Custom PostgreSQL with extensions
# Based on official postgres image with pgvector support

FROM postgres:16-alpine

LABEL org.opencontainers.image.source="https://github.com/1enterprisesight/ES1-platform"
LABEL org.opencontainers.image.description="PostgreSQL 16 with pgvector extension"

# Install build dependencies and pgvector
RUN apk add --no-cache --virtual .build-deps \
        git \
        build-base \
        clang15 \
        llvm15-dev \
    && cd /tmp \
    && git clone --branch v0.7.4 https://github.com/pgvector/pgvector.git \
    && cd pgvector \
    && make \
    && make install \
    && cd / \
    && rm -rf /tmp/pgvector \
    && apk del .build-deps

# Copy initialization scripts
COPY init/ /docker-entrypoint-initdb.d/

# Default environment variables
ENV POSTGRES_DB=es1_platform \
    POSTGRES_USER=es1_user
