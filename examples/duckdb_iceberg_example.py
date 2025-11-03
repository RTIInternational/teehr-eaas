#!/usr/bin/env python3
"""
TEEHR Iceberg Data Warehouse with DuckDB Query Engine
=====================================================
Demonstrates using DuckDB to query Iceberg tables for hydrologic evaluation.
DuckDB provides excellent performance for analytical queries and is easy to set up.
"""

import pandas as pd
from datetime import datetime, timedelta
import subprocess
import json
from pathlib import Path
import os

try:
    import duckdb
except ImportError:
    print("❌ Missing DuckDB. Install with:")
    print("pip install duckdb")
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

def setup_duckdb_with_iceberg():
    """Set up DuckDB with Iceberg extension for TEEHR data warehouse."""
    
    # Create DuckDB connection
    conn = duckdb.connect(':memory:')  # or use persistent DB: duckdb.connect('teehr.db')
    
    # Install and load required extensions
    print("📦 Installing DuckDB extensions...")
    try:
        conn.execute("INSTALL iceberg")
        conn.execute("LOAD iceberg")
        conn.execute("INSTALL aws")
        conn.execute("LOAD aws")
        print("✅ Extensions loaded successfully")
    except Exception as e:
        print(f"⚠️ Extension loading failed: {e}")
        print("Note: DuckDB Iceberg extension is experimental")
    
    # Configure AWS credentials for S3 access
    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    aws_region = os.getenv('AWS_DEFAULT_REGION', 'us-east-2')
    
    if aws_access_key and aws_secret_key:
        conn.execute(f"""
            CREATE SECRET aws_secret (
                TYPE S3,
                KEY_ID '{aws_access_key}',
                SECRET '{aws_secret_key}',
                REGION '{aws_region}'
            )
        """)
        print("✅ AWS credentials configured")
    else:
        print("⚠️ AWS credentials not found in environment")
    
    return conn

def query_iceberg_with_duckdb_direct():
    """Query Iceberg tables directly using DuckDB's S3 capabilities."""
    
    conn = setup_duckdb_with_iceberg()
    warehouse_bucket = "dev-teehr-sys-iceberg-warehouse"
    
    # Since DuckDB's Iceberg support is limited, we can query Parquet files directly
    queries = {
        "explore_warehouse": f"""
            SELECT * FROM read_parquet('s3://{warehouse_bucket}/warehouse/teehr/locations/data/*.parquet')
            LIMIT 5
        """,
        
        "location_analysis": f"""
            WITH location_data AS (
                SELECT * FROM read_parquet('s3://{warehouse_bucket}/warehouse/teehr/primary_timeseries/data/*.parquet')
            )
            SELECT 
                location_id,
                configuration,
                COUNT(*) as record_count,
                MIN(value) as min_value,
                MAX(value) as max_value,
                AVG(value) as avg_value,
                STDDEV(value) as std_value
            FROM location_data
            GROUP BY location_id, configuration
            ORDER BY location_id, configuration
        """,
        
        "time_series_analytics": f"""
            WITH ts_data AS (
                SELECT 
                    location_id,
                    configuration,
                    value_time,
                    value,
                    -- DuckDB has excellent window function support
                    LAG(value, 1) OVER (PARTITION BY location_id, configuration ORDER BY value_time) as prev_value,
                    LEAD(value, 1) OVER (PARTITION BY location_id, configuration ORDER BY value_time) as next_value,
                    AVG(value) OVER (
                        PARTITION BY location_id, configuration 
                        ORDER BY value_time 
                        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
                    ) as rolling_7day_avg
                FROM read_parquet('s3://{warehouse_bucket}/warehouse/teehr/primary_timeseries/data/*.parquet')
            )
            SELECT 
                location_id,
                configuration,
                value_time,
                value,
                prev_value,
                rolling_7day_avg,
                -- Calculate flow changes
                CASE 
                    WHEN prev_value IS NOT NULL THEN value - prev_value 
                    ELSE 0 
                END as flow_change
            FROM ts_data
            WHERE value_time >= CURRENT_DATE - INTERVAL 30 DAY
            ORDER BY location_id, configuration, value_time
        """,
        
        "advanced_aggregations": f"""
            SELECT 
                location_id,
                configuration,
                EXTRACT(year FROM value_time) as year,
                EXTRACT(month FROM value_time) as month,
                
                -- Statistical measures
                COUNT(*) as observations,
                AVG(value) as mean_flow,
                MEDIAN(value) as median_flow,
                PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY value) as q25,
                PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY value) as q75,
                MAX(value) as peak_flow,
                MIN(value) as low_flow,
                
                -- Hydrologic measures
                COUNT(CASE WHEN value > PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY value) THEN 1 END) as high_flow_days,
                COUNT(CASE WHEN value < PERCENTILE_CONT(0.05) WITHIN GROUP (ORDER BY value) THEN 1 END) as low_flow_days
                
            FROM read_parquet('s3://{warehouse_bucket}/warehouse/teehr/primary_timeseries/data/*.parquet')
            GROUP BY location_id, configuration, EXTRACT(year FROM value_time), EXTRACT(month FROM value_time)
            ORDER BY location_id, configuration, year, month
        """
    }
    
    results = {}
    
    for query_name, sql in queries.items():
        try:
            print(f"\n📊 Executing {query_name} with DuckDB...")
            result = conn.execute(sql).fetchdf()
            results[query_name] = result
            
            print(f"✅ Retrieved {len(result)} rows")
            if len(result) > 0:
                print("Sample results:")
                print(result.head().to_string(index=False))
                
        except Exception as e:
            print(f"❌ Failed to execute {query_name}: {e}")
            results[query_name] = None
    
    conn.close()
    return results

