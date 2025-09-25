#!/usr/bin/env python3
"""
Initialize Iceberg catalog schema for TEEHR evaluation system.

This script creates the necessary Iceberg tables for storing hydrologic
time series data and metadata.
"""

import argparse
import os
from pathlib import Path

from pyiceberg.catalog import load_catalog
from pyiceberg.schema import Schema
from pyiceberg.types import (
    DoubleType,
    LongType,
    StringType,
    TimestampType,
    NestedField,
)


def create_catalog_connection(environment: str):
    """Create Iceberg catalog connection based on environment."""
    if environment == "local":
        # For local development with docker-compose
        catalog_config = {
            "uri": "http://localhost:8181",
            "credential": "client-credentials",
            "warehouse": "s3://test-warehouse/",
        }
    else:
        # For AWS environments - get endpoint from Terraform outputs
        import subprocess
        import json
        
        try:
            # Get the catalog endpoint from terraform output
            tf_output = subprocess.run(
                ["terraform", "output", "-json", "catalog_endpoint"],
                cwd="infrastructure/environments/dev",
                capture_output=True,
                text=True,
                check=True
            )
            catalog_uri = json.loads(tf_output.stdout)
        except subprocess.CalledProcessError:
            # Fallback to hardcoded endpoint if terraform output fails
            catalog_uri = f"http://{environment}-teehr-sys-iceberg-alb-2105268770.us-east-2.elb.amazonaws.com"
        
        catalog_config = {
            "uri": catalog_uri,
            "credential": "client-credentials", 
            "warehouse": f"s3://{environment}-teehr-sys-iceberg-warehouse/warehouse/",
        }
    
    catalog = load_catalog("rest", **catalog_config)
    return catalog


def create_timeseries_schema():
    """Define schema for time series data table."""
    return Schema(
        NestedField(1, "location_id", StringType(), required=True),
        NestedField(2, "timestamp", TimestampType(), required=True),
        NestedField(3, "value", DoubleType(), required=True),
        NestedField(4, "variable_name", StringType(), required=True),
        NestedField(5, "configuration", StringType(), required=False),
        NestedField(6, "measurement_unit", StringType(), required=False),
        NestedField(7, "reference_time", TimestampType(), required=False),
    )


def create_locations_schema():
    """Define schema for location metadata table."""
    return Schema(
        NestedField(1, "location_id", StringType(), required=True),
        NestedField(2, "name", StringType(), required=False),
        NestedField(3, "latitude", DoubleType(), required=False),
        NestedField(4, "longitude", DoubleType(), required=False),
        NestedField(5, "drainage_area", DoubleType(), required=False),
        NestedField(6, "state", StringType(), required=False),
        NestedField(7, "country", StringType(), required=False),
    )


def create_configurations_schema():
    """Define schema for model configuration metadata."""
    return Schema(
        NestedField(1, "configuration", StringType(), required=True),
        NestedField(2, "configuration_name", StringType(), required=False),
        NestedField(3, "configuration_description", StringType(), required=False),
        NestedField(4, "variable_name", StringType(), required=True),
        NestedField(5, "variable_description", StringType(), required=False),
        NestedField(6, "measurement_unit", StringType(), required=False),
    )


def initialize_schema(catalog, environment: str):
    """Initialize all tables in the catalog."""
    
    namespace = "teehr"
    
    # Create namespace if it doesn't exist
    try:
        catalog.create_namespace(namespace)
        print(f"Created namespace: {namespace}")
    except Exception as e:
        print(f"Namespace {namespace} may already exist: {e}")
    
    # Table definitions
    tables = {
        "timeseries": {
            "schema": create_timeseries_schema(),
            "description": "Time series data for observed and simulated values"
        },
        "locations": {
            "schema": create_locations_schema(),
            "description": "Location metadata and geographic information"
        },
        "configurations": {
            "schema": create_configurations_schema(), 
            "description": "Model configuration and variable metadata"
        }
    }
    
    # Create tables
    for table_name, table_def in tables.items():
        table_identifier = f"{namespace}.{table_name}"
        
        try:
            # Check if table exists
            table = catalog.load_table(table_identifier)
            print(f"⚠️  Table {table_identifier} already exists")
        except Exception:
            # Create table
            table = catalog.create_table(
                identifier=table_identifier,
                schema=table_def["schema"],
                properties={
                    "write.format.default": "parquet",
                    "write.parquet.compression-codec": "zstd",
                }
            )
            print(f"✅ Created table: {table_identifier}")
    
    print(f"\n✅ Schema initialization complete for environment: {environment}")
    print(f"Tables created in namespace: {namespace}")


def main():
    parser = argparse.ArgumentParser(description="Initialize Iceberg catalog schema")
    parser.add_argument(
        "--environment",
        default="local",
        help="Environment (local, dev, staging, prod)"
    )
    
    args = parser.parse_args()
    
    try:
        catalog = create_catalog_connection(args.environment)
        initialize_schema(catalog, args.environment)
    except Exception as e:
        print(f"Error initializing schema: {e}")
        return 1
    
    return 0

def list():
    parser = argparse.ArgumentParser(description="Initialize Iceberg catalog schema")
    parser.add_argument(
        "--environment",
        default="local",
        help="Environment (local, dev, staging, prod)"
    )
    
    args = parser.parse_args()
    
    try:
        catalog = create_catalog_connection(args.environment)
        print("Catalog namespaces:", catalog.list_namespaces())
        print("Catalog tables:", catalog.list_tables(namespace="teehr"))
        print(catalog.properties)
        ts = catalog.load_table("teehr.timeseries")
        print(ts.schema())
    except Exception as e:
        print(f"Error initializing schema: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
    # exit(list())