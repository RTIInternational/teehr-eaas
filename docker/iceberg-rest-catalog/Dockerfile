# Use the official Apache Iceberg REST catalog image as base
FROM tabulario/iceberg-rest:0.7.0

# Install curl for health checks
USER root
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
USER iceberg

# Add health check (aligned with ECS task definition)
HEALTHCHECK --interval=30s --timeout=15s --start-period=180s --retries=5 \
  CMD curl -f http://localhost:8181/v1/config || exit 1

# Expose the REST API port
EXPOSE 8181

# Set default environment variables
ENV CATALOG_WAREHOUSE=s3://warehouse/
ENV CATALOG_IO__IMPL=org.apache.iceberg.aws.s3.S3FileIO
ENV CATALOG_S3_ENDPOINT=https://s3.amazonaws.com

# Add labels for better organization
LABEL org.opencontainers.image.title="TEEHR Iceberg REST Catalog"
LABEL org.opencontainers.image.description="Apache Iceberg REST Catalog for TEEHR evaluation system"
LABEL org.opencontainers.image.version="0.7.0"
LABEL maintainer="teehr-team"