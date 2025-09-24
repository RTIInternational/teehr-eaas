# TEEHR Evaluation System - Virtual Environment Setup

## Overview

This project uses a dedicated Python virtual environment to manage dependencies for the TEEHR (Tools for Exploratory Evaluation in Hydrologic Research) evaluation system. The virtual environment ensures consistent package versions and isolates project dependencies.

## 🚀 Quick Start

### 1. Activate the Virtual Environment

```bash
# From project root directory
cd /path/to/teehr-eval-sys
source .venv/bin/activate
```

Or use the helper script:
```bash
./activate_env.sh
```

### 2. Use with VS Code Jupyter Notebooks

1. Open `notebooks/teehr_iceberg_connection.ipynb`
2. Select the **"TEEHR Evaluation System"** kernel from the kernel picker
3. Run the cells to test the connection to your Iceberg catalog

## 📦 Installed Packages

The virtual environment includes all necessary packages for TEEHR evaluation:

### Core Dependencies
- **PySpark 4.0.0**: Distributed computing engine with Iceberg support
- **PyIceberg 0.10.0**: Python client for Apache Iceberg tables
- **findspark 2.0.1**: Spark environment initialization

### AWS Integration
- **boto3**: AWS SDK for Python
- **awswrangler**: Pandas on AWS
- **s3fs**: S3 filesystem interface

### Data Science Stack
- **pandas 2.2.3**: Data manipulation and analysis
- **numpy 1.26.4**: Numerical computing
- **matplotlib 3.10.6**: Plotting library
- **plotly 6.3.0**: Interactive visualizations
- **seaborn 0.13.2**: Statistical data visualization

### Jupyter Support
- **ipykernel**: Jupyter kernel support
- **jupyter**: Complete Jupyter environment
- **jupyterlab**: JupyterLab interface

### Additional Utilities
- **requests**: HTTP library
- **python-dotenv**: Environment variable management

## 🔧 Virtual Environment Details

- **Python Version**: 3.10.15 (compatible with all packages)
- **Location**: `.venv/` in project root
- **Kernel Name**: `teehr-eval`
- **Display Name**: "TEEHR Evaluation System"

## 💡 Usage Tips

### For Notebook Development
1. Always select the "TEEHR Evaluation System" kernel in VS Code
2. The first cell will verify that all packages are properly loaded
3. Environment variables can be loaded from `.env` files using `python-dotenv`

### For Script Development
```bash
# Activate environment first
source .venv/bin/activate

# Run your script
python your_script.py

# Deactivate when done
deactivate
```

### For Package Management
```bash
# Activate environment
source .venv/bin/activate

# Install additional packages
pip install new-package

# Update requirements (if needed)
pip freeze > requirements.txt
```

## 🧪 Testing the Environment

```bash
# Test core imports
python -c "import pyspark, pyiceberg, pandas; print('✅ All core packages ready!')"

# Test PySpark version
python -c "import pyspark; print(f'PySpark: {pyspark.__version__}')"

# Test Iceberg client
python -c "import pyiceberg; print(f'PyIceberg: {pyiceberg.__version__}')"
```

## 🔍 Troubleshooting

### Virtual Environment Not Found
```bash
# Recreate the virtual environment
~/.pyenv/versions/3.10.15/bin/python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m ipykernel install --user --name=teehr-eval --display-name="TEEHR Evaluation System"
```

### Kernel Not Available in VS Code
```bash
# Reinstall the kernel
source .venv/bin/activate
python -m ipykernel install --user --name=teehr-eval --display-name="TEEHR Evaluation System"
```

### Package Import Errors
1. Verify you're using the correct kernel in VS Code
2. Check that the virtual environment is activated
3. Verify package installation: `pip list | grep package-name`

### AWS Credentials
Make sure your AWS profile is configured:
```bash
# Set your AWS profile
export AWS_PROFILE=your-profile-name

# Or configure default credentials
aws configure
```

## 🏗️ Infrastructure Connection

The notebook connects to your TEEHR infrastructure:

- **Iceberg Catalog**: REST API endpoint from your Terraform deployment
- **S3 Warehouse**: Data lake storage for Iceberg tables
- **Database**: PostgreSQL metadata backend

Ensure your infrastructure is deployed and healthy before running the notebook.

## 📚 Next Steps

1. **Test Connection**: Run the notebook to verify connectivity to your Iceberg catalog
2. **Explore Data**: Use the provided examples to query existing tables
3. **Create Evaluations**: Implement TEEHR evaluation workflows using PySpark
4. **Visualize Results**: Create interactive dashboards with the included plotting libraries

## 🆘 Support

If you encounter issues:

1. Check that your infrastructure is running (`terraform output`)
2. Verify AWS credentials are configured
3. Ensure the virtual environment is activated
4. Check VS Code is using the correct Jupyter kernel
5. Review the notebook cells for any error messages

---

*This virtual environment provides a complete TEEHR evaluation stack optimized for hydrologic research with cloud-based Apache Iceberg data warehouse integration.*