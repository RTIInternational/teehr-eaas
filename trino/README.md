# TEEHR Trino Production Dashboard Setup

This directory contains a complete production-ready Tri```
trino/
├── docker-compose.yml          # Docker services configuration
├── setup.sh                   # Automated setup script
├── start_dashboards.sh         # Interactive dashboard launcher
├── locations_map_app.py        # Interactive map dashboard for TEEHR hydrologic evaluation dashboards.

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   Dashboard     │    │    Trino     │    │ Iceberg Catalog │
│   (Streamlit/   │───▶│   Cluster    │───▶│   (REST API)    │
│   Grafana)      │    │              │    │                 │
└─────────────────┘    └──────────────┘    └─────────────────┘
                              │                       │
                              ▼                       ▼
                       ┌──────────────┐    ┌─────────────────┐
                       │    Redis     │    │   S3 Warehouse  │
                       │   (Cache)    │    │   (Parquet)     │
                       └──────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### 1. Prerequisites

```bash
# Required software
- Docker & Docker Compose
- Python 3.8+
- AWS CLI configured

# Check prerequisites
docker --version
docker-compose --version
python3 --version
aws sts get-caller-identity
```

### 2. Environment Setup

```bash
# Set AWS credentials
export AWS_PROFILE=ciroh_mdenno
# Or set directly:
# export AWS_ACCESS_KEY_ID=your-key
# export AWS_SECRET_ACCESS_KEY=your-secret
# export AWS_DEFAULT_REGION=us-east-2

# Make setup script executable (if needed)
chmod +x setup.sh
```

### 3. Start Trino

```bash
# Automated setup
./setup.sh

# Or manual setup
docker-compose up -d
```

### 6. Launch Dashboard

```bash
# Interactive launcher (recommended)
./start_dashboards.sh

# Direct launch
streamlit run locations_map_app.py --server.port 8502
```

### 4. Install Python Dependencies

```bash
# Core packages
pip install trino pandas plotly streamlit

# Geospatial packages for mapping
pip install geopandas shapely folium streamlit-folium
```

### 5. Test Connection

```bash
# Test Trino integration status
python3 scripts/trino_status_check.py

# Start interactive locations map
streamlit run locations_map_app.py --server.port 8502
```

## 📁 File Structure

```
trino/
├── docker-compose.yml          # Docker services configuration
├── setup.sh                   # Automated setup script
├── start_dashboards.sh         # Interactive dashboard launcher
├── dashboard_client.py         # Python client with caching
├── streamlit_dashboard.py      # Main dashboard with analytics
├── locations_map_app.py        # Interactive map of gage locations
├── config/
│   ├── config.properties       # Trino coordinator config
│   ├── jvm.config             # JVM settings
│   ├── node.properties        # Node identification
│   ├── queue.properties       # Query queue management
│   ├── event-listener.properties  # Query monitoring
│   └── catalog/
│       └── iceberg.properties # Iceberg catalog connection
├── scripts/
│   ├── README.md              # Script documentation
│   ├── trino_status_check.py  # Trino integration diagnostic tool
│   ├── sql_template.py        # Comprehensive SQL query templates
│   └── quick_sql.py           # Simple SQL testing script
├── data/                      # Trino data directory
└── logs/                      # Application logs
```

## 🔧 Configuration

### Trino Performance Tuning

The configuration is optimized for dashboard workloads:

- **Memory**: 8GB JVM heap, 4GB query memory
- **Concurrency**: Up to 50 concurrent queries
- **Caching**: Iceberg metadata caching enabled
- **Queue Management**: Separate queues for different workload types

### Iceberg Catalog Connection

Connects to your existing AWS infrastructure:
- **REST Catalog**: `http://dev-teehr-sys-iceberg-alb-2105268770.us-east-2.elb.amazonaws.com`
- **S3 Warehouse**: `s3://dev-teehr-sys-iceberg-warehouse/warehouse/`
- **Credentials**: From AWS environment variables

