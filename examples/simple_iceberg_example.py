#!/usr/bin/env python3
"""
Simple Iceberg Data Warehouse Example using PyIceberg
======================================================
Demonstrates basic operations with the TEEHR Iceberg catalog:
- Connecting to the catalog
- Creating tables
- Inserting data
- Querying data
"""
import os
import pandas as pd
import pyarrow as pa
from pyiceberg.catalog import load_catalog
from pyiceberg.schema import Schema
from pyiceberg.types import (
    StringType, DoubleType, TimestampType, NestedField, BooleanType
)
from datetime import datetime, timedelta
import numpy as np

# Configuration
CATALOG_URI = "http://dev-teehr-sys-iceberg-alb-1831820261.us-east-2.elb.amazonaws.com"
WAREHOUSE_LOCATION = "s3://dev-teehr-sys-iceberg-warehouse/warehouse/"

def load_iceberg_catalog():
    """Load the Iceberg REST catalog"""
    catalog_properties = {
        "uri": CATALOG_URI,
        "warehouse": WAREHOUSE_LOCATION,
    }
    
    print(f"📡 Catalog URI: {CATALOG_URI}")
    print(f"🪣 Warehouse: {WAREHOUSE_LOCATION}")
    
    catalog = load_catalog("rest", **catalog_properties)
    print(f"✅ Connected to Iceberg catalog. Namespaces: {list(catalog.list_namespaces())}")
    return catalog

def generate_sample_timeseries_data(num_locations=3, days=7):
    """Generate sample hydrologic time series data"""
    print(f"📊 Generating sample data for {num_locations} locations over {days} days")
    
    # Generate timestamps (hourly for the specified days)
    start_date = datetime(2024, 1, 1)
    timestamps = [start_date + timedelta(hours=i) for i in range(days * 24)]
    
    data = []
    for location_id in range(1, num_locations + 1):
        location_name = f"USGS-{10000000 + location_id:08d}"
        
        for timestamp in timestamps:
            # Generate realistic streamflow data (m³/s)
            base_flow = 10.0 + location_id * 5.0
            seasonal_factor = 1 + 0.3 * np.sin(2 * np.pi * timestamp.timetuple().tm_yday / 365)
            noise = np.random.normal(0, 0.1)
            
            # Observed data
            observed_value = base_flow * seasonal_factor * (1 + noise)
            data.append({
                'location_id': location_name,
                'timestamp': timestamp,
                'variable_name': 'streamflow',
                'value': observed_value,
                'unit': 'm³/s',
                'configuration': 'observed',
                'is_primary': True
            })
            
            # Simulated data (with some bias)
            simulated_value = observed_value * (1.1 + np.random.normal(0, 0.05))
            data.append({
                'location_id': location_name,
                'timestamp': timestamp,
                'variable_name': 'streamflow',
                'value': simulated_value,
                'unit': 'm³/s',
                'configuration': 'nwm_retrospective',
                'is_primary': False
            })
    
    df = pd.DataFrame(data)
    print(f"📈 Generated {len(df)} time series records")
    return df

def create_timeseries_table(catalog):
    """Create the timeseries table with proper schema"""
    table_name = "teehr.timeseries_demo"
    
    # Define schema for time series data
    schema = Schema(
        NestedField(1, "location_id", StringType(), required=True),
        NestedField(2, "timestamp", TimestampType(), required=True),
        NestedField(3, "variable_name", StringType(), required=True),
        NestedField(4, "value", DoubleType(), required=True),
        NestedField(5, "unit", StringType(), required=False),
        NestedField(6, "configuration", StringType(), required=True),
        NestedField(7, "is_primary", BooleanType(), required=False),
    )
    
    try:
        # Try to load existing table
        table = catalog.load_table(table_name)
        print(f"📋 Table {table_name} already exists")
        return table
    except:
        # Create new table if it doesn't exist
        print(f"🔨 Creating new table: {table_name}")
        table = catalog.create_table(
            identifier=table_name,
            schema=schema,
            location=f"{WAREHOUSE_LOCATION}timeseries_demo"
        )
        print(f"✅ Created table {table_name}")
        return table

