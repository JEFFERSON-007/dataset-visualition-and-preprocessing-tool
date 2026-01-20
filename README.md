# Premium Dataset Explorer & Visualizer

A powerful, aesthetic, and fully automated dataset exploration tool.  
**Analyze, Visualize, Clean, and Download** your data in seconds.

![Dataset Explorer](https://via.placeholder.com/800x400?text=Premium+Dataset+Explorer)

## 🌟 Features

*   **Universal File Support**: Drag & drop CSV, TSV, Excel, JSON, Parquet, or Text files.
*   **Premium Visualization**: 
    *   Interactive Plotly charts with a **vibrant 10-color palette**.
    *   Automatic recommendation engine (Scatter, Line, Bar, Pie, Heatmaps, Geo Maps).
    *   Glassmorphism UI with smooth animations.
*   **Data Health Check**:
    *   Instant detection of **Duplicates**.
    *   **Quality Analysis**: Identifies missing values, constant columns, and anomalies.
*   **One-Click Preprocessing**:
    *   **Remove Duplicates**: Clean exact matches instantly.
    *   **Smart Imputation**: Fills missing numeric values with Median and categorical with Mode.
    *   **Optimization**: Drops useless constant columns.
*   **Export**: Download your cleaned and optimized dataset.

## 🚀 Quick Start (Any System)

This project comes with an **auto-runner** script that handles everything for you.

1.  **Run the Auto-Installer**:
    ```bash
    python run_with_auto_requirements.py
    ```
    *This script will automatically detect dependencies, install them, and start the verified server.*

2.  **Open Browser**:
    Go to `http://localhost:8081`

## 🛠 Manual Installation

If you prefer to install manually:

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Run Application**:
    ```bash
    python app.py
    ```

## 📊 How It Works

1.  **Upload**: Drop your file. The app detects types (Numeric, Categorical, Datetime, Geo).
2.  **Explore**: See the "Data Health" report and auto-generated "Visualizations".
3.  **Clean**: Toggle options in the "Preprocessing" card and click "Clean & Download".
4.  **Export**: Get your ready-to-use dataset.

## 🎨 Visualization Palette
We use a custom-tuned premium palette:
- `Indigo` #6366f1
- `Violet` #8b5cf6
- `Pink` #ec4899
- `Emerald` #10b981
- `Amber` #f59e0b
- ...and more!

---
*Created for the "Weather Dataset Visualisation" task.*
