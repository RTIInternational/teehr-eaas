#!/usr/bin/env python3
"""
TEEHR Locations Panel Dashboard
===============================
Interactive web dashboard for TEEHR hydrologic evaluation gage locations using Panel.
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
import numpy as np

# Enable Panel extensions
pn.extension('folium', 'plotly', 'tabulator')

# ECS Trino configuration following TEEHR patterns
TRINO_HOST = "dev-teehr-sys-trino-1725339932.us-east-2.elb.amazonaws.com"
TRINO_PORT = 80
TRINO_USER = "testuser" 
TRINO_CATALOG = "iceberg"
TRINO_SCHEMA = "teehr"

# Global variables for state management
locations_data = None
selected_location = None

def get_trino_connection():
    """
    Create Trino connection following TEEHR cloud-native patterns.
    
    Returns:
        tuple: (connection, error_message)
    """
    try:
        conn = trino.dbapi.connect(
            host=TRINO_HOST,
            port=TRINO_PORT,
            user=TRINO_USER,
            catalog=TRINO_CATALOG,
            schema=TRINO_SCHEMA,
        )
        # Test connection
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        cursor.fetchone()
        return conn, None
    except Exception as e:
        return None, str(e)

def load_locations_data():
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
        LIMIT 1000
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

def load_timeseries_data(location_id, start_date, end_date):
    """
    Load time series data for a specific location and date range.
    
    Args:
        location_id: TEEHR location identifier
        start_date: Start date for time series query
        end_date: End date for time series query
        
    Returns:
        tuple: (DataFrame, error_message)
    """
    conn, error = get_trino_connection()
    if not conn:
        return None, f"Trino connection failed: {error}"
    
    try:
        cur = conn.cursor()
        
        # Query primary_timeseries for the location with hourly streamflow
        query = f"""
        SELECT 
            value_time,
            value,
            configuration_name,
            variable_name,
            unit_name
        FROM iceberg.teehr.primary_timeseries
        WHERE location_id = '{location_id}'
          AND variable_name = 'streamflow_hourly_inst'
          AND value_time >= TIMESTAMP '{start_date} 00:00:00'
          AND value_time <= TIMESTAMP '{end_date} 23:59:59'
        ORDER BY value_time, configuration_name
        """
        
        cur.execute(query)
        results = cur.fetchall()
        
        if not results:
            return None, f"No time series data found for {location_id} in the specified date range"
        
        # Convert to DataFrame
        columns = ['value_time', 'value', 'configuration_name', 'variable_name', 'unit_name']
        df = pd.DataFrame(results, columns=columns)
        
        # Convert timestamp column to datetime
        df['value_time'] = pd.to_datetime(df['value_time'])
        
        return df, None
        
    except Exception as e:
        return None, f"Time series query failed: {str(e)}"

def create_folium_map(gdf):
    """
    Create Folium map with location markers using TEEHR visualization patterns.
    
    Args:
        gdf: GeoDataFrame with location data and geometries
        
    Returns:
        folium.Map: Interactive map centered on data extent
    """
    if gdf is None or len(gdf) == 0:
        # Default center if no data (geographic center of CONUS for TEEHR)
        center_lat, center_lon = 39.8283, -98.5795
    else:
        # Calculate center from GeoDataFrame bounds for optimal view
        # This follows TEEHR patterns for efficient geospatial processing
        bounds = gdf.total_bounds  # [minx, miny, maxx, maxy]
        center_lon = (bounds[0] + bounds[2]) / 2  # (minx + maxx) / 2
        center_lat = (bounds[1] + bounds[3]) / 2  # (miny + maxy) / 2
    
    # Create base map with multiple tile layers for better visualization
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=4,
        tiles=None  # We'll add custom layers
    )

    # Add multiple tile layers following TEEHR dashboard patterns
    folium.TileLayer('OpenStreetMap', name='OpenStreetMap').add_to(m)
    folium.TileLayer('CartoDB positron', name='CartoDB Light').add_to(m)
    folium.TileLayer('CartoDB dark_matter', name='CartoDB Dark').add_to(m)
    
    # Add markers for each location with data quality color coding
    for idx, row in gdf.iterrows():
        geom = row.geometry
        if geom and not geom.is_empty:
            # Color code by data quality bucket following TEEHR patterns
            color_map = {
                'high': 'green',    # High quality: >10k records
                'medium': 'orange', # Medium quality: 1k-10k records
                'low': 'red'        # Low quality: <1k records
            }
            color = color_map.get(getattr(row, 'record_count_bucket', 'low'), 'blue')
            
            # Create rich popup with TEEHR metadata
            popup_content = f"""
            <div style='min-width: 200px'>
                <h4>{row.id}</h4>
                <p><b>{row.name}</b></p>
                <hr>
                <p><b>Records:</b> {getattr(row, 'record_count', 'N/A'):,}</p>
                <p><b>Quality:</b> {getattr(row, 'record_count_bucket', 'unknown').title()}</p>
                <p><b>Coordinates:</b> {geom.y:.4f}°, {geom.x:.4f}°</p>
                <button onclick="window.parent.postMessage({{type: 'location_click', location_id: '{row.id}'}}, '*')">
                    View Time Series
                </button>
            </div>
            """
            
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
    
    # Add layer control for tile selection
    folium.LayerControl().add_to(m)
    
    return m

def create_timeseries_chart(df, location_id, start_date, end_date):
    """
    Create plotly time series chart with multiple configurations as traces.
    
    Args:
        df: DataFrame with time series data
        location_id: Location identifier for chart title
        start_date: Start date for chart title
        end_date: End date for chart title
        
    Returns:
        plotly.graph_objects.Figure: Interactive time series chart
    """
    fig = go.Figure()
    
    # Get unique configurations
    configurations = df['configuration_name'].unique()
    
    # Color palette for different configurations
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
        title=f'Hourly Streamflow for {location_id}<br><sub>{start_date} to {end_date}</sub>',
        xaxis_title='Date/Time',
        yaxis_title='Streamflow (cfs)',
        hovermode='x unified',
        showlegend=True,
        height=400,
        margin=dict(l=40, r=40, t=60, b=40)
    )
    
    return fig

class TEEHRDashboard:
    """
    Main dashboard class following TEEHR architecture patterns.
    
    Implements cloud-native hydrologic evaluation dashboard with:
    - ECS Trino integration for scalable data access
    - Interactive geospatial visualization
    - Time series analysis and comparison
    - Data quality assessment and visualization
    """
    
    def __init__(self):
        """Initialize dashboard components and state."""
        self.locations_gdf = None
        self.selected_location_id = None
        self.selected_location_data = None
        
        # Initialize Panel components
        self.setup_components()
        self.load_data()
    
    def setup_components(self):
        """Setup Panel dashboard components following TEEHR UI patterns."""
        
        # Header and configuration
        self.title = pn.pane.Markdown("""
        # 🗺️ TEEHR Gage Locations Dashboard
        ### Interactive map showing TEEHR hydrologic evaluation gage locations
        **Powered by ECS-hosted Trino and Apache Iceberg**
        """)
        
        # Configuration panel
        self.config_info = pn.pane.Markdown(f"""
        ### 🔧 ECS Trino Configuration
        ```
        Host: {TRINO_HOST}
        Port: {TRINO_PORT}
        User: {TRINO_USER}
        Catalog: {TRINO_CATALOG}
        Schema: {TRINO_SCHEMA}
        ```
        """)
        
        # Status indicator
        self.status_pane = pn.pane.Markdown("🔄 **Loading connection status...**")
        
        # Data refresh button
        self.refresh_button = pn.widgets.Button(
            name="🔄 Refresh Data", 
            button_type="primary",
            width=150
        )
        self.refresh_button.on_click(self.refresh_data)
        
        # Map component
        self.map_pane = pn.pane.HTML("Loading map...", height=600)
        
        # Summary statistics
        self.stats_pane = pn.pane.Markdown("Loading statistics...")
        
        # Location selection
        self.location_selector = pn.widgets.Select(
            name="📍 Select Location",
            options=[],
            width=300
        )
        self.location_selector.param.watch(self.on_location_change, 'value')
        
        # Date range selectors
        today = date.today()
        default_start = today - timedelta(days=30)
        
        self.start_date = pn.widgets.DatePicker(
            name="📅 Start Date",
            value=default_start,
            end=today,
            width=150
        )
        
        self.end_date = pn.widgets.DatePicker(
            name="📅 End Date", 
            value=today,
            start=default_start,
            end=today,
            width=150
        )
        
        # Time series chart
        self.chart_pane = pn.pane.Plotly(height=400)
        
        # Location details
        self.location_details = pn.pane.Markdown("Select a location to view details")
        
        # Data table
        self.data_table = pn.widgets.Tabulator(pagination='remote', page_size=20, height=300)
    
    def load_data(self):
        """Load locations data from Trino following TEEHR patterns."""
        self.status_pane.object = "🔄 **Loading data from ECS Trino...**"
        
        # Test connection first
        conn, conn_error = get_trino_connection()
        if conn_error:
            self.status_pane.object = f"❌ **Connection Failed**: {conn_error}"
            return
        
        # Load locations data
        gdf, error = load_locations_data()
        if error:
            self.status_pane.object = f"❌ **Data Loading Failed**: {error}"
            return
        
        self.locations_gdf = gdf
        self.update_components()
        self.status_pane.object = f"✅ **Connected**: Loaded {len(gdf)} locations"
    
    def update_components(self):
        """Update dashboard components with loaded data."""
        if self.locations_gdf is None:
            return
        
        # Update summary statistics
        gdf = self.locations_gdf
        bounds = gdf.total_bounds
        lat_range = bounds[3] - bounds[1]
        lon_range = bounds[2] - bounds[0]
        
        self.stats_pane.object = f"""
        ### 📊 Data Summary
        - **Total Locations**: {len(gdf):,}
        - **Valid Geometries**: {len(gdf[~gdf.geometry.is_empty]):,}
        - **Geographic Span**: {lat_range:.1f}° × {lon_range:.1f}°
        - **Record Quality**: High: {len(gdf[gdf.record_count_bucket == 'high']):,}, 
          Medium: {len(gdf[gdf.record_count_bucket == 'medium']):,}, 
          Low: {len(gdf[gdf.record_count_bucket == 'low']):,}
        """
        
        # Update location selector
        location_options = [(f"{row.id} - {row.name}", row.id) for _, row in gdf.iterrows()]
        self.location_selector.options = location_options
        
        # Update map
        folium_map = create_folium_map(gdf)
        self.map_pane.object = folium_map._repr_html_()
        
        # Update data table
        display_df = gdf[['id', 'name', 'record_count', 'record_count_bucket']].copy()
        display_df['latitude'] = gdf.geometry.y.round(6)
        display_df['longitude'] = gdf.geometry.x.round(6)
        self.data_table.value = display_df
    
    def refresh_data(self, event=None):
        """Refresh data from Trino."""
        self.load_data()
    
    def on_location_change(self, event):
        """Handle location selection change."""
        if not event.new:
            return
        
        self.selected_location_id = event.new
        selected_row = self.locations_gdf[self.locations_gdf.id == event.new].iloc[0]
        
        # Update location details
        geom = selected_row.geometry
        self.location_details.object = f"""
        ### 📍 Selected Location: {selected_row.id}
        - **Name**: {selected_row.name}
        - **Coordinates**: {geom.y:.4f}°N, {geom.x:.4f}°W
        - **Records**: {selected_row.record_count:,}
        - **Quality**: {selected_row.record_count_bucket.title()}
        """
        
        # Load time series data
        self.load_timeseries()
    
    def load_timeseries(self):
        """Load time series data for selected location."""
        if not self.selected_location_id:
            return
        
        # Get date range
        start_date = self.start_date.value
        end_date = self.end_date.value
        
        # Load data
        ts_df, error = load_timeseries_data(self.selected_location_id, start_date, end_date)
        
        if error:
            self.chart_pane.object = go.Figure().add_annotation(
                text=f"No time series data available: {error}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            return
        
        # Create chart
        chart = create_timeseries_chart(ts_df, self.selected_location_id, start_date, end_date)
        self.chart_pane.object = chart
    
    def create_layout(self):
        """Create dashboard layout following TEEHR UI patterns."""
        
        # Sidebar with configuration and controls
        sidebar = pn.Column(
            self.config_info,
            self.status_pane,
            self.refresh_button,
            "---",
            self.stats_pane,
            "---",
            self.location_selector,
            self.location_details,
            pn.Row(self.start_date, self.end_date),
            width=350,
            scroll=True
        )
        
        # Main content area
        main_content = pn.Column(
            self.title,
            pn.pane.Markdown("🚀 **Using ECS-hosted Trino** to query TEEHR locations from Iceberg warehouse"),
            "---",
            pn.pane.Markdown("### 📍 Interactive Location Map"),
            self.map_pane,
            "---",
            pn.pane.Markdown("### 📈 Time Series Analysis"),
            self.chart_pane,
            "---",
            pn.pane.Markdown("### 📋 Location Data"),
            self.data_table,
            sizing_mode='stretch_width'
        )
        
        # Complete layout
        layout = pn.template.MaterialTemplate(
            title="TEEHR Locations Dashboard",
            sidebar=[sidebar],
            main=[main_content],
            header_background='#2596be',
        )
        
        return layout

def create_dashboard():
    """
    Create and return TEEHR Panel dashboard.
    
    Returns:
        Panel template with complete dashboard layout
    """
    dashboard = TEEHRDashboard()
    return dashboard.create_layout()

# Configure Panel for deployment
pn.config.sizing_mode = 'stretch_width'

# Create the dashboard
dashboard_app = create_dashboard()

# For serving the dashboard
def serve_dashboard():
    """Serve the TEEHR Panel dashboard."""
    dashboard_app.show(port=5007, allow_websocket_origin=["localhost:5007"])

if __name__ == "__main__":
    serve_dashboard()