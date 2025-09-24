# TEEHR Evaluation System - AI Coding Guidelines

## Project Overview
This is a cloud-based TEEHR (Tools for Exploratory Evaluation in Hydrologic Research) evaluation system hosted on AWS. The system uses an Apache Iceberg data warehouse with REST catalog for scalable hydrologic data storage and analysis, complemented by web APIs, dashboards, and Jupyter notebooks for interactive evaluation workflows.

## Architecture & Key Components

### Cloud Infrastructure (AWS)
- **Data Lake**: S3-based storage with Apache Iceberg tables for time series and metadata
- **Catalog Service**: REST catalog for Iceberg table management and schema evolution
- **Compute**: EMR/Glue for PySpark workloads, ECS/Fargate for API services
- **Analytics**: EMR clusters for TEEHR/PySpark processing, SageMaker for notebooks
- **Storage**: S3 for raw data ingestion and Iceberg table storage

### Data Warehouse (Apache Iceberg)
- **Table Structure**: Partitioned by time and location for optimal query performance
- **Schema Evolution**: Handle evolving data formats from USGS, NWM, and custom sources
- **Time Travel**: Leverage Iceberg's versioning for data lineage and reproducibility
- **Compaction**: Automated maintenance for optimal file sizes and query performance

### Service Architecture
- `api/` - REST API services for data access and evaluation endpoints
- `warehouse/` - Iceberg table management, schema definitions, and ETL pipelines
- `dashboards/` - Interactive visualization components and dashboard backends
- `notebooks/` - Jupyter notebook templates and shared analysis libraries
- `infrastructure/` - AWS CDK/Terraform for infrastructure as code

### Configuration Management
- Environment-specific AWS resource configurations
- Iceberg catalog connection settings and table schemas
- API authentication and authorization policies
- Use AWS Systems Manager Parameter Store for secrets management

## Development Patterns

### Iceberg Table Operations
```python
# Standard pattern for querying Iceberg tables
from pyiceberg.catalog import load_catalog

catalog = load_catalog("rest", **catalog_config)
table = catalog.load_table("teehr.timeseries_data")

# Time-based filtering with partition pruning
df = table.scan(
    filter=("timestamp", ">=", start_date) & ("timestamp", "<", end_date)
).to_pandas()
```

### API Service Development
- Use FastAPI for REST endpoints with automatic OpenAPI documentation
- Implement async/await patterns for I/O operations
- Structure responses with consistent error handling and status codes
- Include request/response validation with Pydantic models

### Time Series Data Handling with PySpark
```python
# Standard pattern for TEEHR evaluation with PySpark and Iceberg
from pyspark.sql import SparkSession
import teehr

def create_spark_session(catalog_uri: str, warehouse_location: str):
    """Create Spark session configured for Iceberg catalog"""
    return SparkSession.builder.appName("teehr-eval") \
        .config("spark.jars.packages", 
                "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.6.0,"
                "org.apache.hadoop:hadoop-aws:3.4.0,"
                "com.amazonaws:aws-java-sdk-bundle:1.12.772") \
        .config("spark.sql.catalog.iceberg", "org.apache.iceberg.spark.SparkCatalog") \
        .config("spark.sql.catalog.iceberg.type", "rest") \
        .config("spark.sql.catalog.iceberg.uri", catalog_uri) \
        .config("spark.sql.catalog.iceberg.warehouse", warehouse_location) \
        .config("spark.sql.catalog.iceberg.io-impl", "org.apache.iceberg.aws.s3.S3FileIO") \
        .getOrCreate()

def evaluate_timeseries_spark(location_id: str, start_date: str, end_date: str):
    """Retrieve and evaluate time series using TEEHR's PySpark backend"""
    spark = create_spark_session(catalog_uri, warehouse_location)
    
    # Query Iceberg tables directly with Spark SQL
    observed_df = spark.sql(f"""
        SELECT timestamp, value
        FROM iceberg.teehr.timeseries
        WHERE location_id = '{location_id}'
          AND configuration = 'observed'
          AND timestamp >= '{start_date}' AND timestamp < '{end_date}'
        ORDER BY timestamp
    """)
    
    simulated_df = spark.sql(f"""
        SELECT timestamp, value  
        FROM iceberg.teehr.timeseries
        WHERE location_id = '{location_id}'
          AND configuration = 'nwm_retrospective'
          AND timestamp >= '{start_date}' AND timestamp < '{end_date}'
        ORDER BY timestamp
    """)
    
    # Use TEEHR's evaluation functions
    return teehr.evaluate_spark(observed_df, simulated_df)
```

### Infrastructure as Code
- Use Terraform for reproducible AWS deployments
- Modular structure: `modules/` for reusable components, `environments/` for env-specific configs
- Separate modules for data-lake (S3), iceberg-catalog (ECS + RDS), networking (VPC)
- Version control all infrastructure changes with state management in S3 backend

