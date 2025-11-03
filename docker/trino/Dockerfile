# Use the official Trino image as base
FROM trinodb/trino:427

# Switch to root user to install dependencies and configure
USER root

# Install necessary tools
RUN apt-get update && \
    apt-get install -y curl gettext-base && \
    rm -rf /var/lib/apt/lists/*

# Create configuration directories
RUN mkdir -p /etc/trino/catalog /data/trino

# Copy configuration templates
COPY config/ /etc/trino/

# Copy the entrypoint script
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Fix ownership and permissions for trino user
RUN chown -R trino:trino /etc/trino /data/trino

# Switch back to trino user
USER trino

# Add health check
HEALTHCHECK --interval=30s --timeout=15s --start-period=120s --retries=5 \
  CMD curl -f http://localhost:8080/v1/status || exit 1

# Expose Trino port
EXPOSE 8080

# Add labels for better organization
LABEL org.opencontainers.image.title="TEEHR Trino"
LABEL org.opencontainers.image.description="Trino query engine for TEEHR evaluation system"
LABEL org.opencontainers.image.version="427"
LABEL maintainer="teehr-team"

# Use our custom entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]