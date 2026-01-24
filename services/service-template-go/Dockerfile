# syntax=docker/dockerfile:1
# Production Dockerfile - Go Service Template
# Multi-stage build for minimal image size

# =============================================================================
# Stage 1: Build
# =============================================================================
FROM golang:1.22-alpine AS builder

WORKDIR /build

# Install ca-certificates for HTTPS
RUN apk add --no-cache ca-certificates

# Download dependencies
COPY go.mod go.sum* ./
RUN go mod download

# Build the application
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-w -s" -o /app ./cmd/main.go

# =============================================================================
# Stage 2: Production
# =============================================================================
FROM scratch AS production

LABEL org.opencontainers.image.source="https://github.com/1enterprisesight/ES1-platform"

# Copy CA certificates
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/

# Copy binary
COPY --from=builder /app /app

# Non-root user (numeric for scratch image)
USER 1000:1000

ENV PORT=8000

EXPOSE 8000

# Note: HEALTHCHECK not supported in scratch, use Kubernetes probes
ENTRYPOINT ["/app"]
