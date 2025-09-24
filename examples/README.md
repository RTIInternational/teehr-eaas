# TEEHR + Iceberg Data Warehouse Connection Guide

This guide shows how to connect Spark (and TEEHR) to your Iceberg data warehouse.

## Quick Start

### 1. Get Your Infrastructure Details

```bash
cd infrastructure/environments/dev
terraform output
```

You'll need:
- `catalog_endpoint`: Your ALB DNS name (e.g., `http://dev-teehr-iceberg-alb-xxx.elb.amazonaws.com`)
- `warehouse_bucket_name`: Your S3 bucket name

### 2. Install Dependencies

```bash
pip install pyspark==3.4.0 teehr
```

### 3. Basic Spark Connection

```python
from pyspark.sql import SparkSession

# Your terraform outputs
CATALOG_URI = "http://your-alb-dns-name.elb.amazonaws.com"
WAREHOUSE_LOCATION = "s3://your-bucket-name/warehouse/"

spark = SparkSession.builder \
    .appName("teehr-iceberg") \
    .config("spark.jars.packages", 
            "org.apache.iceberg:iceberg-spark-runtime-3.4_2.12:1.4.2,"
            "org.apache.hadoop:hadoop-aws:3.3.4,"
            "com.amazonaws:aws-java-sdk-bundle:1.12.367") \
    .config("spark.sql.catalog.iceberg", "org.apache.iceberg.spark.SparkCatalog") \
    .config("spark.sql.catalog.iceberg.type", "rest") \
    .config("spark.sql.catalog.iceberg.uri", CATALOG_URI) \
    .config("spark.sql.catalog.iceberg.warehouse", WAREHOUSE_LOCATION) \
    .config("spark.sql.catalog.iceberg.io-impl", "org.apache.iceberg.aws.s3.S3FileIO") \
    .getOrCreate()

# Test connection
spark.sql("SHOW TABLES IN iceberg.teehr").show()
```

## Connection Methods

### Option 1: Local Development (Docker Compose)

```python
from examples.spark_config import create_local_spark_session
spark = create_local_spark_session()
```

### Option 2: AWS Environment

```python
from examples.spark_config import create_aws_spark_session
spark = create_aws_spark_session()
```

### Option 3: EMR Clusters

```python
from examples.spark_config import create_emr_spark_session
spark = create_emr_spark_session()
```

## Working with Data

### Read Time Series Data

```python
# Load specific location and time range
df = spark.sql("""
    SELECT location_id, timestamp, value, configuration
    FROM iceberg.teehr.timeseries
    WHERE location_id = '01646500'
      AND timestamp >= '2020-01-01'
      AND timestamp < '2021-01-01'
    ORDER BY timestamp
""")

df.show()
```

### Write New Data

```python
# Example: Insert new observations
new_data = spark.createDataFrame([
    ("01646500", "2023-01-01 12:00:00", 150.5, "streamflow", "observed", "cfs", None),
    ("01646500", "2023-01-01 13:00:00", 149.2, "streamflow", "observed", "cfs", None),
], ["location_id", "timestamp", "value", "variable_name", "configuration", "measurement_unit", "reference_time"])

new_data.write \
    .mode("append") \
    .saveAsTable("iceberg.teehr.timeseries")
```

### TEEHR Integration

```python
import teehr

# Configure TEEHR to use your Spark session
teehr.set_spark_session(spark)

# Load data for evaluation
observed = spark.sql("""
    SELECT timestamp, value 
    FROM iceberg.teehr.timeseries
    WHERE location_id = '01646500' 
      AND configuration = 'observed'
      AND variable_name = 'streamflow'
    ORDER BY timestamp
""").toPandas()

simulated = spark.sql("""
    SELECT timestamp, value 
    FROM iceberg.teehr.timeseries
    WHERE location_id = '01646500' 
      AND configuration = 'nwm_retrospective'
      AND variable_name = 'streamflow'
    ORDER BY timestamp
""").toPandas()

# Evaluate with TEEHR
metrics = teehr.evaluate(
    observed=observed['value'],
    simulated=simulated['value'],
    metrics=['nash_sutcliffe_efficiency', 'kling_gupta_efficiency', 'bias']
)

print(metrics)
```

## Jupyter Notebook Setup

### Install Jupyter with PySpark

```bash
pip install jupyter pyspark[sql]==3.4.0 findspark
```

### Notebook Configuration

```python
# Cell 1: Setup
import findspark
findspark.init()

import sys
sys.path.append('/path/to/your/teehr-eval-sys/examples')
from spark_config import create_aws_spark_session

# Cell 2: Connect
spark = create_aws_spark_session()
print("Connected to Iceberg catalog")

# Cell 3: Explore
spark.sql("SHOW NAMESPACES").show()
spark.sql("SHOW TABLES IN iceberg.teehr").show()
```

## AWS IAM Permissions

Your Spark application needs these IAM permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::your-warehouse-bucket",
                "arn:aws:s3:::your-warehouse-bucket/*"
            ]
        }
    ]
}
```

## Performance Tips

### Partition Pruning
```python
# Good: Uses partition pruning
df = spark.sql("""
    SELECT * FROM iceberg.teehr.timeseries
    WHERE location_id = '01646500'  -- Partition column
      AND year(timestamp) = 2020     -- Partition column
""")

# Bad: Full table scan
df = spark.sql("SELECT * FROM iceberg.teehr.timeseries WHERE value > 100")
```

### Caching for Interactive Analysis
```python
# Cache frequently accessed data
df = spark.sql("SELECT * FROM iceberg.teehr.timeseries WHERE location_id = '01646500'")
df.cache()
df.count()  # Materialize the cache
```

### Coalesce for Small Results
```python
# For small result sets, reduce partitions
df.coalesce(1).write.mode("overwrite").parquet("s3://bucket/results/")
```

## Troubleshooting

### Common Issues

1. **"No FileSystem for scheme: s3a"**
   - Missing Hadoop AWS jars in spark.jars.packages

2. **"Catalog 'iceberg' not found"**
   - Check catalog URI and ensure ALB is accessible

3. **"Access Denied" on S3**
   - Verify AWS credentials and IAM permissions

4. **Slow queries**
   - Check partition pruning and query plan with `df.explain()`

### Debug Commands

```python
# Check Spark configuration
spark.sparkContext.getConf().getAll()

# Check available catalogs
spark.sql("SHOW CATALOGS").show()

# Explain query plan
df = spark.sql("SELECT * FROM iceberg.teehr.timeseries LIMIT 10")
df.explain(True)
```