# DataLyze Pro: User Manual

## 1. Getting Started
DataLyze Pro is a zero-installation tool. Simply double-click `DataLyze.exe` in the `dist/` folder to begin. The application will automatically open in your default web browser (usually at `http://localhost:8085`).

## 2. Core Workspace
### 2.1. Uploading Data
1.  **Drag & Drop**: Drag any `.csv`, `.xlsx`, or `.parquet` file onto the upload zone.
2.  **Analyze**: Click "Upload & Process". DataLyze will generate a Dashboard with statistics and visualizations.

### 2.2. Data Health
The **Data Health** tab highlights issues like:
*   Duplicate rows.
*   Columns with missing values (shown in red).
*   Constant columns (columns with no variance).

## 3. Merge Studio (Advanced)
The Merge Studio allows you to combine your current dataset with other files.

### 3.1. Performing a Bulk Merge
1.  **Select Multiple Files**: Click "Browse" and select one or more files to merge.
2.  **Define Keys**: 
    *   **Primary Key(s)**: Enter the column name(s) from your current data.
    *   **Secondary Key(s)**: Enter the column name(s) from the new files.
    *   *Note: For multiple columns, separate them with commas (e.g., `Year, ID`).*
3.  **Choose Type**: Select Inner, Left, Right, or Full Outer Join.
4.  **Run**: Click "Run Bulk Merge". The resulting dataset will automatically download.

## 4. Data Cleaning
1.  Open the **Data Cleaning** section.
2.  Check your desired options:
    *   **Remove Duplicates**: Deletes identical rows.
    *   **Impute Missing Values**: Fills empty cells with the Median or Mode.
    *   **Drop Constant Columns**: Removes columns that provide no information.
3.  Click **Clean & Download** to get your refined dataset.

## 5. Machine Learning Readiness
Click the **Auto-Prep for ML** button. This will:
1.  Handle all missing values.
2.  Perform One-Hot Encoding on categorical columns with low cardinality.
3.  Return a clean CSV ready for training models.

## 6. Troubleshooting
*   **App won't start?** Ensure no other process is using port 8085. The app will try up to port 8095 automatically.
*   **Merge Failed?** Ensure your join keys exist in both datasets and that the number of keys matches exactly.
*   **Browser showing old version?** Press `Ctrl + F5` to perform a hard refresh and clear the cache.

---
*DataLyze Pro - Making Data Work For You.*
