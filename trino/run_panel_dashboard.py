#!/usr/bin/env python3
"""
TEEHR Panel Dashboard Launcher
==============================
Simple launcher script for the TEEHR Panel dashboard.
"""

import subprocess
import sys
import os

def install_requirements():
    """Install required packages if not already installed."""
    requirements = [
        'panel>=1.3.0',
        'folium>=0.14.0',
        'plotly>=5.0.0',
        'geopandas>=0.14.0',
        'trino>=0.328.0',
        'pandas>=2.0.0',
        'shapely>=2.0.0'
    ]
    
    print("🔧 Installing Panel dashboard requirements...")
    for req in requirements:
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', req])
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Failed to install {req}: {e}")
    
    print("✅ Requirements installation complete!")

def main():
    """Main launcher function."""
    print("🚀 TEEHR Panel Dashboard Launcher")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists('locations_dashboard_panel.py'):
        print("❌ Please run this script from the trino/ directory")
        sys.exit(1)
    
    # Install requirements
    install_requirements()
    
    print("\n🌐 Starting TEEHR Panel Dashboard...")
    print("   URL: http://localhost:5007")
    print("   Press Ctrl+C to stop the dashboard")
    print("-" * 50)
    
    try:
        # Run the Panel dashboard
        subprocess.run([
            sys.executable, '-m', 'panel', 'serve', 
            'locations_dashboard_panel.py',
            '--show',
            '--port', '5007',
            '--allow-websocket-origin', 'localhost:5007'
        ])
    except KeyboardInterrupt:
        print("\n🛑 Dashboard stopped by user")
    except Exception as e:
        print(f"❌ Dashboard failed to start: {e}")

if __name__ == "__main__":
    main()