### Query Optimization

- **Partition Filtering**: Automatic partition pruning
- **Projection Pushdown**: Column selection optimization  
- **Statistics**: Query cost optimization
- **Metadata Caching**: 10-minute cache for table metadata

## 📊 Dashboard Application

### Interactive Locations Map (`locations_map_app.py`)

The TEEHR locations dashboard provides:

- **Interactive Map**: 13,654+ USGS gage locations on Folium map
- **Trino Backend**: Production-ready query engine with native S3 support
- **Geometry Processing**: WKB geometry parsing for precise locations
- **Real-time Status**: Connection diagnostics and data statistics
- **Click Details**: View location information by clicking markers
- **Data Table**: Expandable raw data view with coordinates

## 🔍 Example Queries

### Basic Data Exploration

```sql
-- Show available tables
SHOW TABLES IN iceberg.teehr;

-- Location summary
SELECT 
    location_id,
    COUNT(*) as records,
    MIN(value_time) as start_date,
    MAX(value_time) as end_date
FROM iceberg.teehr.primary_timeseries 
GROUP BY location_id 
ORDER BY records DESC;
```

### Advanced Analytics

```sql
-- Monthly flow statistics with percentiles
SELECT 
    location_id,
    YEAR(value_time) as year,
    MONTH(value_time) as month,
    COUNT(*) as observations,
    AVG(value) as mean_flow,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY value) as median_flow,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY value) as q95_flow
FROM iceberg.teehr.primary_timeseries
WHERE location_id = 'USGS-01646500'
GROUP BY location_id, YEAR(value_time), MONTH(value_time)
ORDER BY year, month;
```

### Time Series Analytics

```sql
-- Moving averages and trend analysis
SELECT 
    location_id,
    value_time,
    value,
    AVG(value) OVER (
        ORDER BY value_time 
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) as moving_7day_avg,
    LAG(value, 1) OVER (ORDER BY value_time) as previous_value
FROM iceberg.teehr.primary_timeseries
WHERE location_id = 'USGS-01646500'
    AND value_time >= CURRENT_DATE - INTERVAL '90' DAY
ORDER BY value_time;
```

## 🔗 Integration Options

### 1. Grafana Integration

```bash
# Install Trino data source plugin
grafana-cli plugins install grafana-trino-datasource

# Connection settings:
Host: localhost:8080
Catalog: iceberg
Schema: teehr
User: teehr
```

### 2. Apache Superset

```python
# Add Trino database connection
SQLALCHEMY_URI = "trino://teehr@localhost:8080/iceberg/teehr"
```

### 3. Jupyter Notebooks

```python
import pandas as pd
from sqlalchemy import create_engine

engine = create_engine("trino://teehr@localhost:8080/iceberg/teehr")
df = pd.read_sql("SELECT * FROM primary_timeseries LIMIT 1000", engine)
```

### 4. BI Tools

Most BI tools support Trino via JDBC:
```
jdbc:trino://localhost:8080/iceberg/teehr
```

## 🔧 Management

### Start/Stop Services

```bash
# Start all services
docker-compose up -d

# Stop services
docker-compose stop

# Restart Trino
docker-compose restart trino

# View logs
docker-compose logs trino
```

### Monitoring

```bash
# Check Trino status
curl http://localhost:8080/v1/status

# View query history
docker exec -it teehr-trino trino-cli --execute "SELECT * FROM system.runtime.queries"

# Check resource usage
docker stats teehr-trino
```

### Scaling

For production scale-out:

1. **Add Worker Nodes**: Create additional Trino worker containers
2. **Load Balancing**: Use nginx/haproxy for query distribution
3. **Resource Limits**: Adjust memory/CPU limits in docker-compose.yml
4. **Persistent Storage**: Use named volumes for data persistence

## 🔒 Security

### Production Security Checklist

