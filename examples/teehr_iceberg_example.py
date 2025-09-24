"""
TEEHR integration with Iceberg data warehouse.

This example shows how to use TEEHR with the Iceberg-based data warehouse
for large-scale hydrologic evaluation following the TEEHR coding guidelines.
"""

import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
import pandas as pd
import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

try:
    from pyiceberg.catalog import load_catalog
    from pyiceberg.schema import Schema
    from pyiceberg.types import (
        NestedField, StringType, DoubleType, TimestampType
    )
    import pyarrow as pa
except ImportError as e:
    print(f"❌ Missing dependencies: {e}")
    print("Install with: pip install pyiceberg pyarrow")
    sys.exit(1)

# Import PySpark for production workflows
try:
    from pyspark.sql import SparkSession
    from pyspark.sql.functions import col, avg, count, stddev, min as spark_min, max as spark_max
    SPARK_AVAILABLE = True
except ImportError:
    print("⚠️ PySpark not available. Install with: pip install pyspark==4.0.0")
    SPARK_AVAILABLE = False

# Import TEEHR when available
try:
    import teehr
    TEEHR_AVAILABLE = True
except ImportError:
    print("⚠️ TEEHR not installed. Install with: pip install teehr")
    TEEHR_AVAILABLE = False


def get_terraform_outputs() -> Tuple[str, str]:
    """Get catalog configuration from terraform outputs."""
    try:
        result = subprocess.run(
            ["terraform", "output", "-json"],
            cwd=project_root / "infrastructure" / "environments" / "dev",
            capture_output=True,
            text=True,
            check=True
        )
        outputs = json.loads(result.stdout)
        
        catalog_uri = outputs["catalog_endpoint"]["value"]
        warehouse_bucket = outputs["warehouse_bucket_name"]["value"]
        warehouse_location = f"s3://{warehouse_bucket}/warehouse/"
        
        print(f"📡 Catalog URI: {catalog_uri}")
        print(f"🪣 Warehouse: {warehouse_location}")
        
        return catalog_uri, warehouse_location
        
    except Exception as e:
        print(f"⚠️ Could not get terraform outputs: {e}")
        # Fallback to your deployed endpoints
        catalog_uri = "http://dev-teehr-sys-iceberg-alb-1831820261.us-east-2.elb.amazonaws.com"
        warehouse_location = "s3://dev-teehr-sys-iceberg-warehouse/warehouse/"
        return catalog_uri, warehouse_location


def setup_iceberg_catalog():
    """Configure Iceberg catalog connection following TEEHR patterns."""
    catalog_uri, warehouse_location = get_terraform_outputs()
    
    # Standard TEEHR Iceberg catalog configuration
    catalog_config = {
        'uri': catalog_uri,
        'credential': 'default',
        'warehouse': warehouse_location
    }
    
    try:
        catalog = load_catalog("rest", **catalog_config)
        
        # Verify connection
        namespaces = catalog.list_namespaces()
        print(f"✅ Connected to Iceberg catalog. Namespaces: {namespaces}")
        
        return catalog, warehouse_location
        
    except Exception as e:
        print(f"❌ Failed to connect to Iceberg catalog: {e}")
        raise


def create_spark_session_for_iceberg(catalog_uri: str, warehouse_location: str) -> SparkSession:
    """
    Create Spark session configured for TEEHR Iceberg evaluation.
    Follows TEEHR coding guidelines for PySpark 4.0.0 + Iceberg 1.6.0.
    """
    if not SPARK_AVAILABLE:
        raise ImportError("PySpark not available. Install with: pip install pyspark==4.0.0")
    
    try:
        # Clean up any existing sessions
        if SparkSession._instantiatedSession is not None:
            SparkSession._instantiatedSession.stop()
            SparkSession._instantiatedSession = None
        
        # TEEHR standard Spark configuration for Iceberg
        spark = SparkSession.builder \
            .appName("teehr-iceberg-evaluation") \
            .master("local[*]") \
            .config("spark.driver.host", "localhost") \
            .config("spark.driver.bindAddress", "127.0.0.1") \
            .config("spark.network.timeout", "800s") \
            .config("spark.executor.heartbeatInterval", "60s") \
            .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
            .config("spark.sql.adaptive.enabled", "true") \
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
            .config("spark.jars.packages", 
                    "org.apache.iceberg:iceberg-spark-runtime-4.0_2.13:1.10.0,"
                    "org.apache.hadoop:hadoop-aws:3.4.0,"
                    "com.amazonaws:aws-java-sdk-bundle:1.12.772") \
            .config("spark.sql.catalog.iceberg", "org.apache.iceberg.spark.SparkCatalog") \
            .config("spark.sql.catalog.iceberg.type", "rest") \
            .config("spark.sql.catalog.iceberg.uri", catalog_uri) \
            .config("spark.sql.catalog.iceberg.warehouse", warehouse_location) \
            .config("spark.sql.catalog.iceberg.io-impl", "org.apache.iceberg.aws.s3.S3FileIO") \
            .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
            .getOrCreate()
        
        print(f"✅ Created Spark {spark.version} session with Iceberg support")
        return spark
        
    except Exception as e:
        print(f"❌ Failed to create Spark session: {e}")
        raise


