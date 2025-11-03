#!/usr/bin/env python3
"""
TEEHR Iceberg Data Warehouse with Trino Query Engine
====================================================
Demonstrates using Trino to query Iceberg tables for hydrologic evaluation.
Trino provides excellent performance for complex analytical queries.
"""

import pandas as pd
from datetime import datetime, timedelta
import subprocess
import json
from pathlib import Path

try:
    from trino.dbapi import connect
    from trino.auth import BasicAuthentication
except ImportError:
    print("❌ Missing Trino dependencies. Install with:")
    print("pip install trino")
    exit(1)

def get_terraform_outputs():
    """Get Terraform outputs for Iceberg configuration."""
    try:
        tf_dir = Path(__file__).parent.parent / "infrastructure" / "environments" / "dev"
        result = subprocess.run(
            ["terraform", "output", "-json"], 
            cwd=tf_dir, 
            capture_output=True, 
            text=True,
            check=True
        )
        outputs = json.loads(result.stdout)
        
        catalog_endpoint = outputs["catalog_endpoint"]["value"]
        warehouse_bucket = outputs["warehouse_bucket_name"]["value"]
        warehouse_location = f"s3://{warehouse_bucket}/warehouse/"
        
        return catalog_endpoint, warehouse_location
        
    except Exception as e:
        print(f"⚠️ Could not get terraform outputs: {e}")
        # Fallback values
        return (
            "http://dev-teehr-sys-iceberg-alb-2105268770.us-east-2.elb.amazonaws.com",
            "s3://dev-teehr-sys-iceberg-warehouse/warehouse/"
        )

def create_trino_connection():
    """Create connection to Trino with Iceberg catalog configuration."""
    catalog_uri, warehouse_location = get_terraform_outputs()
    
    # Trino connection configuration
    conn = connect(
        host='localhost',  # We'll run Trino locally or via Docker
        port=8080,
        user='teehr',
        catalog='iceberg',
        schema='teehr',
        http_scheme='http',
        # For production, add authentication:
        # auth=BasicAuthentication("username", "password")
    )
    
    return conn, catalog_uri, warehouse_location

def setup_trino_docker():
    """Set up Trino with Iceberg connector via Docker."""
    catalog_uri, warehouse_location = get_terraform_outputs()
    
    # Create Trino catalog configuration for Iceberg
    catalog_config = f"""
connector.name=iceberg
iceberg.catalog.type=rest
iceberg.rest-catalog.uri={catalog_uri}
iceberg.rest-catalog.warehouse={warehouse_location}
iceberg.rest-catalog.io-impl=org.apache.iceberg.aws.s3.S3FileIO
hive.s3.aws-access-key=your-access-key
hive.s3.aws-secret-key=your-secret-key
hive.s3.region=us-east-2
"""
    
    # Create docker-compose for Trino
    docker_compose = f"""
version: '3.8'
services:
  trino:
    image: trinodb/trino:latest
    ports:
      - "8080:8080"
    environment:
      - AWS_ACCESS_KEY_ID=${{AWS_ACCESS_KEY_ID}}
      - AWS_SECRET_ACCESS_KEY=${{AWS_SECRET_ACCESS_KEY}}
      - AWS_DEFAULT_REGION=us-east-2
    volumes:
      - ./trino-config:/etc/trino/catalog
    command: /usr/lib/trino/bin/run-trino
    """
    
    print("🐳 Docker configuration for Trino + Iceberg:")
    print("1. Create trino-config/iceberg.properties with the catalog config above")
    print("2. Run: docker-compose up -d")
    print("3. Connect to Trino at http://localhost:8080")
    
    return catalog_config, docker_compose

