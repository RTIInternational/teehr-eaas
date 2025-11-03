#!/usr/bin/env python3
"""
TEEHR Panel Dashboard - Fixed Version
=====================================
Interactive dashboard using Panel with proper Folium integration.
Fixed to work with standard Panel installation.
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
import io
import base64

# Enable Panel extensions (only plotly, not folium)
pn.extension('plotly')

# ECS Trino configuration
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
        LIMIT 2000
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
    
    m = folium.Map(
        location=[center_lat, center_lon], 
        zoom_start=4,
        tiles='OpenStreetMap'
    )
    
    # Add tile layer options
    folium.TileLayer('CartoDB positron', name='CartoDB Light').add_to(m)
    folium.TileLayer('CartoDB dark_matter', name='CartoDB Dark').add_to(m)
    folium.LayerControl().add_to(m)
    
    # Add markers
    for idx, row in gdf.iterrows():
        color_map = {'high': 'green', 'medium': 'orange', 'low': 'red'}
        color = color_map.get(row.get('record_count_bucket', 'low'), 'blue')
        
        popup_html = f"""
        <div style='min-width: 200px'>
            <h4>{row['location_id']}</h4>
            <p><b>{row['location_name']}</b></p>
            <hr>
            <p><b>Records:</b> {row['record_count']:,}</p>
            <p><b>Quality:</b> {row['record_count_bucket'].title()}</p>
            <p><b>Coordinates:</b> {row.geometry.y:.4f}°, {row.geometry.x:.4f}°</p>
        </div>
        """
        
        folium.CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"{row['location_id']} - {row['record_count']:,} records",
            radius=8,
            color='white',
            weight=2,
            fillColor=color,
            fillOpacity=0.8
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
            line=dict(color=colors[i % len(colors)]),
            hovertemplate='<b>%{fullData.name}</b><br>' +
                         'Time: %{x}<br>' +
                         'Flow: %{y:.2f} cfs<br>' +
                         '<extra></extra>'
        ))
    
    fig.update_layout(
        title=f'Hourly Streamflow for {location_id}',
        xaxis_title='Date/Time',
        yaxis_title='Streamflow (cfs)',
        height=400,
        hovermode='x unified'
    )
    
    return fig

# Global state for selected location
selected_location_id = None

def create_dashboard():
    """Create the main dashboard layout with improved Panel integration."""
    
    # Load data
    status = pn.pane.Markdown("🔄 Loading data from ECS Trino cluster...")
    gdf, error = load_locations_data()
    
    if error:
        status.object = f"❌ **Error**: {error}"
        return pn.template.MaterialTemplate(
            title="TEEHR Dashboard - Error",
            main=[
                pn.pane.Markdown("# 🗺️ TEEHR Locations Dashboard"),
                status,
                pn.pane.Markdown("""
                ### 🔧 Troubleshooting
                - Check ECS Trino cluster status
                - Verify location_metrics_table exists
                - Confirm network connectivity to AWS
                """)
            ]
        )
    
    status.object = f"✅ **Successfully loaded {len(gdf)} locations** from ECS Trino"
    
    # Create map HTML
    folium_map = create_map(gdf)
    map_html = folium_map._repr_html_()
    map_pane = pn.pane.HTML(map_html, height=500, sizing_mode='stretch_width')
    
    # Location selector
    location_options = [(f"{row['location_id']} - {row['location_name']}", row['location_id']) 
                       for _, row in gdf.iterrows()]
    location_select = pn.widgets.Select(
        name="📍 Select Location", 
        options=location_options[:500],  # Show top 500 by record count
        width=400
    )
    
    # Date pickers
    today = date.today()
    start_date = pn.widgets.DatePicker(
        name="📅 Start Date", 
        value=today - timedelta(days=14),
        end=today,
        width=150
    )
    end_date = pn.widgets.DatePicker(
        name="📅 End Date", 
        value=today,
        start=today - timedelta(days=365),
        end=today,
        width=150
    )
    
    # Chart pane
    chart_pane = pn.pane.Plotly(
        go.Figure().add_annotation(
            text="Select a location to view time series data",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray")
        ),
        height=400, 
        sizing_mode='stretch_width'
    )
    
    # Location details
    location_details = pn.pane.Markdown("Select a location to view details")
    
    # Stats calculation
    bounds = gdf.total_bounds if len(gdf) > 0 else [0, 0, 0, 0]
    lat_range = bounds[3] - bounds[1]
    lon_range = bounds[2] - bounds[0]
    
    high_quality = len(gdf[gdf.record_count_bucket == 'high']) if 'record_count_bucket' in gdf.columns else 0
    medium_quality = len(gdf[gdf.record_count_bucket == 'medium']) if 'record_count_bucket' in gdf.columns else 0
    low_quality = len(gdf[gdf.record_count_bucket == 'low']) if 'record_count_bucket' in gdf.columns else 0
    
    stats = pn.pane.Markdown(f"""
    ### 📊 Data Summary
    - **Total Locations**: {len(gdf):,}
    - **Geographic Span**: {lat_range:.1f}° × {lon_range:.1f}°
    - **Data Quality Distribution**:
      - 🟢 High Quality: {high_quality:,} locations
      - 🟠 Medium Quality: {medium_quality:,} locations  
      - 🔴 Low Quality: {low_quality:,} locations
    """)
    
    # Event handler for location selection
    def update_analysis(event=None):
        if not location_select.value or not start_date.value or not end_date.value:
            return
        
        # Update location details - location_select.value is just the location_id string
        selected_rows = gdf[gdf['location_id'] == location_select.value]
        if len(selected_rows) == 0:
            return
        selected_row = selected_rows.iloc[0]
        geom = selected_row.geometry
        
        location_details.object = f"""
        ### 📍 Selected Location Details
        - **Location ID**: {selected_row['location_id']}
        - **Name**: {selected_row['location_name']}
        - **Coordinates**: {geom.y:.4f}°N, {geom.x:.4f}°W
        - **Records**: {selected_row['record_count']:,}
        - **Quality**: {selected_row['record_count_bucket'].title()}
        """
        
        # Load and display time series
        chart_pane.object = go.Figure().add_annotation(
            text="🔄 Loading time series data...",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        
        ts_df, ts_error = load_timeseries(location_select.value, start_date.value, end_date.value)
        
        if ts_error:
            chart_pane.object = go.Figure().add_annotation(
                text=f"⚠️ {ts_error}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(color="orange")
            )
        else:
            chart_pane.object = create_chart(ts_df, location_select.value)
    
    # Bind events
    location_select.param.watch(update_analysis, 'value')
    start_date.param.watch(update_analysis, 'value')
    end_date.param.watch(update_analysis, 'value')
    
    # Create sidebar
    sidebar = pn.Column(
        pn.pane.Markdown(f"""
        ### 🔧 ECS Trino Configuration
        **Host**: {TRINO_HOST}  
        **Port**: {TRINO_PORT}  
        **Catalog**: {TRINO_CATALOG}  
        **Schema**: {TRINO_SCHEMA}
        """),
        "---",
        status,
        "---",
        stats,
        "---",
        location_select,
        location_details,
        "---",
        pn.pane.Markdown("### 📅 Time Series Parameters"),
        pn.Row(start_date, end_date),
        width=350,
        scroll=True
    )
    
    # Create main content
    main_content = pn.Column(
        pn.pane.Markdown("# 🗺️ TEEHR Gage Locations Dashboard"),
        pn.pane.Markdown("*Interactive dashboard powered by Panel, ECS Trino, and Apache Iceberg*"),
        "---",
        pn.pane.Markdown("### 📍 Interactive Location Map"),
        map_pane,
        "---", 
        pn.pane.Markdown("### 📈 Time Series Analysis"),
        chart_pane,
        sizing_mode='stretch_width'
    )
    
    # Create template
    template = pn.template.MaterialTemplate(
        title="TEEHR Locations Dashboard",
        sidebar=[sidebar],
        main=[main_content],
        header_background='#2596be',
    )
    
    return template

# Create the dashboard
dashboard = create_dashboard()

# Make it servable
dashboard.servable()

if __name__ == "__main__":
    dashboard.show(port=5007)