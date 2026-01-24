# syntax=docker/dockerfile:1
# Production Dockerfile for KrakenD API Gateway
# Multi-arch compatible (amd64/arm64)

FROM devopsfaith/krakend:2.6 AS production

LABEL org.opencontainers.image.source="https://github.com/1enterprisesight/ES1-platform"
LABEL org.opencontainers.image.description="ES1 Platform API Gateway (KrakenD)"

# Copy configuration
COPY config/ /etc/krakend/

# Validate configuration at build time
RUN krakend check -d -t -c /etc/krakend/krakend.json

# KrakenD runs as non-root by default (krakend user)
USER krakend

EXPOSE 8080 8090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8090/__health || exit 1

ENTRYPOINT ["/usr/bin/krakend"]
CMD ["run", "-d", "-c", "/etc/krakend/krakend.json"]
