#!/bin/bash

# TEEHR Evaluation System - Virtual Environment Activation Script

echo "🚀 TEEHR Evaluation System - Virtual Environment Setup"
echo "=================================================="

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run the setup first from the project root directory:"
    echo "   cd /path/to/teehr-eval-sys"
    echo "   ~/.pyenv/versions/3.10.15/bin/python -m venv .venv"
    echo "   source .venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source .venv/bin/activate

# Verify installation
echo "✅ Environment activated!"
echo ""
echo "📦 Installed packages:"
echo "   - PySpark: $(python -c 'import pyspark; print(pyspark.__version__)' 2>/dev/null || echo 'Not installed')"
echo "   - PyIceberg: $(python -c 'import pyiceberg; print(pyiceberg.__version__)' 2>/dev/null || echo 'Not installed')"
echo "   - Pandas: $(python -c 'import pandas; print(pandas.__version__)' 2>/dev/null || echo 'Not installed')"
echo ""
echo "🎯 To use in VS Code:"
echo "   1. Open the notebook: notebooks/teehr_iceberg_connection.ipynb"
echo "   2. Select kernel: 'TEEHR Evaluation System'"
echo "   3. Run the cells to test the connection"
echo ""
echo "🧪 To test the environment:"
echo "   python -c 'import pyspark; print(f\"PySpark {pyspark.__version__} ready!\")'"
echo ""
echo "💡 To deactivate: deactivate"