#!/usr/bin/env python3
"""
TEEHR Locations Map - Interactive Dashboard using ECS-hosted Trino
"""
import streamlit as st
import pandas as pd
import geopandas as gpd
import trino
from shapely import wkb
import folium
from streamlit_folium import st_folium
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
import os

# ECS Trino Configuration
TRINO_HOST = "dev-teehr-sys-trino-1725339932.us-east-2.elb.amazonaws.com"
TRINO_PORT = 80
TRINO_USER = "testuser"
TRINO_CATALOG = "iceberg"
TRINO_SCHEMA = "teehr"

# Configure Streamlit page
st.set_page_config(
    page_title="TEEHR Gage Locations Map",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_resource
def get_trino_connection():
    """Get Trino connection (cached as resource)."""
    try:
        conn = trino.dbapi.connect(
            host=TRINO_HOST,
            port=TRINO_PORT,
            user=TRINO_USER,
            catalog=TRINO_CATALOG,
            schema=TRINO_SCHEMA
        )
        # Test the connection
        cur = conn.cursor()
        cur.execute('SELECT 1')
        cur.fetchone()
        return conn, None
    except Exception as e:
        return None, str(e)

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_locations_data_trino():
    """
    Load locations data using Trino with pre-extracted coordinates.
    
    Uses the location_metrics_table which has longitude/latitude already extracted
    to avoid WKB parsing issues and leverage cloud-optimized query performance.
    
    Returns:
        tuple: (GeoDataFrame, error_message) following TEEHR error handling patterns
    """
    conn, error = get_trino_connection()
    if not conn:
        return None, f"Trino connection failed: {error}"
    
    try:
        cur = conn.cursor()
        
        # Query the metrics table with pre-extracted coordinates
        # This follows TEEHR patterns for cloud-optimized geospatial processing
        query = """
        SELECT 
            location_id,
            location_name,
            record_count,
            longitude,
            latitude,
            record_count_bucket,
            earliest_record,
            latest_record
        FROM iceberg.teehr.location_metrics_table
        WHERE longitude IS NOT NULL 
          AND latitude IS NOT NULL
        ORDER BY record_count DESC
        """
        
        cur.execute(query)
        results = cur.fetchall()
        
        if not results:
            return None, "No location data found with valid coordinates"
        
        # Convert results to DataFrame with proper column mapping
        columns = [
            'id', 'name', 'record_count', 'longitude', 'latitude', 
            'record_count_bucket', 'earliest_record', 'latest_record'
        ]
        df = pd.DataFrame(results, columns=columns)
        
        # Create Point geometries from extracted coordinates
        # This follows TEEHR geospatial processing patterns
        from shapely.geometry import Point
        df['geometry'] = df.apply(
            lambda row: Point(row['longitude'], row['latitude']), 
            axis=1
        )
        
        # Convert to GeoDataFrame following TEEHR standards
        gdf = gpd.GeoDataFrame(
            df[['id', 'name', 'record_count', 'record_count_bucket', 
                'earliest_record', 'latest_record']],
            geometry=df['geometry'], 
            crs='EPSG:4326'  # WGS84 standard for TEEHR
        )
        
        return gdf, None
        
    except Exception as e:
        return None, f"Trino query failed: {str(e)}"

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_timeseries_data(location_id, start_date, end_date):
    """Load time series data for a specific location and date range."""
    conn, error = get_trino_connection()
    if not conn:
        return None, f"Trino connection failed: {error}"
    
    try:
        cur = conn.cursor()
        
        # Query primary_timeseries for the location with hourly_streamflow_inst
        query = f"""
        SELECT 
            value_time,
            value,
            configuration_name
        FROM iceberg.teehr.primary_timeseries
        WHERE location_id = '{location_id}'
          AND variable_name = 'streamflow_hourly_inst'
          AND value_time >= date '{start_date}'
          AND value_time < date '{end_date}' + interval '1' day
        ORDER BY value_time, configuration_name
        """
        
        cur.execute(query)
        results = cur.fetchall()
        
        if not results:
            return None, f"No time series data found for {location_id} between {start_date} and {end_date}"
        
        # Convert to DataFrame
        df = pd.DataFrame(results, columns=['value_time', 'value', 'configuration_name'])
        df['value_time'] = pd.to_datetime(df['value_time'])
        
        return df, None
        
    except Exception as e:
        return None, f"Time series query failed: {str(e)}"

def create_timeseries_chart(df, location_id, start_date, end_date):
    """Create plotly time series chart with multiple configurations as traces."""
    fig = go.Figure()
    
    # Get unique configurations
    configurations = df['configuration_name'].unique()
    
    # Color palette for different configurations
    colors = px.colors.qualitative.Set3
    
    for i, config in enumerate(configurations):
        config_data = df[df['configuration_name'] == config]
        
        fig.add_trace(go.Scatter(
            x=config_data['value_time'],
            y=config_data['value'],
            mode='lines',
            name=config,
            line=dict(color=colors[i % len(colors)]),
            hovertemplate='<b>%{fullData.name}</b><br>' +
                         'Time: %{x}<br>' +
                         'Flow: %{y:.2f} cfs<br>' +
                         '<extra></extra>'
        ))
    
    fig.update_layout(
        title=f'Hourly Streamflow for {location_id}<br><sub>{start_date} to {end_date}</sub>',
        xaxis_title='Date/Time',
        yaxis_title='Streamflow (cfs)',
        hovermode='x unified',
        showlegend=True,
        height=400,
        margin=dict(l=40, r=40, t=60, b=40)
    )
    
    return fig

def create_folium_map(gdf):
    """Create Folium map with location markers."""
    if gdf is None or len(gdf) == 0:
        # Default center if no data
        center_lat, center_lon = 39.8283, -98.5795  # Geographic center of US
    else:
        # Calculate center from GeoDataFrame geometries using vectorized operations
        # This follows TEEHR patterns for efficient geospatial processing
        bounds = gdf.total_bounds  # [minx, miny, maxx, maxy]
        center_lon = (bounds[0] + bounds[2]) / 2  # (minx + maxx) / 2
        center_lat = (bounds[1] + bounds[3]) / 2  # (miny + maxy) / 2
    
    # Create base map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=4,
        tiles='OpenStreetMap'
    )

    # Add multiple tile layers following TEEHR dashboard patterns
    folium.TileLayer('OpenStreetMap', name='OpenStreetMap').add_to(m)
    folium.TileLayer('CartoDB positron', name='CartoDB Light').add_to(m)
    folium.TileLayer('CartoDB dark_matter', name='CartoDB Dark').add_to(m)
    
    # Add markers for each location using TEEHR geospatial patterns
    for idx, row in gdf.iterrows():
        # Access geometry correctly - row is a pandas Series
        geom = row.geometry
        if geom and not geom.is_empty:
            # Color code by data quality bucket following TEEHR patterns
            color = 'blue'  # default
            if hasattr(row, 'record_count_bucket') and pd.notna(row.record_count_bucket):
                color_map = {
                    'high': 'green',    # High quality: >10k records
                    'medium': 'orange', # Medium quality: 1k-10k records
                    'low': 'red'        # Low quality: <1k records
                }
                color = color_map.get(row.record_count_bucket, 'blue')
            
            # Create rich popup with TEEHR metadata
            popup_content = f"<b>{row.id}</b><br>{row.name}"
            if hasattr(row, 'record_count') and pd.notna(row.record_count):
                popup_content += f"<br>Records: {row.record_count:,}"
            if hasattr(row, 'record_count_bucket') and pd.notna(row.record_count_bucket):
                popup_content += f"<br>Quality: {row.record_count_bucket.title()}"
            
            folium.CircleMarker(
                location=[geom.y, geom.x],
                popup=folium.Popup(popup_content, max_width=300),
                tooltip=f"{row.id} - Click for time series analysis",
                radius=8,
                color='white',
                weight=2,
                fillColor=color,
                fillOpacity=0.8
            ).add_to(m)
    
    return m

