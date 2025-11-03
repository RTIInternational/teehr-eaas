#!/bin/bash
# Panel Dashboard Fixed Version Launcher
# Ensures all dependencies are available and runs the dashboard

echo "🚀 Starting TEEHR Panel Dashboard (Fixed Version)"
echo "=================================================="

# Activate virtual environment if available
if [ -f "../.venv/bin/activate" ]; then
    echo "📦 Activating virtual environment..."
    source ../.venv/bin/activate
else
    echo "❌ Virtual environment not found at ../.venv/bin/activate"
    echo "Please create a virtual environment first:"
    echo "  cd /Users/mdenno/repos/teehr-eval-sys"
    echo "  python3 -m venv .venv"
    echo "  source .venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# Check Python environment
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.8+ to continue."
    exit 1
fi

echo "✅ Python found: $(python3 --version)"

# Install required packages from requirements file
echo "📦 Installing dashboard dependencies..."
pip install -r ../requirements.txt

echo ""
echo "🌐 Dashboard will be available at: http://localhost:5007"
echo "📊 Press Ctrl+C to stop the server"
echo ""

# Run the dashboard
python3 teehr_panel_fixed.py