### Iceberg Warehouse Architecture
```hcl
# Core components for Iceberg REST catalog
# S3 bucket for table data and metadata
resource "aws_s3_bucket" "iceberg_warehouse" {
  bucket = "${var.environment}-teehr-iceberg-warehouse"
}

# RDS PostgreSQL for catalog metadata backend
resource "aws_db_instance" "catalog_db" {
  identifier = "${var.environment}-iceberg-catalog-db"
  engine     = "postgres"
  engine_version = "15.4"
  instance_class = var.db_instance_class
}

# ECS service for REST catalog container
resource "aws_ecs_service" "iceberg_catalog" {
  name            = "${var.environment}-iceberg-catalog"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.iceberg_catalog.arn
  desired_count   = var.catalog_replicas
}
```

### Code Quality
- Use `black` for formatting with line length 88
- `isort` for import organization
- `flake8` or `ruff` for linting
- Type hints required for public APIs

### Performance Considerations
- Profile memory usage for large datasets
- Use vectorized operations over loops
- Consider `dask` for out-of-core processing if needed
- Cache expensive computations with clear invalidation logic

## Testing Strategy

### Data-Driven Tests
- Use synthetic datasets with known statistical properties
- Test edge cases: single values, all NaN, misaligned time series
- Validate against reference implementations where available

### Performance Testing
- Benchmark large dataset processing (>1M records)
- Memory usage profiling for long time series
- Parallel processing validation

## Dependencies & Environment

### Cloud & Data Warehouse
- `pyiceberg`: Apache Iceberg Python client for table operations
- `boto3`: AWS SDK for S3, EMR, and other AWS services
- `awswrangler`: Simplified AWS data operations
- `sqlalchemy`: Database abstraction for REST catalog integration

### API & Web Services
- `fastapi`: Modern Python web framework for APIs
- `uvicorn`: ASGI server for FastAPI applications
- `httpx`: Async HTTP client for external API calls
- `redis`: Caching and session management

### Analytics & Visualization
- `teehr`: Core hydrologic evaluation library (PySpark 4.0-based)
- `pyspark`: Distributed computing engine for large-scale analytics (v4.0.0)
- `pandas`: Local data manipulation (for smaller datasets and API responses)
- `plotly` + `streamlit`: Interactive dashboards and visualizations
- `jupyter`: Notebook environment with PySpark 4.0 kernel support

### Infrastructure & DevOps
- `aws-cdk-lib`: Infrastructure as code for AWS resources
- `docker`: Containerization for consistent deployments
- `pytest-asyncio`: Testing async API endpoints

## Development Workflow

### Local Development
```bash
# Standard development setup with cloud dependencies
pip install -e ".[dev]"
aws configure  # Configure AWS credentials
docker-compose up -d  # Local Iceberg catalog for development
pre-commit install
pytest tests/ --cov=teehr_eval
```

### Infrastructure Deployment
```bash
# Deploy Iceberg data warehouse infrastructure
cd infrastructure/environments/dev
terraform init
terraform plan -var-file="dev.tfvars"
terraform apply

# Initialize Iceberg catalog schema
cd ../../../scripts
python init_catalog_schema.py --environment dev
```

### Cloud Development
- Use AWS profiles for environment separation (dev/staging/prod)
- Test against local Iceberg catalog before cloud deployment
- Include infrastructure tests for resource provisioning
- Monitor costs with AWS budgets and cost allocation tags

## Documentation Standards

### Function Documentation
```python
def nash_sutcliffe_efficiency(observed: pd.Series, simulated: pd.Series) -> float:
    """
    Calculate Nash-Sutcliffe Efficiency.
    
    Args:
        observed: Observed time series values
        simulated: Simulated time series values
        
    Returns:
        NSE value (-∞ to 1, where 1 is perfect)
        
    Raises:
        ValueError: If series have different lengths or no valid pairs
    """
```

### Configuration Examples
- Include working configuration examples in `examples/`
- Document parameter sensitivity and recommended ranges
- Provide templates for common evaluation scenarios

## Integration Points

### External Data Sources
- USGS NWIS API integration patterns
- NWM data access (cloud-optimized formats)
- Handle rate limiting and API failures gracefully

### Output Formats
- Support multiple export formats (CSV, NetCDF, Parquet)
- Generate publication-ready figures with consistent styling
- Provide programmatic access to all computed metrics

## Debugging & Troubleshooting

### Common Issues
- Time zone mismatches: Always work in UTC internally, convert at boundaries
- Missing data handling: Document propagation rules clearly
- Memory issues: Use chunked processing for large datasets
- Performance: Profile before optimizing, focus on I/O bottlenecks first

### Logging Strategy
- Use structured logging with evaluation context
- Log data quality issues as warnings
- Include data statistics in debug logs (record counts, date ranges)

---

*Update this file as the codebase evolves. Focus on patterns that aren't obvious from reading individual files.*