def create_duckdb_analysis_functions():
    """Create custom analysis functions for TEEHR in DuckDB."""
    
    conn = setup_duckdb_with_iceberg()
    
    # Create custom functions for hydrologic analysis
    custom_functions = """
    -- Nash-Sutcliffe Efficiency function
    CREATE OR REPLACE MACRO nash_sutcliffe(observed, simulated) AS (
        1 - (SUM((observed - simulated) * (observed - simulated)) / 
             SUM((observed - AVG(observed)) * (observed - AVG(observed))))
    );
    
    -- Root Mean Square Error
    CREATE OR REPLACE MACRO rmse(observed, simulated) AS (
        SQRT(AVG((observed - simulated) * (observed - simulated)))
    );
    
    -- Percent Bias
    CREATE OR REPLACE MACRO pbias(observed, simulated) AS (
        100 * (SUM(simulated - observed) / SUM(observed))
    );
    
    -- Flow Duration Curve percentile
    CREATE OR REPLACE MACRO flow_percentile(flow_values, percentile) AS (
        PERCENTILE_CONT(percentile / 100.0) WITHIN GROUP (ORDER BY flow_values DESC)
    );
    """
    
    try:
        conn.execute(custom_functions)
        print("✅ Created custom hydrologic analysis functions")
        
        # Example usage
        warehouse_bucket = "dev-teehr-sys-iceberg-warehouse"
        example_query = f"""
        WITH paired_data AS (
            SELECT 
                o.location_id,
                o.value_time,
                o.value as observed,
                s.value as simulated
            FROM read_parquet('s3://{warehouse_bucket}/warehouse/teehr/primary_timeseries/data/*.parquet') o
            JOIN read_parquet('s3://{warehouse_bucket}/warehouse/teehr/secondary_timeseries/data/*.parquet') s
                ON o.location_id = s.location_id 
                AND o.value_time = s.value_time
            WHERE o.location_id = 'USGS-01646500'  -- Example location
        )
        SELECT 
            location_id,
            COUNT(*) as pairs,
            nash_sutcliffe(observed, simulated) as nse,
            rmse(observed, simulated) as rmse_value,
            pbias(observed, simulated) as bias_percent,
            flow_percentile(observed, 95) as q95_observed,
            flow_percentile(simulated, 95) as q95_simulated
        FROM paired_data
        GROUP BY location_id
        """
        
        print("\n🧮 Example evaluation metrics query:")
        print(example_query)
        
    except Exception as e:
        print(f"⚠️ Function creation failed: {e}")
    
    conn.close()