def query_timeseries_with_trino(conn):
    """Example queries using Trino for TEEHR timeseries analysis."""
    
    queries = {
        "table_info": """
            DESCRIBE iceberg.teehr.primary_timeseries
        """,
        
        "location_summary": """
            SELECT 
                location_id,
                configuration,
                COUNT(*) as record_count,
                MIN(value) as min_value,
                MAX(value) as max_value,
                AVG(value) as avg_value,
                MIN(value_time) as start_time,
                MAX(value_time) as end_time
            FROM iceberg.teehr.primary_timeseries
            GROUP BY location_id, configuration
            ORDER BY location_id, configuration
        """,
        
        "time_series_stats": """
            WITH daily_stats AS (
                SELECT 
                    location_id,
                    configuration,
                    DATE(value_time) as date,
                    AVG(value) as daily_avg,
                    MAX(value) as daily_max,
                    MIN(value) as daily_min
                FROM iceberg.teehr.primary_timeseries
                WHERE value_time >= CURRENT_DATE - INTERVAL '30' DAY
                GROUP BY location_id, configuration, DATE(value_time)
            )
            SELECT 
                location_id,
                configuration,
                COUNT(*) as days_count,
                AVG(daily_avg) as avg_daily_flow,
                MAX(daily_max) as peak_flow,
                MIN(daily_min) as low_flow
            FROM daily_stats
            GROUP BY location_id, configuration
        """,
        
        "advanced_analytics": """
            SELECT 
                location_id,
                configuration,
                value_time,
                value,
                -- Moving averages
                AVG(value) OVER (
                    PARTITION BY location_id, configuration 
                    ORDER BY value_time 
                    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
                ) as moving_7day_avg,
                
                -- Percentile rankings
                PERCENT_RANK() OVER (
                    PARTITION BY location_id, configuration 
                    ORDER BY value
                ) as percentile_rank,
                
                -- Lag/lead for trend analysis
                LAG(value, 1) OVER (
                    PARTITION BY location_id, configuration 
                    ORDER BY value_time
                ) as prev_value,
                
                -- Seasonal decomposition (month-over-month)
                AVG(value) OVER (
                    PARTITION BY location_id, configuration, MONTH(value_time)
                ) as monthly_climatology
                
            FROM iceberg.teehr.primary_timeseries
            WHERE value_time >= CURRENT_DATE - INTERVAL '1' YEAR
            ORDER BY location_id, configuration, value_time
        """
    }
    
    results = {}
    
    for query_name, sql in queries.items():
        try:
            print(f"\n📊 Executing {query_name} query...")
            df = pd.read_sql(sql, conn)
            results[query_name] = df
            
            print(f"✅ Retrieved {len(df)} rows")
            if len(df) > 0:
                print("Sample results:")
                print(df.head().to_string(index=False))
                
        except Exception as e:
            print(f"❌ Failed to execute {query_name}: {e}")
            results[query_name] = None
    
    return results

def compare_performance_metrics():
    """Compare different query engines for TEEHR use cases."""
    
    comparison = {
        "Engine": ["PySpark", "Trino", "DuckDB", "PyIceberg", "Athena"],
        "Best For": [
            "Large-scale ETL, batch processing",
            "Interactive analytics, complex queries", 
            "Local analysis, fast aggregations",
            "Simple queries, Python workflows",
            "Ad-hoc queries, serverless"
        ],
        "Performance": [
            "Excellent for large data",
            "Very fast for complex SQL",
            "Fastest for small-medium data",
            "Good for filtered queries", 
            "Variable, serverless scaling"
        ],
        "SQL Features": [
            "Good SQL support",
            "Advanced SQL, window functions",
            "Rich SQL, analytics functions",
            "Limited SQL (via Python)",
            "Standard SQL, AWS integrations"
        ],
        "Setup Complexity": ["High", "Medium", "Low", "Low", "Very Low"],
        "Cost": ["Compute intensive", "Moderate", "Very low", "Low", "Pay per query"]
    }
    
    df = pd.DataFrame(comparison)
    print("\n🔄 Query Engine Comparison for TEEHR:")
    print(df.to_string(index=False))

def main():
    """Demonstrate Trino integration with TEEHR Iceberg."""
    print("🚀 TEEHR Iceberg Data Warehouse with Trino")
    print("=" * 60)
    
    try:
        # 1. Show setup instructions
        print("\n1️⃣ Setting up Trino with Iceberg...")
        catalog_config, docker_compose = setup_trino_docker()
        
        # 2. Performance comparison
        print("\n2️⃣ Query engine comparison:")
        compare_performance_metrics()
        
        # 3. Example connection (would work with running Trino)
        print("\n3️⃣ Example Trino queries for TEEHR:")
        print("Note: Requires running Trino instance")
        
        # Show example queries without executing
        example_queries = [
            "-- Location performance summary",
            "SELECT location_id, AVG(value) as mean_flow FROM iceberg.teehr.primary_timeseries GROUP BY location_id;",
            "",
            "-- Time series with window functions", 
            "SELECT location_id, value_time, value,",
            "       LAG(value) OVER (PARTITION BY location_id ORDER BY value_time) as prev_value",
            "FROM iceberg.teehr.primary_timeseries;",
            "",
            "-- Complex aggregations with filtering",
            "SELECT location_id, YEAR(value_time) as year,",
            "       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY value) as median_flow",
            "FROM iceberg.teehr.primary_timeseries",
            "WHERE value > 0 GROUP BY location_id, YEAR(value_time);"
        ]
        
        for line in example_queries:
            print(line)
            
        print("\n✅ Trino setup instructions provided!")
        print("🔗 Next steps:")
        print("   1. Run the Docker setup")
        print("   2. Configure AWS credentials")  
        print("   3. Execute queries via Trino CLI or Python")
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()