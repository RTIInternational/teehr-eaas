#!/usr/bin/env python3
"""
Quick SQL test for ECS-hosted Trino cluster
"""

import trino
import pandas as pd
import requests
import time
from functools import wraps

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
    
    # Query 2: Check available catalogs
    sql2 = """
    SHOW CATALOGS
    """
    result2 = run_timed_query(conn, sql2, "QUERY 2: Available catalogs")
    if result2 is not None:
        print(result2)

    # Query 3: Check if iceberg catalog is working
    sql3 = """
    SHOW SCHEMAS FROM iceberg
    """
    result3 = run_timed_query(conn, sql3, "QUERY 3: Iceberg catalog schemas")
    if result3 is not None:
        print(result3)

    # Query 4: If TEEHR schema exists, check tables
    sql4 = """
    SHOW TABLES FROM iceberg.teehr
    """
    result4 = run_timed_query(conn, sql4, "QUERY 4: TEEHR tables (if schema exists)")
    if result4 is not None:
        print(result4)
        
        # Query 5: If tables exist, get sample data
        if len(result4) > 0:
            sql5 = """
            SELECT 
                COUNT(*) as total_locations
            FROM iceberg.teehr.locations
            """
            result5 = run_timed_query(conn, sql5, "QUERY 5: Sample locations data")
            if result5 is not None:
                print(result5)
    
    # =================================================================
    # PERFORMANCE BENCHMARKS - DIFFERENT QUERY TYPES
    # =================================================================
    
    print("\n" + "🏁" * 25)
    print("⚡ PERFORMANCE BENCHMARK SUITE")
    print("🏁" * 25)
    
    # Quick metadata query
    metadata_sql = """
    SELECT 
        location_id, 
        COUNT(*) as record_count
    FROM iceberg.teehr.primary_timeseries 
    GROUP BY location_id
    ORDER BY record_count DESC
    LIMIT 5
    """
    metadata_result = run_timed_query(conn, metadata_sql, "BENCHMARK 1: Configuration summary")
    if metadata_result is not None:
        print(metadata_result)
    
    # Sample location data with limit
    location_sql = """
    SELECT 
        value_time,
        configuration_name,
        value,
        variable_name
    FROM 
        iceberg.teehr.primary_timeseries
    WHERE location_id = 'usgs-01315500'
    ORDER BY value_time DESC
    --LIMIT 1000
    """
    location_result = run_timed_query(conn, location_sql, "BENCHMARK 2: Recent location data (limited)")
    if location_result is not None:
        print(f"📊 Result shape: {location_result.shape}")
        if len(location_result) > 0:
            print("Most recent 3 records:")
            print(location_result.head(3))
    
    # Locations with geometry test
    geometry_sql = """
    SELECT 
        id as location_id,
        name,
        geometry
    FROM iceberg.teehr.locations 
    ORDER BY name
    LIMIT 5
    """
    geometry_result = run_timed_query(conn, geometry_sql, "BENCHMARK 3: Locations with geometry")
    if geometry_result is not None:
        print(f"📊 Sample locations with geometry:")
        print(geometry_result)
    
    print("\n" + "=" * 50)
    print("✅ ECS Trino connection test complete!")
    print(f"🌐 Trino Endpoint: http://{TRINO_HOST}:{TRINO_PORT}")
    print("📊 Check the timing results above for performance insights")
    print("=" * 50)

# =================================================================
# ECS TROUBLESHOOTING GUIDE
# =================================================================
"""
🔧 ECS Trino Troubleshooting:

1. CHECK ECS SERVICES:
   aws ecs describe-services --cluster dev-teehr-sys-trino --services dev-teehr-sys-trino-coordinator

2. CHECK TASK LOGS:
   aws logs get-log-events --log-group-name /ecs/dev-teehr-sys-trino-coordinator --log-stream-name [STREAM_NAME]

3. CHECK LOAD BALANCER HEALTH:
   aws elbv2 describe-target-health --target-group-arn [TARGET_GROUP_ARN]

4. CHECK TRINO COORDINATOR STATUS:
   curl http://dev-teehr-sys-trino-1725339932.us-east-2.elb.amazonaws.com/v1/info

5. CHECK WORKER CONNECTIVITY:
   curl http://dev-teehr-sys-trino-1725339932.us-east-2.elb.amazonaws.com/v1/node

6. RESTART SERVICES:
   aws ecs update-service --cluster dev-teehr-sys-trino --service dev-teehr-sys-trino-coordinator --force-new-deployment

COMMON ISSUES:
- Configuration files missing from EFS → Need to populate /etc/trino/
- Services not starting → Check CloudWatch logs
- Load balancer unhealthy → Check target group health
- Connection timeout → Check security groups
"""