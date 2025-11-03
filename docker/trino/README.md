# TEEHR Trino Docker Image

This directory contains the Docker setup for building a custom Trino image with baked-in configuration templates for the TEEHR evaluation system.

## Why Use a Custom Image?

The custom Docker image approach provides several advantages over inline shell scripts in ECS task definitions:

1. **Reliability**: Configuration files are baked into the image, eliminating runtime script failures
2. **Environment Variable Substitution**: Proper `envsubst` handling of variables
3. **Version Control**: Configuration changes are tracked with Docker image versions
4. **Faster Startup**: No need to generate configuration files at runtime
5. **Debugging**: Easy to test locally and inspect configuration
6. **Consistency**: Matches the pattern used for the Iceberg REST catalog

## File Structure

```
docker/trino/
├── Dockerfile                                    # Main Docker build file
├── build.sh                                     # Build and push script  
├── entrypoint.sh                                # Runtime entrypoint script
├── config/
│   ├── config.properties.template               # Main Trino configuration
│   ├── node.properties.template                 # Node identification
│   ├── jvm.config.template                      # JVM settings
│   ├── log.properties                           # Logging configuration
│   └── catalog/
│       └── iceberg.properties.template          # Iceberg catalog config
└── simplified-task-definitions.tf               # Example ECS task definitions
```

## Environment Variables

The image supports these environment variables for configuration:

### Trino Core Settings
- `TRINO_COORDINATOR`: "true" for coordinator, "false" for worker
- `TRINO_INCLUDE_COORDINATOR`: Whether coordinator participates in execution
- `TRINO_DISCOVERY_URI`: URI for service discovery
- `TRINO_MAX_MEMORY`: Total memory available for queries
- `TRINO_MAX_MEMORY_PER_NODE`: Memory limit per node
- `TRINO_ENVIRONMENT`: Environment name (dev/staging/prod)
- `TRINO_NODE_ID`: Unique node identifier
- `TRINO_HEAP_SIZE`: JVM heap size

### Iceberg Integration
- `ICEBERG_REST_URI`: Iceberg REST catalog endpoint
- `S3_WAREHOUSE_URI`: S3 warehouse location
- `AWS_REGION`: AWS region

## Building and Pushing

1. **Build the image:**
   ```bash
   cd docker/trino
   ./build.sh
   ```

2. **The script will:**
   - Login to ECR
   - Create the repository if needed
   - Build for linux/amd64 (required for ECS Fargate)
   - Push to ECR
   - Display the final ECR URI

## Using in Terraform

Update your `trino_image` variable to use the ECR URI:

```hcl
# In your terraform.tfvars or variables
trino_image = "123456789012.dkr.ecr.us-east-2.amazonaws.com/dev-teehr-sys/trino:latest"
```

Then update the ECS task definitions to use simple environment variables instead of complex shell scripts.

## Local Testing

You can test the image locally:

```bash
# Test coordinator
docker run --rm -p 8080:8080 \
  -e TRINO_COORDINATOR=true \
  -e TRINO_ENVIRONMENT=dev \
  -e TRINO_NODE_ID=coordinator001 \
  -e ICEBERG_REST_URI=http://localhost:8181 \
  -e S3_WAREHOUSE_URI=s3://test-bucket/warehouse/ \
  -e AWS_REGION=us-east-2 \
  dev-teehr-sys/trino:latest

# Test worker
docker run --rm -p 8081:8080 \
  -e TRINO_COORDINATOR=false \
  -e TRINO_DISCOVERY_URI=http://coordinator:8080 \
  -e TRINO_ENVIRONMENT=dev \
  -e TRINO_NODE_ID=worker001 \
  -e ICEBERG_REST_URI=http://localhost:8181 \
  -e S3_WAREHOUSE_URI=s3://test-bucket/warehouse/ \
  -e AWS_REGION=us-east-2 \
  dev-teehr-sys/trino:latest
```

## Migration Steps

1. **Build and push the custom image**
2. **Update Terraform variables** to use the new ECR image URI
3. **Replace the complex shell script task definitions** with simple environment variable configurations
4. **Test the deployment** in a development environment
5. **Update the dashboard connection** to use the ECS endpoint

This approach eliminates the shell script complexity and provides a much more maintainable solution.