- [ ] Enable HTTPS with SSL certificates
- [ ] Configure user authentication (LDAP/OAuth)
- [ ] Set up query access controls
- [ ] Enable query auditing
- [ ] Secure AWS credentials (IAM roles preferred)
- [ ] Network isolation (VPC/security groups)

### Authentication Setup

Uncomment in `config/config.properties`:
```properties
http-server.authentication.type=PASSWORD
http-server.authentication.password.user-mapping.file=/etc/trino/password.db
```

## 📈 Performance Tuning

### Query Performance

1. **Partition Pruning**: Always filter on partition columns (location_id, date)
2. **Column Selection**: Use specific columns instead of SELECT *
3. **Limit Results**: Add LIMIT clauses for exploratory queries
4. **Join Optimization**: Put smaller tables on the right side of joins

### Memory Tuning

Adjust in `config/config.properties`:
```properties
query.max-memory=16GB                    # Increase for complex queries
query.max-memory-per-node=4GB           # Per-worker memory limit
query.max-total-memory-per-node=8GB     # Total worker memory
```

### JVM Tuning

Adjust in `config/jvm.config`:
```
-Xmx16G                                  # Increase heap size
-XX:G1HeapRegionSize=64M                # Adjust for larger heaps
```

## 🆘 Troubleshooting

### Common Issues

1. **Connection Refused**
   ```bash
   # Check if Trino is running
   docker ps | grep trino
   curl http://localhost:8080/v1/status
   ```

2. **Iceberg Catalog Connection Issues**
   ```bash
   # Run comprehensive diagnostic
   python3 scripts/trino_status_check.py
   
   # Test REST catalog directly
   curl -s http://dev-teehr-sys-iceberg-alb-2105268770.us-east-2.elb.amazonaws.com/v1/config
   ```

3. **S3 Access Issues (Critical for Trino 477)**
   
   **Problem**: "Error processing metadata for table" or "Failed to list views"
   
   **Solution**: Ensure `config/catalog/iceberg.properties` uses native S3 configuration:
   ```properties
   # REQUIRED for Trino 477
   fs.native-s3.enabled=true
   s3.aws-access-key=${ENV:AWS_ACCESS_KEY_ID}
   s3.aws-secret-key=${ENV:AWS_SECRET_ACCESS_KEY}
   s3.region=us-east-2
   
   # NOT: fs.s3a.* or hive.s3.* properties
   ```

4. **Out of Memory**
   ```bash
   # Check memory usage
   docker stats teehr-trino
   
   # Increase memory limits in docker-compose.yml
   mem_limit: 16g
   ```

5. **AWS Credentials**
   ```bash
   # Verify AWS credentials
   aws sts get-caller-identity
   export AWS_PROFILE=your-profile  # If using profiles
   
   # Check IAM permissions for S3 and Iceberg
   ```

6. **Query Failures**
   ```bash
   # Check query logs
   docker-compose logs trino | grep ERROR
   
   # View failed queries
   curl http://localhost:8080/v1/query
   ```

### Performance Issues

1. **Slow Queries**: Check partition filters and query plans
2. **High Memory Usage**: Tune JVM settings and query limits
3. **Connection Timeouts**: Adjust network and timeout settings

## 📚 Resources

- [Trino Documentation](https://trino.io/docs/)
- [Iceberg Trino Integration](https://iceberg.apache.org/trino/)
- [TEEHR Documentation](https://teehr.readthedocs.io/)
- [Performance Tuning Guide](https://trino.io/docs/current/admin/tuning.html)

## 🎯 Next Steps

1. **Start the Stack**: Run `./setup.sh`
2. **Explore Data**: Use the Streamlit dashboard
3. **Build Dashboards**: Integrate with your preferred BI tool
4. **Scale Up**: Add workers and tune performance
5. **Production Deploy**: Enable security and monitoring

Your TEEHR Trino production environment is ready! 🚀