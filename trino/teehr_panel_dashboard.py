#!/usr/bin/env python3
"""
TEEHR Panel Dashboard - Simplified Version
==========================================
Simplified interactive web dashboard for TEEHR hydrologic evaluation gage locations.
Connects to ECS-hosted Trino cluster for cloud-optimized geospatial analytics.
"""

import panel as pn
import pandas as pd
import geopandas as gpd
import folium
import trino
import plotly.graph_objects as go
import plotly.express as px
from datetime import date, timedelta
from shapely.geometry import Point

# Enable Panel extensions
pn.extension('plotly')

# ECS Trino configuration following TEEHR patterns
TRINO_HOST = "dev-teehr-sys-trino-1725339932.us-east-2.elb.amazonaws.com"
TRINO_PORT = 80
TRINO_USER = "testuser" 
TRINO_CATALOG = "iceberg"
TRINO_SCHEMA = "teehr"

def get_trino_connection():
    """Create Trino connection following TEEHR cloud-native patterns."""
    try:
        conn = trino.dbapi.connect(
            host=TRINO_HOST,
            port=TRINO_PORT,
            user=TRINO_USER,
            catalog=TRINO_CATALOG,
            schema=TRINO_SCHEMA,
        )
        return conn, None
    except Exception as e:
        return None, str(e)

@pn.cache
def load_locations_data():
    """Load locations data using Trino with caching for performance."""
    conn, error = get_trino_connection()
    if not conn:
        return None, f"Trino connection failed: {error}"
    
    try:
        query = """
        SELECT 
            location_id,
            location_name,
            record_count,
            longitude,
            latitude,
            record_count_bucket
        FROM iceberg.teehr.location_metrics_table
        WHERE longitude IS NOT NULL 
          AND latitude IS NOT NULL
        ORDER BY record_count DESC
        LIMIT 500
        """
        
        df = pd.read_sql(query, conn)
        
        if df.empty:
            return None, "No location data found"
        
        # Create Point geometries
        df['geometry'] = df.apply(
            lambda row: Point(row['longitude'], row['latitude']), 
            axis=1
        )
        
        # Convert to GeoDataFrame
        gdf = gpd.GeoDataFrame(df, geometry='geometry', crs='EPSG:4326')
        
        return gdf, None
        
    except Exception as e:
        return None, f"Query failed: {str(e)}"

def create_map(gdf):
    """Create Folium map with location markers."""
    if gdf is None or len(gdf) == 0:
        center_lat, center_lon = 39.8283, -98.5795
    else:
        bounds = gdf.total_bounds
        center_lon = (bounds[0] + bounds[2]) / 2
        center_lat = (bounds[1] + bounds[3]) / 2
    
    m = folium.Map(location=[center_lat, center_lon], zoom_start=4)
    
    # Add markers
    for idx, row in gdf.iterrows():
        color_map = {'high': 'green', 'medium': 'orange', 'low': 'red'}
        color = color_map.get(row.get('record_count_bucket', 'low'), 'blue')
        
        folium.CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            popup=f"<b>{row['location_id']}</b><br>{row['location_name']}<br>Records: {row['record_count']:,}",
            tooltip=f"{row['location_id']} - {row['record_count']:,} records",
            radius=6,
            fillColor=color,
            fillOpacity=0.7
        ).add_to(m)
    
    return m

def load_timeseries(location_id, start_date, end_date):
    """Load time series data for a specific location."""
    conn, error = get_trino_connection()
    if not conn:
        return None, f"Connection failed: {error}"
    
    try:
        query = f"""
        SELECT 
            value_time,
            value,
            configuration_name
        FROM iceberg.teehr.primary_timeseries
        WHERE location_id = '{location_id}'
          AND variable_name = 'streamflow_hourly_inst'
          AND value_time >= TIMESTAMP '{start_date} 00:00:00'
          AND value_time <= TIMESTAMP '{end_date} 23:59:59'
        ORDER BY value_time, configuration_name
        LIMIT 10000
        """
        
        df = pd.read_sql(query, conn)
        if df.empty:
            return None, "No time series data found"
        
        df['value_time'] = pd.to_datetime(df['value_time'])
        return df, None
        
    except Exception as e:
        return None, f"Query failed: {str(e)}"