def insert_data_to_table(table, df):
    """Insert DataFrame data into Iceberg table"""
    import pyarrow as pa
    
    print(f"💾 Inserting {len(df)} records into table...")
    
    # Convert timestamp to proper format with microsecond precision
    df['timestamp'] = pd.to_datetime(df['timestamp']).dt.floor('us')
    
    # Define the correct schema to match the table schema
    schema = pa.schema([
        pa.field('location_id', pa.string(), nullable=False),
        pa.field('timestamp', pa.timestamp('us'), nullable=False),
        pa.field('variable_name', pa.string(), nullable=False),
        pa.field('value', pa.float64(), nullable=False),
        pa.field('unit', pa.string(), nullable=True),
        pa.field('configuration', pa.string(), nullable=False),
        pa.field('is_primary', pa.bool_(), nullable=True),
    ])
    
    # Convert pandas DataFrame to PyArrow table with correct schema
    arrow_table = pa.Table.from_pandas(df, schema=schema)
    
    # Append data to table
    table.append(arrow_table)
    print(f"✅ Successfully inserted {len(df)} records")

def query_table_data(table):
    """Query and display data from the table"""
    print(f"🔍 Querying data from table...")
    
    # Simple scan to get all data
    df = table.scan().to_pandas()
    print(f"📊 Retrieved {len(df)} records")
    
    # Display summary statistics
    print("\n📈 Data Summary:")
    print(f"  Locations: {df['location_id'].nunique()}")
    print(f"  Configurations: {df['configuration'].unique()}")
    print(f"  Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"  Value range: {df['value'].min():.2f} to {df['value'].max():.2f} {df['unit'].iloc[0]}")
    
    # Show sample data
    print("\n🔢 Sample Records:")
    print(df.head(10).to_string(index=False))
    
    # Show aggregated statistics by configuration
    print("\n📊 Statistics by Configuration:")
    stats = df.groupby(['configuration', 'location_id'])['value'].agg(['count', 'mean', 'std']).round(2)
    print(stats.head(10).to_string())
    
    return df

def demonstrate_filtering(table):
    """Demonstrate various filtering capabilities"""
    from pyiceberg.expressions import EqualTo, And, GreaterThanOrEqual, LessThan
    
    print(f"\n🎯 Demonstrating filtering capabilities...")
    
    # Filter by configuration
    print("\n1️⃣ Filter by configuration (observed only):")
    observed_df = table.scan(
        row_filter=EqualTo("configuration", "observed")
    ).to_pandas()
    print(f"   Found {len(observed_df)} observed records")
    
    # Filter by time range
    print("\n2️⃣ Filter by time range (first 3 days):")
    from datetime import datetime
    import pyarrow as pa
    
    start_time = datetime(2024, 1, 1)
    end_time = datetime(2024, 1, 4)
    
    time_filtered_df = table.scan(
        row_filter=And(
            GreaterThanOrEqual("timestamp", start_time),
            LessThan("timestamp", end_time)
        )
    ).to_pandas()
    print(f"   Found {len(time_filtered_df)} records in time range")
    
    # Filter by location
    print("\n3️⃣ Filter by location:")
    location_df = table.scan(
        row_filter=EqualTo("location_id", "USGS-10000001")
    ).to_pandas()
    print(f"   Found {len(location_df)} records for USGS-10000001")
    
    # Combined filter
    print("\n4️⃣ Combined filter (location + configuration):")
    combined_df = table.scan(
        row_filter=And(
            EqualTo("location_id", "USGS-10000001"),
            EqualTo("configuration", "observed")
        )
    ).to_pandas()
    print(f"   Found {len(combined_df)} observed records for USGS-10000001")
    
    return observed_df, time_filtered_df, location_df

def main():
    """Main demonstration function"""
    print("🌊 Simple TEEHR Iceberg Data Warehouse Demonstration")
    print("=" * 60)
    
    try:
        # 1. Connect to catalog
        print("\n1️⃣ Connecting to Iceberg catalog...")
        catalog = load_iceberg_catalog()
        
        # 2. Create table
        print("\n2️⃣ Setting up timeseries table...")
        table = create_timeseries_table(catalog)
        
        # 3. Generate sample data
        print("\n3️⃣ Generating sample hydrologic data...")
        sample_data = generate_sample_timeseries_data(num_locations=3, days=5)
        
        # 4. Insert data
        print("\n4️⃣ Inserting data into table...")
        insert_data_to_table(table, sample_data)
        
        # 5. Query data
        print("\n5️⃣ Querying data from table...")
        df = query_table_data(table)
        
        # 6. Demonstrate filtering
        print("\n6️⃣ Demonstrating filtering capabilities...")
        observed_df, time_df, location_df = demonstrate_filtering(table)
        
        print("\n✅ Demonstration completed successfully!")
        print(f"📊 Total records processed: {len(df)}")
        print(f"📍 Unique locations: {df['location_id'].nunique()}")
        print(f"⏱️  Time range: {(df['timestamp'].max() - df['timestamp'].min()).days} days")
        
    except Exception as e:
        print(f"❌ Demonstration failed: {str(e)}")
        raise

if __name__ == "__main__":
    main()