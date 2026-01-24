# syntax=docker/dockerfile:1
# Production Dockerfile - Node.js Service Template
# Multi-stage build for minimal image size

# =============================================================================
# Stage 1: Build
# =============================================================================
FROM node:20-slim AS builder

WORKDIR /build

COPY package*.json ./
RUN npm ci --only=production

# =============================================================================
# Stage 2: Production
# =============================================================================
FROM node:20-slim AS production

LABEL org.opencontainers.image.source="https://github.com/1enterprisesight/ES1-platform"

# Create non-root user
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /build/node_modules ./node_modules

# Copy application code
COPY --chown=appuser:appgroup package*.json ./
COPY --chown=appuser:appgroup src/ ./src/

# Switch to non-root user
USER appuser

ENV NODE_ENV=production \
    PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD node -e "require('http').get('http://localhost:8000/health', (r) => process.exit(r.statusCode === 200 ? 0 : 1))" || exit 1

CMD ["node", "src/index.js"]