def create_chart(df, location_id):
    """Create time series chart."""
    fig = go.Figure()
    
    configurations = df['configuration_name'].unique()
    colors = px.colors.qualitative.Set3
    
    for i, config in enumerate(configurations):
        config_df = df[df['configuration_name'] == config]
        
        fig.add_trace(go.Scatter(
            x=config_df['value_time'],
            y=config_df['value'],
            mode='lines',
            name=config,
            line=dict(color=colors[i % len(colors)])
        ))
    
    fig.update_layout(
        title=f'Time Series for {location_id}',
        xaxis_title='Date/Time',
        yaxis_title='Streamflow (cfs)',
        height=400
    )
    
    return fig

# Create dashboard components
def create_dashboard():
    """Create the main dashboard layout."""
    
    # Load data
    status = pn.pane.Markdown("🔄 Loading data...")
    gdf, error = load_locations_data()
    
    if error:
        status.object = f"❌ **Error**: {error}"
        return pn.Column(
            pn.pane.Markdown("# TEEHR Locations Dashboard"),
            status
        )
    
    status.object = f"✅ **Loaded**: {len(gdf)} locations from ECS Trino"
    
    # Create components  
    folium_map = create_map(gdf)
    map_pane = pn.pane.HTML(folium_map._repr_html_(), height=500, sizing_mode='stretch_width')
    
    # Location selector
    location_options = [(f"{row['location_id']} - {row['location_name']}", row['location_id']) 
                       for _, row in gdf.iterrows()]
    location_select = pn.widgets.Select(
        name="Select Location", 
        options=location_options[:100],  # Limit for performance
        width=400
    )
    
    # Date pickers
    today = date.today()
    start_date = pn.widgets.DatePicker(
        name="Start Date", 
        value=today - timedelta(days=7),
        width=150
    )
    end_date = pn.widgets.DatePicker(
        name="End Date", 
        value=today,
        width=150
    )
    
    # Chart pane
    chart_pane = pn.pane.Plotly(height=400, sizing_mode='stretch_width')
    
    # Stats
    bounds = gdf.total_bounds
    stats = pn.pane.Markdown(f"""
    ### 📊 Summary
    - **Locations**: {len(gdf):,}
    - **Geographic Span**: {bounds[3]-bounds[1]:.1f}° × {bounds[2]-bounds[0]:.1f}°
    - **High Quality**: {len(gdf[gdf.record_count_bucket == 'high']):,}
    - **Medium Quality**: {len(gdf[gdf.record_count_bucket == 'medium']):,}
    - **Low Quality**: {len(gdf[gdf.record_count_bucket == 'low']):,}
    """)
    
    # Event handler for location selection
    def update_chart(event):
        if not location_select.value or not start_date.value or not end_date.value:
            return
        
        chart_pane.object = "Loading time series..."
        ts_df, ts_error = load_timeseries(location_select.value, start_date.value, end_date.value)
        
        if ts_error:
            chart_pane.object = f"Error: {ts_error}"
        else:
            chart_pane.object = create_chart(ts_df, location_select.value)
    
    # Bind events
    location_select.param.watch(update_chart, 'value')
    start_date.param.watch(update_chart, 'value')
    end_date.param.watch(update_chart, 'value')
    
    # Layout
    sidebar = pn.Column(
        pn.pane.Markdown(f"""
        ### 🔧 ECS Trino Config
        **Host**: {TRINO_HOST}  
        **Port**: {TRINO_PORT}  
        **Schema**: {TRINO_SCHEMA}
        """),
        status,
        stats,
        "---",
        location_select,
        pn.Row(start_date, end_date),
        width=350
    )
    
    main_area = pn.Column(
        pn.pane.Markdown("# 🗺️ TEEHR Locations Dashboard"),
        pn.pane.Markdown("*Interactive dashboard powered by ECS Trino and Apache Iceberg*"),
        "---",
        map_pane,
        "---",
        pn.pane.Markdown("### 📈 Time Series Analysis"),
        chart_pane,
        sizing_mode='stretch_width'
    )
    
    return pn.Row(sidebar, main_area, sizing_mode='stretch_width')

# Create the app
dashboard = create_dashboard()

# For Panel serve
dashboard.servable()

if __name__ == "__main__":
    dashboard.show(port=5007)