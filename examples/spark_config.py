"""
Spark configuration for connecting to TEEHR Iceberg data warehouse.

This module provides configuration patterns for connecting PySpark to the
Iceberg REST catalog and S3-based data warehouse.
"""

from pyspark.sql import SparkSession
import os


def create_spark_session(
    catalog_uri: str,
    warehouse_location: str,
    aws_access_key_id: str = None,
    aws_secret_access_key: str = None,
    aws_region: str = "us-east-1",
    app_name: str = "teehr-iceberg"
) -> SparkSession:
    """
    Create a Spark session configured for Iceberg and S3.
    
    Args:
        catalog_uri: URI of the Iceberg REST catalog (from terraform output)
        warehouse_location: S3 location of the warehouse (s3://bucket/warehouse/)
        aws_access_key_id: AWS access key (optional if using IAM roles)
        aws_secret_access_key: AWS secret key (optional if using IAM roles)
        aws_region: AWS region
        app_name: Spark application name
        
    Returns:
        Configured SparkSession
    """
    
    builder = SparkSession.builder.appName(app_name)
    
    # Iceberg and AWS dependencies for PySpark 4.0.0
    builder = builder.config(
        "spark.jars.packages",
        "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.6.0,"
        "org.apache.hadoop:hadoop-aws:3.4.0,"
        "com.amazonaws:aws-java-sdk-bundle:1.12.772"
    )
    
    # Iceberg catalog configuration
    builder = builder.config("spark.sql.catalog.iceberg", "org.apache.iceberg.spark.SparkCatalog")
    builder = builder.config("spark.sql.catalog.iceberg.type", "rest")
    builder = builder.config("spark.sql.catalog.iceberg.uri", catalog_uri)
    builder = builder.config("spark.sql.catalog.iceberg.warehouse", warehouse_location)
    builder = builder.config("spark.sql.catalog.iceberg.io-impl", "org.apache.iceberg.aws.s3.S3FileIO")
    
    # S3 configuration
    builder = builder.config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
    builder = builder.config("spark.hadoop.fs.s3a.aws.credentials.provider", 
                           "com.amazonaws.auth.DefaultAWSCredentialsProviderChain")
    
    # Set AWS credentials if provided (for local development)
    if aws_access_key_id and aws_secret_access_key:
        builder = builder.config("spark.hadoop.fs.s3a.access.key", aws_access_key_id)
        builder = builder.config("spark.hadoop.fs.s3a.secret.key", aws_secret_access_key)
    
    # AWS region
    builder = builder.config(f"spark.hadoop.fs.s3a.endpoint.region", aws_region)
    
    # Performance optimizations
    builder = builder.config("spark.sql.adaptive.enabled", "true")
    builder = builder.config("spark.sql.adaptive.coalescePartitions.enabled", "true")
    builder = builder.config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
    
    return builder.getOrCreate()


def get_terraform_outputs() -> dict:
    """
    Get catalog configuration from terraform outputs.
    Run this from the infrastructure/environments/dev directory.
    """
    import subprocess
    import json
    
    try:
        result = subprocess.run(
            ["terraform", "output", "-json"],
            capture_output=True,
            text=True,
            check=True
        )
        outputs = json.loads(result.stdout)
        
        return {
            "catalog_uri": outputs["catalog_endpoint"]["value"],
            "warehouse_bucket": outputs["warehouse_bucket_name"]["value"],
            "warehouse_location": f"s3://{outputs['warehouse_bucket_name']['value']}/warehouse/"
        }
    except Exception as e:
        print(f"Error getting terraform outputs: {e}")
        print("Make sure you're in the infrastructure/environments/dev directory")
        return {}


# Example usage for different environments
def create_local_spark_session():
    """Create Spark session for local development (docker-compose)."""
    return create_spark_session(
        catalog_uri="http://localhost:8181",
        warehouse_location="s3a://test-warehouse/",
        aws_access_key_id="minio",
        aws_secret_access_key="minio123",
        app_name="teehr-local"
    )


def create_aws_spark_session():
    """Create Spark session for AWS environment."""
    # Get configuration from terraform outputs
    config = get_terraform_outputs()
    
    if not config:
        raise ValueError("Could not get terraform configuration")
    
    return create_spark_session(
        catalog_uri=config["catalog_uri"],
        warehouse_location=config["warehouse_location"],
        app_name="teehr-aws"
    )


def create_emr_spark_session():
    """Create Spark session optimized for EMR."""
    config = get_terraform_outputs()
    
    if not config:
        raise ValueError("Could not get terraform configuration")
    
    # EMR-specific optimizations
    builder = SparkSession.builder.appName("teehr-emr")
    
    # EMR comes with pre-installed jars, use compatible versions for PySpark 4
    builder = builder.config(
        "spark.jars.packages",
        "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.6.0"
    )
    
    # Catalog configuration
    builder = builder.config("spark.sql.catalog.iceberg", "org.apache.iceberg.spark.SparkCatalog")
    builder = builder.config("spark.sql.catalog.iceberg.type", "rest")
    builder = builder.config("spark.sql.catalog.iceberg.uri", config["catalog_uri"])
    builder = builder.config("spark.sql.catalog.iceberg.warehouse", config["warehouse_location"])
    builder = builder.config("spark.sql.catalog.iceberg.io-impl", "org.apache.iceberg.aws.s3.S3FileIO")
    
    # EMR optimizations
    builder = builder.config("spark.sql.adaptive.enabled", "true")
    builder = builder.config("spark.sql.adaptive.coalescePartitions.enabled", "true")
    builder = builder.config("spark.sql.adaptive.skewJoin.enabled", "true")
    builder = builder.config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
    
    return builder.getOrCreate()


if __name__ == "__main__":
    # Example: Create a Spark session and list tables
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "local":
        spark = create_local_spark_session()
    else:
        spark = create_aws_spark_session()
    
    # List available tables
    spark.sql("SHOW TABLES IN iceberg").show()
    
    # Example query
    spark.sql("SELECT * FROM iceberg.teehr.timeseries LIMIT 10").show()
    
    spark.stop()