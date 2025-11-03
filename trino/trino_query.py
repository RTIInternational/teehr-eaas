#!/usr/bin/env python3
"""
Quick SQL test for ECS-hosted Trino cluster
"""

import trino
import pandas as pd
import requests
import time
from functools import wraps
import geopandas as gpd

# ECS Trino configuration
TRINO_HOST = "dev-teehr-sys-trino-1725339932.us-east-2.elb.amazonaws.com" 
TRINO_PORT = 80
TRINO_USER = "testuser"
TRINO_CATALOG = "iceberg"
TRINO_SCHEMA = "teehr"

def timer(func):
    """Decorator to time function execution."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        print(f"⏱️  Query executed in {execution_time:.3f} seconds")
        return result
    return wrapper

def connect_to_trino():
    """Create Trino connection."""
    try:
        conn = trino.dbapi.connect(
            host=TRINO_HOST,
            port=TRINO_PORT,
            user=TRINO_USER,
            catalog=TRINO_CATALOG,
            schema=TRINO_SCHEMA,
        )
        print(f"✅ Connected to Trino at {TRINO_HOST}:{TRINO_PORT}")
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to Trino: {e}")
        return None

@timer
def run_query(conn, sql):
    """Execute SQL and return DataFrame."""
    try:
        df = pd.read_sql(sql, conn)
        print(f"✅ Query returned {len(df)} rows")
        return df
    except Exception as e:
        print(f"❌ Query failed: {e}")
        return None

def run_timed_query(conn, sql, query_name="Query"):
    """Execute SQL with detailed timing information."""
    print(f"\n🔍 {query_name}")
    print("-" * 40)
    
    start_time = time.perf_counter()
    
    try:
        df = pd.read_sql(sql, conn)
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        
        print(f"✅ Success: {len(df)} rows returned")
        print(f"⏱️  Execution time: {execution_time:.3f} seconds")
        
        # Performance categorization
        if execution_time < 1.0:
            print("🚀 Performance: Excellent (< 1s)")
        elif execution_time < 5.0:
            print("✅ Performance: Good (< 5s)")
        elif execution_time < 10.0:
            print("⚠️  Performance: Moderate (< 10s)")
        else:
            print("🐌 Performance: Slow (> 10s)")
        
        return df
        
    except Exception as e:
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        print(f"❌ Query failed after {execution_time:.3f} seconds: {e}")
        return None

def test_connection():
    """Test basic connectivity to Trino coordinator."""
    print(f"🔍 Testing connection to ECS Trino: {TRINO_HOST}:{TRINO_PORT}")
    
    try:
        # Test basic HTTP connectivity to coordinator
        response = requests.get(f"http://{TRINO_HOST}:{TRINO_PORT}/v1/info", timeout=10)
        if response.status_code == 200:
            print("✅ Trino coordinator is responding")
            info = response.json()
            print(f"   Version: {info.get('nodeVersion', {}).get('version', 'unknown')}")
            print(f"   Environment: {info.get('environment', 'unknown')}")
            return True
        else:
            print(f"⚠️  Trino responded with status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot reach Trino coordinator: {e}")
        return False

# =================================================================
# MAIN SCRIPT - MODIFY YOUR QUERIES HERE
# =================================================================
if __name__ == "__main__":
    
    print("🚀 TEEHR ECS Trino Connection Test")
    print("=" * 50)
    
    # Test basic connectivity first
    if not test_connection():
        print("\n❌ Basic connectivity test failed. Check:")
        print("   1. ECS services are running")
        print("   2. Load balancer is healthy")
        print("   3. Security groups allow traffic")
        print("   4. Trino configuration is properly loaded")
        exit(1)
    
    # Try SQL connection
    print(f"\n🔗 Attempting SQL connection...")
    conn = connect_to_trino()
    if not conn:
        print("\n❌ SQL connection failed. This might be because:")
        print("   1. Trino services haven't finished starting")
        print("   2. Configuration files are missing from EFS")
        print("   3. Iceberg catalog connection isn't working")
        exit(1)
    
    # =================================================================
    # YOUR CUSTOM QUERIES - MODIFY THESE SECTIONS
    # =================================================================
    
    # Query 1: Test basic functionality
    sql1 = """
    SELECT 'ECS Trino is working!' as message, current_timestamp as test_time
    """
    result1 = run_timed_query(conn, sql1, "QUERY 1: Testing basic Trino functionality")
    if result1 is not None:
        print(result1)
    
    # Query 2: Test geospatial functions with proper WKB conversion
    # sql2 = """
    # WITH metrics AS (
    #     SELECT
    #         pt.location_id,
    #         count(*) as record_count
    #     FROM iceberg.teehr.primary_timeseries pt
    #     GROUP BY pt.location_id
    # )
    # SELECT
    #     m.record_count,
    #     ST_GeomFromBinary(l.geometry) as geometry
    # FROM metrics m
    # JOIN iceberg.teehr.locations l
    # ON m.location_id = l.id
    # LIMIT 5
    # """
    # sql2 = """
    # DROP TABLE IF EXISTS iceberg.teehr.location_metrics_table
    # """

    # sql2 = """
    # CREATE TABLE IF NOT EXISTS iceberg.teehr.location_metrics_table
    # WITH (
    #     format = 'PARQUET',
    #     partitioning = ARRAY['record_count_bucket']
    # ) AS
    # SELECT
    #     l.id as location_id,
    #     l.name as location_name,
    #     COALESCE(m.record_count, 0) as record_count,
    #     -- Use proper Iceberg timestamp format with timezone
    #     COALESCE(m.earliest_record, CAST(NULL AS timestamp(6) with time zone)) as earliest_record,
    #     COALESCE(m.latest_record, CAST(NULL AS timestamp(6) with time zone)) as latest_record,
    #     -- Extract coordinates safely using TRY for error handling
    #     TRY(ST_X(ST_GeomFromBinary(l.geometry))) as longitude,
    #     TRY(ST_Y(ST_GeomFromBinary(l.geometry))) as latitude,
    #     -- Keep original WKB geometry for full geospatial operations
    #     l.geometry as geometry_wkb,
    #     -- Partitioning column for query performance
    #     CASE 
    #         WHEN COALESCE(m.record_count, 0) < 1000 THEN 'low'
    #         WHEN COALESCE(m.record_count, 0) < 10000 THEN 'medium'
    #         ELSE 'high'
    #     END as record_count_bucket,
    #     -- Use proper Iceberg timestamp format
    #     CAST(current_timestamp AS timestamp(6) with time zone) as created_at
    # FROM iceberg.teehr.locations l
    # LEFT JOIN (
    #     SELECT
    #         pt.location_id,
    #         COUNT(*) as record_count,
    #         -- Ensure aggregated timestamps use proper format
    #         CAST(MIN(pt.value_time) AS timestamp(6) with time zone) as earliest_record,
    #         CAST(MAX(pt.value_time) AS timestamp(6) with time zone) as latest_record
    #     FROM iceberg.teehr.primary_timeseries pt
    #     WHERE pt.variable_name = 'hourly_streamflow_inst'
    #     GROUP BY pt.location_id
    # ) m ON l.id = m.location_id
    # """

    # sql2 = """
    # SELECT 
    #     *
    # FROM iceberg.teehr.location_metrics_table
    # LIMIT 5
    # """

    # gdf = gpd.read_postgis(sql2, conn, geom_col='geometry_wkb', crs='EPSG:4326')
    # print(gdf.geometry)

    # result2 = run_timed_query(conn, sql2, "QUERY 2: Locations with geometry (WKT format)")
    # if result2 is not None:
    #     first_row = result2.iloc[0]
    #     for column, value in first_row.items():
    #         print(f"{column}: {value}")   

    sql3 = """
        SELECT location_id, count(*) as record_count 
        FROM iceberg.teehr.primary_timeseries
        GROUP BY location_id
        ORDER BY record_count
    """
    result3 = run_timed_query(conn, sql3, "QUERY 3: Location record counts")
    if result3 is not None:
        print(result3)