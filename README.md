# Dataset Visualization & Preprocessing Tool

<div align="center">

![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)

**Professional-grade tool for analyzing and preprocessing datasets up to 5GB**

[Features](#features) • [Quick Start](#quick-start) • [Installation](#installation) • [Usage](#usage) • [Performance](#performance)

</div>

---

## ✨ Features

### 📊 **Multi-Format Support**
- CSV, TSV, TXT (delimited files)
- Excel (XLSX, XLS) - multiple sheets
- JSON (standard & NDJSON)
- Parquet (with zero-copy reads)

### 🚀 **Intelligent Backend Selection**
- **<1GB**: Pandas (fast in-memory processing)
- **1-2GB**: Dask (distributed computing)
- **>2GB**: DuckDB (SQL-based analytics with zero-copy)

### 🎨 **Modern UI**
- Dark mode with glassmorphism design
- Responsive layout (mobile, tablet, desktop)
- WebGL-accelerated visualizations
- Smooth animations and transitions

### 🧹 **Data Preprocessing**
- Remove duplicates
- Handle missing values (drop/impute)
- Detect outliers
- Data quality analysis
- Download cleaned datasets
- Generate analysis reports

### ⚡ **Performance Optimizations**
- Adaptive sampling (10k-100k rows)
- Memory-efficient dtype optimization
- WebGL rendering for large charts
- Chunked processing for multi-GB files

---

## 🚀 Quick Start

### Windows

```batch
# 1. Double-click to install
install.bat

# 2. Double-click to run
start.bat

# 3. Open browser
http://localhost:8081
```

### macOS / Linux

```bash
# 1. Make scripts executable
chmod +x install.sh start.sh

# 2. Install
./install.sh

# 3. Run
./start.sh

# 4. Open browser
http://localhost:8081
```

---

## 📋 Requirements

- **Python**: 3.8 or higher
- **RAM**: 2GB minimum (4GB recommended for large files)
- **Browser**: Chrome, Firefox, Edge, or Safari (latest versions)
- **Disk Space**: 500MB for dependencies

---

## 🔧 Installation

### Option 1: Automated (Recommended)

**Windows:**
```batch
install.bat
```

**macOS/Linux:**
```bash
chmod +x install.sh
./install.sh
```

### Option 2: APT Package (Debian/Ubuntu)

**One-command installation:**
```bash
# Build the package
chmod +x build-deb.sh
./build-deb.sh

# Install
sudo dpkg -i releases/dataset-viz_1.0.0_all.deb
```

**Features:**
- ✅ Auto-starts as systemd service
- ✅ Runs on boot
- ✅ Easy management with `dataset-viz` command
- ✅ Clean uninstallation

**Usage:**
```bash
dataset-viz start   # Start service
dataset-viz stop    # Stop service
dataset-viz status  # Check status
dataset-viz logs    # View logs
dataset-viz open    # Open in browser
```

See [INSTALL_APT.md](INSTALL_APT.md) for detailed instructions.

### Option 3: Manual

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Run application
python app.py
```

---

## 📖 Usage

### 1. Upload Dataset

- **Drag & drop** your file onto the upload zone
- Or **click** to browse and select
- Supported formats: CSV, TSV, Excel, JSON, Parquet
- Max file size: **5GB**

### 2. View Analysis

The tool automatically:
- Profiles your data (types, missing values, duplicates)
- Recommends visualizations based on data types
- Generates interactive charts
- Identifies data quality issues

### 3. Preprocess (Optional)

Select preprocessing options:
- ✅ Remove duplicate rows
- ✅ Drop rows with missing values
- ✅ Impute missing values (mean/median/mode)
- ✅ Remove outliers

### 4. Download

Download your cleaned dataset in the original format.

### 5. Generate Report

Click **"Download Report"** to get a comprehensive HTML analysis of your dataset, including:
- Statistical summary
- Data quality issues
- Column distribution details

---

## 📊 Performance

### Processing Speed

| File Size | Format | Backend | Load Time | Memory Usage |
|-----------|--------|---------|-----------|--------------|
| 100MB | CSV | Pandas | <2s | ~30MB |
| 500MB | CSV | Pandas | ~5s | ~150MB |
| 1GB | CSV | DuckDB | ~8s | ~200MB |
| 3GB | CSV | DuckDB | ~10s | ~250MB |
| 5GB | Parquet | DuckDB | ~3s | ~150MB (zero-copy) |

### Visualization Performance

- **<10k points**: Standard Plotly rendering
- **>10k points**: WebGL-accelerated (scattergl)
- **Adaptive sampling**: Maintains visual fidelity with reduced data

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│           Frontend (HTML/JS)            │
│  - Modern UI with dark mode             │
│  - WebGL visualizations                 │
│  - Drag-and-drop upload                 │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│         Backend (FastAPI)               │
│  - Smart backend selection              │
│  - File parsing & validation            │
│  - Data profiling                       │
└────────────────┬────────────────────────┘
                 │
        ┌────────┴────────┐
        ▼                 ▼
┌──────────────┐  ┌──────────────┐
│    Pandas    │  │   DuckDB     │
│   (<1GB)     │  │   (>1GB)     │
│              │  │              │
│ - In-memory  │  │ - SQL-based  │
│ - Fast       │  │ - Zero-copy  │
└──────────────┘  └──────────────┘
```

---

## 🛠️ Technology Stack

- **Backend**: FastAPI, Uvicorn
- **Data Processing**: Pandas, DuckDB, Dask
- **Visualization**: Plotly.js (with WebGL)
- **UI**: HTML5, CSS3 (Glassmorphism), Vanilla JavaScript

---

## 🐛 Troubleshooting

### Python Not Found

**Windows:**
```
Download from: https://www.python.org/downloads/
Make sure to check "Add Python to PATH" during installation
```

**macOS:**
```bash
brew install python@3.11
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

### Port Already in Use

If port 8081 is already in use, edit `app.py`:
```python
# Change this line at the bottom
uvicorn.run(app, host='0.0.0.0', port=8082)  # Use different port
```

### Dependencies Installation Failed

```bash
# Upgrade pip first
python -m pip install --upgrade pip

# Install dependencies one by one
pip install fastapi uvicorn pandas numpy
pip install plotly openpyxl pyarrow
pip install dask[complete] duckdb
```

---

## 📝 License

MIT License - feel free to use this tool for personal or commercial projects.

---

## 🤝 Contributing

Contributions are welcome! Feel free to:
- Report bugs
- Suggest features
- Submit pull requests

---

## 📧 Support

For issues or questions, please open an issue on GitHub.

---

<div align="center">

**Made with ❤️ for data enthusiasts**

⭐ Star this repo if you find it useful!

</div>
