# Custom Redis configuration
# Based on official redis image

FROM redis:7-alpine

LABEL org.opencontainers.image.source="https://github.com/1enterprisesight/ES1-platform"
LABEL org.opencontainers.image.description="Redis 7 for ES1 Platform"

# Copy custom configuration
COPY redis.conf /usr/local/etc/redis/redis.conf

# Run as non-root
USER redis

CMD ["redis-server", "/usr/local/etc/redis/redis.conf"]