def display_summary_stats(gdf):
    """
    Display summary statistics using GeoDataFrame following TEEHR patterns.
    
    Args:
        gdf: GeoDataFrame with location data and geometries
    """
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Locations", len(gdf))
    
    with col2:
        # Count valid geometries using vectorized operations
        valid_geoms = gdf[~gdf.geometry.is_empty & gdf.geometry.notna()]
        st.metric("Valid Geometries", len(valid_geoms))
    
    with col3:
        # Calculate geographic span using GeoDataFrame bounds for optimal performance
        # This follows TEEHR patterns for efficient geospatial processing
        if len(gdf) > 0:
            bounds = gdf.total_bounds  # [minx, miny, maxx, maxy]
            lat_range = bounds[3] - bounds[1]  # maxy - miny
            lon_range = bounds[2] - bounds[0]  # maxx - minx
            st.metric("Geographic Span", f"{lat_range:.1f}° × {lon_range:.1f}°")
        else:
            st.metric("Geographic Span", "No data")

def main():
    """Main Streamlit application following TEEHR dashboard patterns."""
    st.title("🗺️ TEEHR Gage Locations Map")
    st.markdown("Interactive map showing TEEHR hydrologic evaluation gage locations (powered by ECS-hosted Trino)")
    
    # Sidebar with connection info and configuration
    with st.sidebar:
        st.header("🔧 ECS Trino Configuration")
        st.code(f"""
Host: {TRINO_HOST}
Port: {TRINO_PORT}
User: {TRINO_USER}
Catalog: {TRINO_CATALOG}
Schema: {TRINO_SCHEMA}
        """)
        
        st.header("📡 Connection Status")
        
        # Test Trino connection following TEEHR error handling patterns
        conn, conn_error = get_trino_connection()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute('SHOW TABLES FROM iceberg.teehr')
                tables = [row[0] for row in cur.fetchall()]
                st.success(f"✅ ECS Trino connected! Found {len(tables)} tables")
                
                # Display available tables for debugging
                st.write("**Available Tables:**")
                for table in sorted(tables):
                    st.write(f"• {table}")
                    
            except Exception as e:
                st.warning(f"ECS Trino connected but table listing failed: {e}")
        else:
            st.error(f"❌ ECS Trino connection failed: {conn_error}")
            
        st.header("📊 Data Management")
        if st.button("Refresh Data", type="primary"):
            st.cache_data.clear()
            st.rerun()
    
    # Main content area
    st.info("🚀 **Using ECS-hosted Trino** to query TEEHR locations from Iceberg warehouse")
    
    # Load and display data with comprehensive error handling
    with st.spinner("Loading location data from ECS Trino cluster..."):
        gdf, error = load_locations_data_trino()
    
    if error:
        st.error(f"❌ **Data Loading Failed**: {error}")
        st.markdown("### 🔧 Troubleshooting")
        st.markdown(f"""
        - **ECS Services**: Check if Trino coordinator and workers are running in AWS ECS
        - **Table Access**: Ensure `location_metrics_table` exists and has data
        - **Connection Issues**: Test `http://{TRINO_HOST}/v1/info`
        - **AWS Access**: Verify your AWS credentials and VPC connectivity
        - **Load Balancer Health**: Check if the ALB targets are healthy
        """)
        return
    
    if gdf is None or len(gdf) == 0:
        st.warning("⚠️ No location data available with valid coordinates")
        return
    
    # Display summary statistics using TEEHR patterns
    display_summary_stats(gdf)
    
    # Create and display interactive map
    st.subheader("📍 Interactive Location Map")
    
    with st.spinner("Generating interactive map with TEEHR locations..."):
        folium_map = create_folium_map(gdf)
    
    # Display map using streamlit-folium with click handling
    map_data = st_folium(
        folium_map,
        width=None,
        height=600,
        returned_objects=["last_object_clicked"]
    )
    
    # Handle location selection for time series analysis
    if map_data['last_object_clicked']:
        clicked_lat = map_data['last_object_clicked']['lat']
        clicked_lng = map_data['last_object_clicked']['lng']
        
        # Find closest location using efficient vectorized operations
        # This follows TEEHR patterns for cloud-optimized geospatial processing
        distances = ((gdf.geometry.y - clicked_lat) ** 2 + 
                    (gdf.geometry.x - clicked_lng) ** 2) ** 0.5
        closest_idx = distances.idxmin()
        closest_location = gdf.loc[closest_idx]
        
        st.subheader(f"📍 Selected Location: {closest_location.id}")
        
        # Location details with TEEHR metadata
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Name**: {closest_location.name}")
            # Access geometry correctly from the Series
            geom = closest_location.geometry
            st.write(f"**Coordinates**: {geom.y:.4f}°N, {geom.x:.4f}°W")
            if hasattr(closest_location, 'record_count') and pd.notna(closest_location.record_count):
                st.write(f"**Records**: {closest_location.record_count:,}")
            if hasattr(closest_location, 'record_count_bucket') and pd.notna(closest_location.record_count_bucket):
                st.write(f"**Quality**: {closest_location.record_count_bucket.title()}")
        
        with col2:
            # Date range selectors for time series analysis
            today = date.today()
            default_start = today - timedelta(days=30)
            
            start_date = st.date_input(
                "📅 Start Date",
                value=default_start,
                max_value=today
            )
            
            end_date = st.date_input(
                "📅 End Date", 
                value=today,
                min_value=start_date,
                max_value=today
            )
        
        # Load and display time series following TEEHR analysis patterns
        st.subheader("📈 Hourly Streamflow Time Series Analysis")
        
        with st.spinner(f"Loading time series data for {closest_location.id}..."):
            ts_df, ts_error = load_timeseries_data(closest_location.id, start_date, end_date)
        
        if ts_error:
            st.warning(f"⚠️ {ts_error}")
            if "No time series data found" in ts_error:
                st.info("💡 This location may not have recent streamflow data or may use a different variable name.")
        elif ts_df is not None and len(ts_df) > 0:
            # Display analysis summary following TEEHR patterns
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Records", len(ts_df))
            with col2:
                st.metric("Configurations", ts_df['configuration_name'].nunique())
            with col3:
                actual_start = ts_df['value_time'].min().strftime('%m/%d')
                actual_end = ts_df['value_time'].max().strftime('%m/%d')
                st.metric("Actual Range", f"{actual_start} - {actual_end}")
            with col4:
                st.metric("Avg Flow", f"{ts_df['value'].mean():.1f} cfs")
            
            # Create and display time series chart
            chart = create_timeseries_chart(ts_df, closest_location.id, start_date, end_date)
            st.plotly_chart(chart, use_container_width=True)
            
            # Configuration analysis summary
            config_summary = ts_df.groupby('configuration_name').agg({
                'value': ['count', 'mean', 'min', 'max'],
                'value_time': ['min', 'max']
            }).round(2)
            
            with st.expander("📊 Configuration Analysis Summary"):
                st.dataframe(config_summary, use_container_width=True)
        else:
            st.info("No time series data available for the selected time range.")
    
    # Raw data viewer for debugging and exploration
    with st.expander("📋 Raw Location Data"):
        display_df = gdf[['id', 'name']].copy()
        display_df['latitude'] = gdf.geometry.y.round(6)
        display_df['longitude'] = gdf.geometry.x.round(6)
        if 'record_count' in gdf.columns:
            display_df['record_count'] = gdf['record_count']
        if 'record_count_bucket' in gdf.columns:
            display_df['quality_bucket'] = gdf['record_count_bucket']
            
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )

if __name__ == "__main__":
    main()