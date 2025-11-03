#!/bin/bash
"""
TEEHR Panel Dashboard Setup and Launch
======================================
Installs Panel and launches the TEEHR dashboard
"""

echo "🚀 TEEHR Panel Dashboard Setup"
echo "================================"

# Activate virtual environment if available
if [ -f "../.venv/bin/activate" ]; then
    echo "📦 Activating virtual environment..."
    source ../.venv/bin/activate
fi

# Install Panel and dependencies
echo "🔧 Installing Panel dashboard requirements..."
pip install panel>=1.3.0 folium>=0.14.0 plotly>=5.0.0

echo ""
echo "🌐 Starting TEEHR Panel Dashboard..."
echo "   URL: http://localhost:5007"
echo "   Press Ctrl+C to stop"
echo "================================"

# Run the dashboard
panel serve teehr_panel_dashboard.py --show --port 5007 --allow-websocket-origin localhost:5007