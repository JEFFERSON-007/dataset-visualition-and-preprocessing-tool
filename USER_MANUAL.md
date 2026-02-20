# DataLyze - User Manual (Professional Edition)

Welcome to **DataLyze**, your all-in-one solution for dataset visualization, cleaning, and ML preparation. This guide will walk you through the core features of the platform.

## 🚀 Getting Started

### 1. Launching the App
- **Windows**: Double-click `DataLyze.exe` in the `dist/` folder.
- **Developer Mode**: Run `python app.py` and navigate to `http://localhost:8081`.

### 2. Loading Data
- Click the center drop zone or drag your file (**CSV, Excel, JSON, Parquet, or TXT**) directly onto the dashboard.
- Once selected, click the **🚀 Analyze Dataset** button.

## 📊 Dashboard Features

### Quick Profile
The "Quick Profile" panel on the right provides an instant snapshot of your data:
- **Type Detection**: Tells you if a column is Numeric, Categorical, Datetime, or Text.
- **Missing Values**: Highlights potential data gaps in **Red**.
- **Unique Count**: Shows the cardinality of each column.

### Data Health Tab
Located on the left, this tab proactively scans for issues:
- **Duplicates**: Tells you exactly how many identical rows exist.
- **Constant Columns**: Alerts you to columns that provide no information (e.g., all rows have the same value).
- **Suggestions**: Provides actionable advice on how to improve your data quality.

## 🛠️ Advanced Tools (Toolbar)

### 🧹 Clean Data
Click the "Clean Data" button to open the cleaning studio:
- **Remove Duplicates**: Instantly purges identical rows.
- **Impute Missing**: Fills empty cells using the **Median** for numbers or **Mode** for categories.
- **Drop Constant**: Removes useless columns automatically.

### 🔗 Merge Studio
Need to combine datasets?
1. Open the **Merge Studio**.
2. Select a **Primary Key** from your current data.
3. Upload a **Secondary File**.
4. Enter the **Secondary Key** and choose your **Merge Type** (Inner, Left, Right, or Full).

### 🤖 Auto-Prep for ML
Preparing for Machine Learning? This feature:
- Performs intelligent imputation.
- Handles One-Hot Encoding for low-cardinality categories.
- Downloads a **clean, numeric-ready CSV** perfect for Scikit-learn or TensorFlow.

### 📄 Download Report
Generates a professional summary of your dataset.
- Includes statistical summaries.
- Lists data structures and identified quality issues.
- Downloads as a **PDF** (if dependencies are present) or an optimized **HTML** file.

## 🎨 Personalization
- Use the **☀️/🌙** toggle in the top right to switch between high-contrast dark mode and clean light mode.

---
**Support**: For technical issues, please refer to the `README.md` or contact the development team.
