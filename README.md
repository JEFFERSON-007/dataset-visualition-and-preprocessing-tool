# 📊 DataLyze Pro

**High-Performance Exploratory Data Analysis & Automated Preprocessing Tool**

DataLyze Pro is a premium, lightweight, and robust data visualization suite designed for data scientists and analysts who need speed without complexity. Built with a hybrid **DuckDB + FastAPI** backend, it handles massive joins and high-cardinality datasets where traditional tools fail.

<img width="1919" height="934" alt="Image" src="https://github.com/user-attachments/assets/09dc06a9-c683-469d-8ff0-2897287b5b56" />

<img width="464" height="888" alt="Image" src="https://github.com/user-attachments/assets/6fce1540-c79f-46b7-a949-415d6be1b507" />

<img width="466" height="169" alt="Image" src="https://github.com/user-attachments/assets/4315d6a3-0a9e-4205-ab29-eb1075823a20" />

## 🚀 Key Features

### 1. High-Performance Hybrid Engine
*   **DuckDB Integration**: SQL-based join engine that prevents `MemoryError` during massive dataset merges.
*   **Memory Guard**: Intelligent predictive logic that blocks "Cartesian Explosions" before they crash your system.
*   **Streaming Downloads**: Efficiently handle 1M+ row CSV exports with zero memory spikes.

### 2. Premium Analytics & EDA
*   **Glassmorphism UI**: A stunning, modern dark-mode interface with responsive Plotly visualizations.
*   **Instant Health Checks**: Automatic detection of duplicate rows, missing values, constant columns, and outliers.
*   **Dynamic Visualizations**: Automatically recommends the best charts (Scatter, Box, Histogram, Bar) based on your data types.

### 3. Advanced Merge Studio
*   **Bulk Merge**: Join multiple files sequentially in one operation.
*   **Multi-Key Support**: Complex relational joins using comma-separated key lists (e.g., `Year, ID, Region`).
*   **Auto-Deduplication**: Automatically handles column name collisions with predictable suffixing.

### 4. Machine Learning Pipeline
*   **Auto-Prep Suite**: One-click pipeline to handle missing values and categorical encoding.
*   **ML-Ready Export**: Descend from raw data to a clean, training-ready CSV in seconds.

## 🛠️ Installation & Usage

### For Users (Windows)
1.  Download the latest release from the `dist/` folder.
2.  Run `DataLyze.exe`.
3.  The application will automatically launch in your browser at `http://localhost:8085`.

### For Developers
1.  Clone the repository.
2.  Install dependencies: `pip install -r requirements.txt`.
3.  Run the app: `python app.py`.

## 📂 Project Structure
*   `app.py`: FastAPI backend and session management.
*   `duckdb_backend.py`: High-performance data processing layer.
*   `build_exe.py`: Optimized PyInstaller build script (compact 56MB binary).
*   `static/`: Premium frontend assets (JS/CSS/HTML).
*   `USER_MANUAL.md`: Step-by-step feature guide.
*   `PROJECT_REPORT.md`: Detailed architectural analysis.

---
*Built with ❤️ for High-Performance Data Engineering.*