def benchmark_query_engines():
    """Benchmark different approaches for TEEHR Iceberg queries."""
    
    print("\n⚡ Query Engine Performance Comparison")
    print("=" * 50)
    
    engines = {
        "PySpark": {
            "Setup": "Complex (JVM, cluster config)",
            "Query Speed": "★★★★☆ (excellent for large data)",
            "Memory Usage": "★★☆☆☆ (high JVM overhead)",
            "SQL Features": "★★★★☆ (good SQL support)",
            "Iceberg Support": "★★★★★ (native, full featured)",
            "Best For": "Large-scale ETL, distributed processing",
            "Cons": "Heavy setup, slow startup"
        },
        
        "DuckDB": {
            "Setup": "★★★★★ (pip install)",
            "Query Speed": "★★★★★ (very fast for analytics)",
            "Memory Usage": "★★★★★ (very efficient)",
            "SQL Features": "★★★★★ (advanced analytics)",
            "Iceberg Support": "★★☆☆☆ (experimental, limited)",
            "Best For": "Interactive analysis, local development",
            "Cons": "Limited Iceberg integration"
        },
        
        "Trino": {
            "Setup": "★★★☆☆ (Docker/cluster needed)",
            "Query Speed": "★★★★★ (excellent for complex queries)",
            "Memory Usage": "★★★☆☆ (moderate)",
            "SQL Features": "★★★★★ (full ANSI SQL)",
            "Iceberg Support": "★★★★★ (excellent integration)",
            "Best For": "Interactive analytics, complex joins",
            "Cons": "Requires infrastructure setup"
        },
        
        "PyIceberg": {
            "Setup": "★★★★★ (simple pip install)",
            "Query Speed": "★★★☆☆ (good for filtered queries)",
            "Memory Usage": "★★★★☆ (efficient)",
            "SQL Features": "★★☆☆☆ (limited, Python-based)",
            "Iceberg Support": "★★★★★ (native Python client)",
            "Best For": "Python workflows, simple queries",
            "Cons": "Limited SQL capabilities"
        },
        
        "AWS Athena": {
            "Setup": "★★★★★ (serverless)",
            "Query Speed": "★★★☆☆ (variable)",
            "Memory Usage": "★★★★★ (serverless)",
            "SQL Features": "★★★★☆ (standard SQL)",
            "Iceberg Support": "★★★★☆ (good AWS integration)",
            "Best For": "Ad-hoc queries, occasional use",
            "Cons": "Pay per query, slower for frequent use"
        }
    }
    
    for engine, metrics in engines.items():
        print(f"\n🔧 {engine}")
        print("-" * (len(engine) + 3))
        for metric, value in metrics.items():
            print(f"  {metric:15}: {value}")

def main():
    """Demonstrate DuckDB integration with TEEHR Iceberg."""
    print("🦆 TEEHR Iceberg Data Warehouse with DuckDB")
    print("=" * 60)
    
    try:
        # 1. Setup demonstration
        print("\n1️⃣ Setting up DuckDB with Iceberg support...")
        conn = setup_duckdb_with_iceberg()
        print("✅ DuckDB configured for S3 access")
        conn.close()
        
        # 2. Create custom functions
        print("\n2️⃣ Creating hydrologic analysis functions...")
        create_duckdb_analysis_functions()
        
        # 3. Performance comparison
        print("\n3️⃣ Query engine benchmarking...")
        benchmark_query_engines()
        
        # 4. Recommendations
        print("\n4️⃣ Recommendations for TEEHR:")
        print("🎯 For Interactive Development: DuckDB + direct Parquet access")
        print("🎯 For Production Analytics: Trino with Iceberg connector")
        print("🎯 For Large-scale ETL: PySpark with Iceberg")
        print("🎯 For Simple Python Scripts: PyIceberg")
        print("🎯 For Occasional Queries: AWS Athena")
        
        print("\n✅ DuckDB demonstration completed!")
        print("📊 Ready for high-performance TEEHR analytics")
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()