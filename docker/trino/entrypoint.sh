#!/bin/bash
set -e

echo "Starting TEEHR Trino container..."
echo "Node Type: ${TRINO_COORDINATOR:-true}"
echo "Environment: ${TRINO_ENVIRONMENT:-dev}"
echo "Node ID: ${TRINO_NODE_ID:-node001}"

# Set default values for variables
export TRINO_COORDINATOR=${TRINO_COORDINATOR:-true}
export TRINO_INCLUDE_COORDINATOR=${TRINO_INCLUDE_COORDINATOR:-false}
export TRINO_DISCOVERY_URI=${TRINO_DISCOVERY_URI:-http://localhost:8080}
export TRINO_MAX_MEMORY=${TRINO_MAX_MEMORY:-6GB}
export TRINO_MAX_MEMORY_PER_NODE=${TRINO_MAX_MEMORY_PER_NODE:-2GB}
export TRINO_ENVIRONMENT=${TRINO_ENVIRONMENT:-dev}
export TRINO_NODE_ID=${TRINO_NODE_ID:-node001}
export TRINO_HEAP_SIZE=${TRINO_HEAP_SIZE:-6G}

# Create the final configuration directory
mkdir -p /etc/trino/catalog

# Process configuration templates with environment variable substitution
echo "Processing configuration templates..."

# Process main config files
envsubst < /etc/trino/config.properties.template > /etc/trino/config.properties
envsubst < /etc/trino/node.properties.template > /etc/trino/node.properties
envsubst < /etc/trino/jvm.config.template > /etc/trino/jvm.config

# Static files are already in place (log.properties doesn't need templating)

# Process catalog configurations
envsubst < /etc/trino/catalog/iceberg.properties.template > /etc/trino/catalog/iceberg.properties

# Debug: Show final configuration (without sensitive values)
echo "=== Final Configuration ==="
echo "Config properties:"
cat /etc/trino/config.properties
echo ""
echo "Node properties:"
cat /etc/trino/node.properties
echo ""
echo "Catalog configuration:"
sed 's/\(uri=\).*/\1[REDACTED]/' /etc/trino/catalog/iceberg.properties
echo "==========================="

# Ensure proper ownership
chown -R trino:trino /data/trino /etc/trino

# Start Trino
echo "Starting Trino server..."
exec /usr/lib/trino/bin/launcher run --etc-dir /etc/trino