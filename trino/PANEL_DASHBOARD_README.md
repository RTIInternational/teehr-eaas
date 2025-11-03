# TEEHR Panel Dashboard

Interactive Panel-based web dashboard for TEEHR hydrologic evaluation gage locations, powered by ECS-hosted Trino and Apache Iceberg.

## 🚀 Quick Start

### Option 1: Using the Launch Script
```bash
cd trino/
./run_panel.sh
```

### Option 2: Manual Setup
```bash
# Install Panel and dependencies
pip install panel folium plotly geopandas

# Run the dashboard
panel serve teehr_panel_dashboard.py --show --port 5007
```

## 🌐 Access
- **URL**: http://localhost:5007
- **Dashboard**: Interactive map and time series analysis
- **Data Source**: ECS-hosted Trino cluster with Iceberg tables

## ✨ Features

### 📍 Interactive Map
- **Location Markers**: Color-coded by data quality (green=high, orange=medium, red=low)
- **Popup Information**: Location ID, name, record count, coordinates
- **Multiple Tile Layers**: OpenStreetMap, CartoDB Light/Dark
- **Geospatial Processing**: Uses pre-extracted coordinates for performance

### 📊 Summary Statistics
- **Total Locations**: Count of available gage locations
- **Geographic Span**: Spatial extent of the dataset
- **Data Quality Breakdown**: Distribution by record count buckets

### 📈 Time Series Analysis
- **Location Selection**: Dropdown with location ID and name
- **Date Range Selection**: Start and end date pickers
- **Interactive Charts**: Plotly-based time series visualization
- **Multiple Configurations**: Separate traces for different data sources

### 🔧 System Integration
- **ECS Trino Connection**: Direct connection to cloud-hosted Trino cluster
- **Iceberg Tables**: Queries optimized location_metrics_table
- **Caching**: Panel-based caching for improved performance
- **Error Handling**: Comprehensive error messages and fallbacks

## 🏗️ Architecture

### Panel vs Streamlit Comparison

| Feature | Panel | Streamlit |
|---------|-------|-----------|
| **Reactivity** | Native reactive widgets | Page-based rerun model |
| **Caching** | `@pn.cache` decorator | `@st.cache_data` decorator |
| **Layout** | Flexible layout system | Column-based layouts |
| **Map Integration** | `pn.pane.Folium` | `st_folium` component |
| **Charts** | `pn.pane.Plotly` | `st.plotly_chart` |
| **Deployment** | `panel serve` | `streamlit run` |

### Code Structure
```
teehr_panel_dashboard.py          # Main dashboard application
├── get_trino_connection()        # ECS Trino connection management
├── load_locations_data()         # Cached location data loading
├── create_map()                  # Folium map creation
├── load_timeseries()             # Time series data queries  
├── create_chart()                # Plotly chart generation
└── create_dashboard()            # Main layout and event handling
```

### TEEHR Integration Patterns
- **Cloud-Optimized Queries**: Uses pre-extracted coordinates from location_metrics_table
- **Error Handling**: Structured error messages following TEEHR patterns
- **Performance Optimization**: Caching and query limits for responsive UI
- **Data Quality Visualization**: Color-coded markers by record count buckets

## 🔧 Configuration

### ECS Trino Settings
```python
TRINO_HOST = "dev-teehr-sys-trino-1725339932.us-east-2.elb.amazonaws.com"
TRINO_PORT = 80
TRINO_USER = "testuser"
TRINO_CATALOG = "iceberg" 
TRINO_SCHEMA = "teehr"
```

### Query Optimization
- **Location Limit**: 500 locations for map performance
- **Time Series Limit**: 10,000 records per query
- **Caching**: Location data cached until restart
- **Efficient Joins**: Uses pre-computed location_metrics_table

## 📊 Data Sources

### Tables Used
- **`iceberg.teehr.location_metrics_table`**: Pre-computed location statistics with coordinates
- **`iceberg.teehr.primary_timeseries`**: Hourly streamflow time series data

### Query Patterns
```sql
-- Location data with quality metrics
SELECT location_id, location_name, record_count, 
       longitude, latitude, record_count_bucket
FROM iceberg.teehr.location_metrics_table
WHERE longitude IS NOT NULL AND latitude IS NOT NULL
ORDER BY record_count DESC;

-- Time series data for selected location
SELECT value_time, value, configuration_name
FROM iceberg.teehr.primary_timeseries  
WHERE location_id = '{location_id}'
  AND variable_name = 'streamflow_hourly_inst'
  AND value_time >= TIMESTAMP '{start_date}'
  AND value_time <= TIMESTAMP '{end_date}';
```

## 🎯 Benefits over Streamlit

### 1. **True Reactivity**
- Panel widgets update automatically without page reloads
- Better user experience for interactive exploration
- More responsive map and chart interactions

### 2. **Advanced Layout Control**
- Flexible row/column layouts with sizing options
- Better responsive design capabilities
- More control over component positioning

### 3. **Performance**
- Native caching without state management issues
- More efficient widget updates
- Better handling of large datasets

### 4. **Extensibility**
- Easier to add custom JavaScript interactions
- Better integration with Jupyter ecosystem
- More customization options for advanced users

## 🚀 Deployment Options

### Local Development
```bash
panel serve teehr_panel_dashboard.py --dev --show
```

### Production Deployment
```bash
panel serve teehr_panel_dashboard.py --port 5007 --allow-websocket-origin your-domain.com
```

### Docker Deployment
```dockerfile
FROM python:3.10-slim
RUN pip install panel folium plotly geopandas trino
COPY teehr_panel_dashboard.py /app/
WORKDIR /app
EXPOSE 5007
CMD ["panel", "serve", "teehr_panel_dashboard.py", "--port", "5007", "--allow-websocket-origin", "*"]
```

## 🔍 Troubleshooting

### Common Issues
1. **Import Errors**: Install Panel with `pip install panel`
2. **Connection Failures**: Check ECS Trino cluster status
3. **Slow Loading**: Reduce location limit in query
4. **Chart Issues**: Verify time series data availability

### Performance Tips
- Use query limits for large datasets
- Enable caching for expensive operations
- Monitor memory usage with large location sets
- Consider pagination for extensive time series

## 📈 Future Enhancements

### Planned Features
- **Location Search**: Text-based location filtering
- **Export Capabilities**: CSV/PNG export functionality  
- **Comparison Tools**: Side-by-side location analysis
- **Real-time Updates**: WebSocket-based data refresh
- **Advanced Analytics**: Statistical summary calculations

### Integration Opportunities
- **Jupyter Integration**: Embedded notebooks for analysis
- **Custom Visualizations**: Additional chart types
- **Data Quality Tools**: Interactive data validation
- **Multi-variable Support**: Beyond streamflow analysis

---

*This Panel dashboard provides a modern, reactive alternative to Streamlit for TEEHR hydrologic evaluation workflows, leveraging Panel's advanced widget system and flexible layout capabilities.*