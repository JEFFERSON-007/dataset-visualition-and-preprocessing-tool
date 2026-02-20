# DataLyze - Professional Project Analysis

## Executive Summary
DataLyze is a high-performance, premium data visualization and preprocessing platform. It bridges the gap between raw data and actionable insights by providing automated profiling, intelligent visualization recommendations, and "one-click" machine learning preparation.

## Technical Architecture

### Backend (Python/FastAPI)
- **High-Concurrency Engine**: Utilizes `ThreadPoolExecutor` for parallelizing data profiling across CPU cores.
- **Adaptive Backend**: Automatically switches between **Pandas** (for standard files) and **DuckDB** (for large-scale data processing >500MB).
- **Session Management**: Implements an in-memory session store for temporary data handling, optimized for low memory footprint.
- **Reporting Layer**: Uses `WeasyPrint` (if available) for professional PDF generation or falls back to optimized HTML reports.

### Frontend (Vanilla JS/CSS)
- **Glassmorphism UI**: A state-of-the-art design system built with custom CSS variables, supporting dynamic dark/light themes.
- **Reactive Dashboard**: Real-time rendering of Plotly.js visualizations based on backend heuristics.
- **Micro-Animations**: Smooth fade-ins and interactive hover effects for a premium user experience.

## Key Features

### 1. Intelligent Data Health Scan
- **Automatic Detection**: Scans for duplicate rows, missing values, and constant columns.
- **Actionable Insights**: Provides specific warnings in the "Data Health" tab with descriptions of the issues.

### 2. Auto-Prep for ML
- **Feature Engineering**: Automated handling of numeric missing values (median imputation) and categorical missing values (labeling).
- **Encoding**: Implements one-hot encoding for categorical variables with manageable cardinality.
- **Scalability**: Designed to handle datasets up to 25GB using DuckDB-powered sampling.

### 3. Merge Studio
- **Dynamic Joining**: Allows users to upload a secondary dataset and perform SQL-like joins (Inner, Left, Right, Full) directly in the browser.
- **Key Discovery**: Automatically populates primary key options from the current dataset.

## Performance Metrics
- **Upload Speed**: Processes 100k+ rows in under 2 seconds (on standard hardware).
- **Memory Efficiency**: Implements lazy loading for previews to keep browser memory usage low.

## Future Roadmap
- **Advanced ML Models**: Integration of Scikit-learn directly for baseline model training.
- **Export Formats**: Support for SQL export and Parquet optimization.
- **Cloud Integration**: AWS/Azure storage hooks for enterprise data.