def generate_sample_data(num_locations: int = 5, num_days: int = 30) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate sample hydrologic time series data for demonstration.
    
    Returns:
        Tuple of (observed_data, simulated_data) DataFrames
    """
    np.random.seed(42)
    
    # Generate location IDs (USGS gage format)
    locations = [f"USGS-0{8000000 + i:07d}" for i in range(num_locations)]
    
    # Generate time series
    start_date = datetime(2023, 1, 1)
    dates = [start_date + timedelta(days=i) for i in range(num_days)]
    
    observed_data = []
    simulated_data = []
    
    for location in locations:
        # Base flow with seasonal variation
        base_flow = np.random.uniform(10, 100)
        seasonal_factor = 1 + 0.3 * np.sin(np.linspace(0, 2*np.pi, num_days))
        noise = np.random.normal(0, 0.1, num_days)
        
        observed_values = base_flow * seasonal_factor * (1 + noise)
        # Simulated has some bias and different noise
        simulated_values = observed_values * np.random.uniform(0.9, 1.1) + np.random.normal(0, 2, num_days)
        
        for i, date in enumerate(dates):
            observed_data.append({
                'location_id': location,
                'timestamp': date,
                'value': max(0, observed_values[i]),  # No negative flows
                'variable_name': 'streamflow_daily_mean',
                'configuration': 'observed',
                'measurement_unit': 'cfs',
                'reference_time': date
            })
            
            simulated_data.append({
                'location_id': location,
                'timestamp': date,
                'value': max(0, simulated_values[i]),  # No negative flows
                'variable_name': 'streamflow_daily_mean',
                'configuration': 'nwm_retrospective',
                'measurement_unit': 'cfs',
                'reference_time': date
            })
    
    return pd.DataFrame(observed_data), pd.DataFrame(simulated_data)


def insert_data_with_pyspark(spark: SparkSession, df: pd.DataFrame, table_name: str):
    """Insert data into Iceberg table using PySpark."""
    try:
        # Convert pandas DataFrame to Spark DataFrame
        spark_df = spark.createDataFrame(df)
        
        print(f"📝 Inserting {len(df)} records into {table_name}")
        print(f"   Data shape: {df.shape}")
        print(f"   Columns: {list(df.columns)}")
        
        # Write to Iceberg table using Spark SQL
        spark_df.createOrReplaceTempView("temp_data")
        
        insert_sql = f"""
        INSERT INTO iceberg.{table_name}
        SELECT * FROM temp_data
        """
        
        spark.sql(insert_sql)
        print(f"✅ Successfully inserted data into {table_name}")
        
        # Verify insertion
        count_sql = f"SELECT COUNT(*) as record_count FROM iceberg.{table_name}"
        result = spark.sql(count_sql).collect()
        total_records = result[0]['record_count']
        print(f"   Total records in table: {total_records}")
        
    except Exception as e:
        print(f"❌ Failed to insert data into {table_name}: {e}")
        raise


def query_data_with_pyspark(spark: SparkSession, table_name: str, location_id: str = None):
    """Query data from Iceberg table using PySpark SQL."""
    try:
        print(f"🔍 Querying data from {table_name}")
        
        # Basic query with optional location filter
        if location_id:
            query_sql = f"""
            SELECT location_id, configuration, 
                   COUNT(*) as record_count,
                   MIN(value) as min_value,
                   MAX(value) as max_value,
                   AVG(value) as avg_value
            FROM iceberg.{table_name}
            WHERE location_id = '{location_id}'
            GROUP BY location_id, configuration
            ORDER BY configuration
            """
            print(f"   Filtering by location: {location_id}")
        else:
            query_sql = f"""
            SELECT location_id, configuration,
                   COUNT(*) as record_count,
                   MIN(value) as min_value,
                   MAX(value) as max_value,
                   AVG(value) as avg_value
            FROM iceberg.{table_name}
            GROUP BY location_id, configuration
            ORDER BY location_id, configuration
            """
        
        result_df = spark.sql(query_sql)
        
        print("📊 Query Results:")
        result_df.show(20, truncate=False)
        
        return result_df
        
    except Exception as e:
        print(f"❌ Failed to query {table_name}: {e}")
        raise


def demonstrate_time_series_operations(spark: SparkSession):
    """Demonstrate time-series specific queries on Iceberg tables."""
    try:
        print("\n🕐 Time Series Analysis Examples")
        print("-" * 40)
        
        # 1. Time range query
        print("1️⃣ Querying specific time range:")
        time_range_sql = """
        SELECT location_id, configuration, timestamp, value
        FROM iceberg.teehr.timeseries
        WHERE timestamp >= '2023-01-15' AND timestamp <= '2023-01-20'
        ORDER BY location_id, configuration, timestamp
        """
        spark.sql(time_range_sql).show(10)
        
        # 2. Daily statistics by configuration
        print("\n2️⃣ Daily averages by configuration:")
        daily_stats_sql = """
        SELECT DATE(timestamp) as date,
               configuration,
               COUNT(*) as locations_count,
               AVG(value) as daily_avg_flow,
               MIN(value) as daily_min_flow,
               MAX(value) as daily_max_flow
        FROM iceberg.teehr.timeseries
        GROUP BY DATE(timestamp), configuration
        ORDER BY date, configuration
        """
        spark.sql(daily_stats_sql).show(10)
        
        # 3. Location comparison
        print("\n3️⃣ Observed vs Simulated by location:")
        comparison_sql = """
        WITH obs AS (
            SELECT location_id, AVG(value) as observed_avg
            FROM iceberg.teehr.timeseries
            WHERE configuration = 'observed'
            GROUP BY location_id
        ),
        sim AS (
            SELECT location_id, AVG(value) as simulated_avg
            FROM iceberg.teehr.timeseries
            WHERE configuration = 'nwm_retrospective'
            GROUP BY location_id
        )
        SELECT obs.location_id,
               ROUND(obs.observed_avg, 2) as observed_avg,
               ROUND(sim.simulated_avg, 2) as simulated_avg,
               ROUND(sim.simulated_avg - obs.observed_avg, 2) as difference
        FROM obs
        JOIN sim ON obs.location_id = sim.location_id
        ORDER BY obs.location_id
        """
        spark.sql(comparison_sql).show()
        
    except Exception as e:
        print(f"❌ Time series analysis failed: {e}")
        raise


def main():
    """Main demonstration of TEEHR Iceberg data warehouse operations."""
    
    print("🌊 TEEHR Iceberg Data Warehouse with PySpark")
    print("=" * 60)
    
    try:
        # 1. Connect to Iceberg catalog
        print("1️⃣ Connecting to Iceberg catalog...")
        catalog, warehouse_location = setup_iceberg_catalog()
        catalog_uri, _ = get_terraform_outputs()
        
        # 2. Create Spark session
        print("\n2️⃣ Creating PySpark session...")
        spark = create_spark_session_for_iceberg(catalog_uri, warehouse_location)
        
        # 3. Verify table exists
        print("\n3️⃣ Verifying Iceberg tables...")
        tables_sql = "SHOW TABLES IN iceberg.teehr"
        tables_df = spark.sql(tables_sql)
        print("Available tables:")
        tables_df.show()
        
        # 4. Generate sample data
        print("\n4️⃣ Generating sample hydrologic data...")
        observed_df, simulated_df = generate_sample_data(num_locations=5, num_days=30)
        
        print(f"Generated data:")
        print(f"  - Observed: {len(observed_df)} records across {observed_df['location_id'].nunique()} locations")
        print(f"  - Simulated: {len(simulated_df)} records across {simulated_df['location_id'].nunique()} locations")
        print(f"  - Time range: {observed_df['timestamp'].min()} to {observed_df['timestamp'].max()}")
        
        # 5. Insert data
        print("\n5️⃣ Inserting data into Iceberg tables...")
        
        # Combine observed and simulated data
        all_data = pd.concat([observed_df, simulated_df], ignore_index=True)
        insert_data_with_pyspark(spark, all_data, "teehr.timeseries")
        
        # 6. Query data back
        print("\n6️⃣ Querying data from Iceberg...")
        
        # Query all data summary
        print("Summary by location and configuration:")
        query_data_with_pyspark(spark, "teehr.timeseries")
        
        # Query specific location
        sample_location = observed_df['location_id'].iloc[0]
        print(f"\nDetailed view for location {sample_location}:")
        query_data_with_pyspark(spark, "teehr.timeseries", sample_location)
        
        # 7. Demonstrate time series operations
        demonstrate_time_series_operations(spark)
        
        print("\n✅ TEEHR Iceberg PySpark demonstration completed successfully!")
        print("🚀 Data successfully stored and queried from persistent Iceberg warehouse")
        print(f"📊 Total records processed: {len(all_data)}")
        
    except Exception as e:
        print(f"❌ Demonstration failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up Spark session
        if 'spark' in locals():
            spark.stop()
            print("🧹 Spark session stopped")


if __name__ == "__main__":
    main()