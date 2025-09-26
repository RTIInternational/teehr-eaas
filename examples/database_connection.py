"""
Connect to the TEEHR Iceberg catalog PostgreSQL database using psycopg2.

This script shows how to connect to the RDS PostgreSQL instance that stores
the Iceberg catalog metadata and query the catalog tables directly.
"""

import psycopg2
import json
import subprocess
from pathlib import Path
from typing import Dict, Any
import pandas as pd


def get_database_credentials_from_terraform() -> Dict[str, str]:
    """Get database connection info from Terraform outputs and AWS Secrets Manager."""
    project_root = Path(__file__).parent.parent
    
    try:
        # Get Terraform outputs
        result = subprocess.run(
            ["terraform", "output", "-json"],
            cwd=project_root / "infrastructure" / "environments" / "dev",
            capture_output=True,
            text=True,
            check=True
        )
        outputs = json.loads(result.stdout)
        
        # Get database endpoint from outputs (if available)
        # You might need to add this to your terraform outputs
        
        # For now, construct from known pattern
        db_host = "dev-teehr-sys-catalog-db.c44zv2ftcjb4.us-east-2.rds.amazonaws.com"  # Replace with your actual endpoint
        db_port = "5432"
        db_name = "iceberg_catalog"
        db_user = "iceberg"
        
        print(f"📡 Database Host: {db_host}")
        print(f"📡 Database Port: {db_port}")
        print(f"📡 Database Name: {db_name}")
        print(f"📡 Database User: {db_user}")
        
        return {
            "host": db_host,
            "port": db_port,
            "database": db_name,
            "user": db_user
        }
        
    except Exception as e:
        print(f"⚠️ Could not get terraform outputs: {e}")
        # Fallback to your known values
        return {
            "host": "dev-teehr-sys-catalog-db.c44zv2ftcjb4.us-east-2.rds.amazonaws.com",
            "port": "5432",
            "database": "iceberg_catalog", 
            "user": "iceberg"
        }


def get_database_password_from_secrets_manager(secret_name: str = "dev-teehr-sys-catalog-db-password") -> str:
    """Get database password from AWS Secrets Manager."""
    try:
        result = subprocess.run(
            ["aws", "secretsmanager", "get-secret-value", "--secret-id", secret_name, "--query", "SecretString", "--output", "text"],
            capture_output=True,
            text=True,
            check=True
        )
        password = result.stdout.strip()
        print("🔐 Retrieved password from Secrets Manager")
        return password
    except Exception as e:
        print(f"❌ Failed to get password from Secrets Manager: {e}")
        print("💡 Make sure you have AWS CLI configured and proper permissions")
        raise


def connect_to_catalog_database() -> psycopg2.extensions.connection:
    """Connect to the Iceberg catalog PostgreSQL database."""
    try:
        # Get connection details
        db_config = get_database_credentials_from_terraform()
        password = get_database_password_from_secrets_manager()
        
        # Create connection
        connection = psycopg2.connect(
            host=db_config["host"],
            port=db_config["port"],
            database=db_config["database"],
            user=db_config["user"],
            password=password,
            connect_timeout=10
        )
        
        print("✅ Successfully connected to catalog database")
        return connection
        
    except psycopg2.Error as e:
        print(f"❌ Database connection failed: {e}")
        raise
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        raise


def explore_catalog_schema(connection: psycopg2.extensions.connection):
    """Explore the Iceberg catalog schema to understand the structure."""
    try:
        with connection.cursor() as cursor:
            print("\n🔍 Exploring catalog database schema...")
            
            # List all tables
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            
            tables = cursor.fetchall()
            print(f"📋 Found {len(tables)} tables in catalog:")
            for table in tables:
                print(f"  - {table[0]}")
            
            # Look at iceberg_tables specifically (main catalog table)
            if any('iceberg_tables' in str(table) for table in tables):
                print("\n📊 Iceberg tables registered in catalog:")
                cursor.execute("""
                    SELECT catalog_name, table_namespace, table_name, metadata_location
                    FROM iceberg_tables
                    ORDER BY catalog_name, table_namespace, table_name;
                """)
                
                catalog_tables = cursor.fetchall()
                for row in catalog_tables:
                    catalog_name, namespace, table_name, metadata_location = row
                    print(f"  - {catalog_name}.{namespace}.{table_name}")
                    print(f"    Metadata: {metadata_location}")
            
            # Look at namespaces
            if any('iceberg_namespace_properties' in str(table) for table in tables):
                print("\n🏷️  Iceberg namespaces:")
                cursor.execute("""
                    SELECT catalog_name, namespace
                    FROM iceberg_namespace_properties
                    ORDER BY catalog_name, namespace;
                """)
                
                namespaces = cursor.fetchall()
                for row in namespaces:
                    catalog_name, namespace = row
                    print(f"  - {catalog_name}.{namespace}")
    
    except psycopg2.Error as e:
        print(f"❌ Failed to explore schema: {e}")


def query_table_metadata(connection: psycopg2.extensions.connection, table_namespace: str = "teehr", table_name: str = "timeseries"):
    """Query metadata for a specific Iceberg table."""
    try:
        with connection.cursor() as cursor:
            print(f"\n🔍 Querying metadata for table: {table_namespace}.{table_name}")
            
            cursor.execute("""
                SELECT catalog_name, table_namespace, table_name, 
                       metadata_location, previous_metadata_location
                FROM iceberg_tables
                WHERE table_namespace = %s AND table_name = %s;
            """, (table_namespace, table_name))
            
            result = cursor.fetchone()
            if result:
                catalog_name, namespace, name, metadata_loc, prev_metadata_loc = result
                print(f"📋 Table: {catalog_name}.{namespace}.{name}")
                print(f"📍 Current metadata: {metadata_loc}")
                if prev_metadata_loc:
                    print(f"📍 Previous metadata: {prev_metadata_loc}")
            else:
                print(f"❌ Table {table_namespace}.{table_name} not found in catalog")
    
    except psycopg2.Error as e:
        print(f"❌ Failed to query table metadata: {e}")


def main():
    """Main function to demonstrate database connectivity."""
    print("🔌 Connecting to TEEHR Iceberg Catalog Database")
    print("=" * 60)
    
    try:
        # Connect to database
        connection = connect_to_catalog_database()
        
        # Explore the schema
        explore_catalog_schema(connection)
        
        # Query specific table metadata
        query_table_metadata(connection, "teehr", "timeseries")
        query_table_metadata(connection, "teehr", "locations")
        query_table_metadata(connection, "teehr", "configurations")
        
        print("\n✅ Database exploration completed successfully!")
        
    except Exception as e:
        print(f"❌ Database operation failed: {e}")
        return 1
    
    finally:
        if 'connection' in locals():
            connection.close()
            print("🔌 Database connection closed")
    
    return 0


if __name__ == "__main__":
    exit(main())