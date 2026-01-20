# Project Report: Enhanced Dataset Visualizer

**Date**: 2026-01-20  
**Project**: Weather Dataset Visualisation Enhancement  

## 1. Executive Summary
The goal of this project was to transform a basic weather dataset viewer into a premium, generic data exploration platform. The final application successfully integrates advanced visualization, data quality analysis, and automated preprocessing into a seamless, high-aesthetic web interface. It is designed to be "plug-and-play" on any system.

## 2. Key Capabilities

### 2.1 Universal Data Handling
- **Formats**: The system now supports CSV, TSV, Excel (.xlsx), JSON (nested & ndjson), and Parquet.
- **Resilience**: It employs robust parsing logic to handle various encodings (UTF-8, Latin1) and structure variations.

### 2.2 Intelligent Visualization Engine
- **Logic**: The app detects column types (Numeric, Categorical, DateTime, Geo-Spatial) to recommend the most impactful charts.
- **Aesthetics**: 
    - A **vibrant 10-color palette** was implemented to ensure distinct and accessible visuals.
    - Chart styles include smooth spline interpolation for line charts and dynamic color scaling for heatmaps/scatter plots.

### 2.3 Data Health & Quality
A new "Data Health" module was developed to provide instant feedback:
- **Duplicate Detection**: Identifies exact row duplicates immediately.
- **Missing Value Analysis**: Flags columns with critical (>40%) or warning (>10%) levels of missing data.
- **Anomaly Detection**: Flags constant columns (zero variance).

### 2.4 Automated Preprocessing Pipeline
Users can now clean their data without writing code. The pipeline supports:
1.  **Deduplication**: Removing exact duplicates.
2.  **Imputation**: Filling missing numeric values (Median) and categorical values (Mode).
3.  **Feature Selection**: Dropping non-informative constant columns.
4.  **Export**: Generating a downloadable CSV of the processed data.

## 3. Technical Architecture

### 3.1 Backend (FastAPI)
- **Framework**: FastAPI for high-performance async handling.
- **Data Processing**: Pandas and NumPy for efficient in-memory manipulation.
- **Stateless Design**: The system is designed to be lightweight. Cleaned datasets are temporarily stored in memory (UUID-keyed) for immediate download.

### 3.2 Frontend (Vanilla JS + Plotly)
- **Design System**: A custom "Glassmorphism" design system using CSS variables for consistent theming.
- **Interactivity**: Drag-and-drop file handling, real-time status updates, and dynamic DOM injection for reports.
- **Zero-Build**: No complex node_modules; the frontend runs directly from standard HTML/CSS/JS.

## 4. Portability
To ensure "work on any system" compatibility:
- **Auto-Runner (`run_with_auto_requirements.py`)**: A self-contained script that detects imports, installs missing dependencies via pip, and launches the server.
- **Standard Dependencies**: usage of widely supported libraries (`pandas`, `plotly`, `fastapi`).

## 5. Conclusion
The application has been upgraded from a simple viewer to a comprehensive EDA (Exploratory Data Analysis) tool. It provides immediate value by identifying data issues and offering one-click solutions, wrapped in a professional, modern user interface.
