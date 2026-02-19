"""
Enhanced single-file FastAPI EDA app

Features:
- Supports CSV, TSV, XLSX (multiple sheets), JSON (ndjson & nested), Parquet
- Automatic type detection: numeric, datetime, categorical, boolean, text, geo (lat/lon), nested JSON flattening
- Profiling and recommended visualizations per dataset
- Interactive Plotly frontend (embedded) with Premium Design
- Real-time chart rendering based on recommendations

Install requirements:
    pip install fastapi uvicorn pandas numpy python-multipart plotly openpyxl pyarrow
    # duckdb is optional for very large files: pip install duckdb

Run:
    python app.py

Open:
    http://localhost:8081
"""

from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, Response
from fastapi.staticfiles import StaticFiles
import uvicorn
import pandas as pd
import numpy as np
import io
import json
from typing import List, Dict, Any, Union
import tempfile
import os
import uuid
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import warnings
warnings.filterwarnings('ignore')

# Try to import Dask for large file support
try:
    import dask
    import dask.dataframe as dd
    from dask.diagnostics import ProgressBar
    DASK_AVAILABLE = True
except ImportError:
    DASK_AVAILABLE = False
    dd = None

# Try to import DuckDB for very large file support
try:
    import duckdb
    from duckdb_backend import DuckDBBackend
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False
    DuckDBBackend = None

try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

app = FastAPI(title="DataLyze — Premium EDA Tool")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configuration
MAX_FILE_SIZE = 25 * 1024 * 1024 * 1024  # 25GB in bytes
LARGE_FILE_THRESHOLD = 1 * 1024 * 1024 * 1024  # 1GB - use DuckDB/Dask
VERY_LARGE_THRESHOLD = 2 * 1024 * 1024 * 1024  # 2GB - force DuckDB
CHUNK_SIZE = 100000  # Rows per chunk for streaming
MAX_SAMPLE_ROWS = 50000  # Maximum rows to sample for visualization
SUPPORTED_EXTENSIONS = ['.csv', '.tsv', '.txt', '.xlsx', '.xls', '.json', '.parquet']

# Thread pool for parallel operations
executor = ThreadPoolExecutor(max_workers=4)

# Store for cleaned datasets (in-memory for simple demo, use Redis/DB for prod)
cleaned_datasets_store = {}

# ---------- Helpers ----------

def safe_read_csv(s: str, sep=',', nrows=None):
    try:
        return pd.read_csv(io.StringIO(s), nrows=nrows)
    except Exception:
        # try with python engine
        return pd.read_csv(io.StringIO(s), engine='python', sep=sep, nrows=nrows)


def optimize_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """Optimize DataFrame memory usage by downcasting dtypes"""
    for col in df.columns:
        col_type = df[col].dtype
        
        if col_type != object:
            c_min = df[col].min()
            c_max = df[col].max()
            
            if str(col_type)[:3] == 'int':
                if c_min > np.iinfo(np.int8).min and c_max < np.iinfo(np.int8).max:
                    df[col] = df[col].astype(np.int8)
                elif c_min > np.iinfo(np.int16).min and c_max < np.iinfo(np.int16).max:
                    df[col] = df[col].astype(np.int16)
                elif c_min > np.iinfo(np.int32).min and c_max < np.iinfo(np.int32).max:
                    df[col] = df[col].astype(np.int32)
            else:
                if c_min > np.finfo(np.float16).min and c_max < np.finfo(np.float16).max:
                    df[col] = df[col].astype(np.float32)
        else:
            # Convert low-cardinality strings to categorical
            num_unique = df[col].nunique()
            num_total = len(df[col])
            if num_unique / num_total < 0.5:
                df[col] = df[col].astype('category')
    
    return df


def smart_sample(df: pd.DataFrame, target_size: int = MAX_SAMPLE_ROWS) -> pd.DataFrame:
    """Smart sampling that maintains data distribution"""
    if len(df) <= target_size:
        return df
    
    # Use random sampling with fixed seed for reproducibility
    return df.sample(n=target_size, random_state=42)


def profile_csv_chunked(filepath: str, chunksize: int = CHUNK_SIZE) -> Dict[str, Any]:
    """Profile large CSV files in chunks without loading into memory"""
    stats = {}
    total_rows = 0
    chunk_count = 0
    
    for chunk in pd.read_csv(filepath, chunksize=chunksize):
        total_rows += len(chunk)
        chunk_count += 1
        
        for col in chunk.columns:
            if col not in stats:
                stats[col] = {
                    'count': 0,
                    'missing': 0,
                    'dtype': str(chunk[col].dtype),
                    'unique_values': set()
                }
            
            stats[col]['count'] += len(chunk[col])
            stats[col]['missing'] += chunk[col].isnull().sum()
            
            # Track unique values (limit to avoid memory issues)
            if len(stats[col]['unique_values']) < 1000:
                stats[col]['unique_values'].update(chunk[col].dropna().unique())
    
    # Convert sets to counts
    for col in stats:
        stats[col]['unique'] = len(stats[col]['unique_values'])
        del stats[col]['unique_values']
    
    return {'total_rows': total_rows, 'columns': stats}


def select_backend(file_size: int, file_ext: str) -> str:
    """
    Choose optimal backend based on file characteristics
    
    Returns: 'pandas', 'dask', or 'duckdb'
    """
    if file_size < LARGE_FILE_THRESHOLD:
        return 'pandas'  # Fast for <1GB
    
    elif file_size < VERY_LARGE_THRESHOLD:
        # 1-2GB: Use Dask if available, else DuckDB
        if DASK_AVAILABLE and file_ext in ['.csv', '.parquet']:
            return 'dask'
        elif DUCKDB_AVAILABLE and file_ext in ['.csv', '.parquet']:
            return 'duckdb'
        return 'pandas'  # Fallback
    
    else:
        # >2GB: DuckDB is most efficient
        if DUCKDB_AVAILABLE and file_ext in ['.csv', '.parquet']:
            return 'duckdb'
        elif DASK_AVAILABLE and file_ext in ['.csv', '.parquet']:
            return 'dask'
        return 'pandas'  # Fallback (will likely fail for very large files)


def adaptive_sample_size(total_rows: int, file_size_mb: float) -> int:
    """
    Determine optimal sample size based on dataset characteristics
    
    Larger datasets get smaller samples to maintain performance
    """
    if total_rows < 10000:
        return total_rows  # Use all data
    
    elif total_rows < 100000:
        return 10000  # 10k sample
    
    elif total_rows < 1000000:
        return 50000  # 50k sample
    
    elif file_size_mb < 1000:  # <1GB
        return 100000  # 100k sample
    
    else:  # >1GB
        return 50000  # Conservative for very large files


def parse_uploaded_file(contents: bytes, filename: str, sample_rows: int = 5000):
    """Return a dict of {name: DataFrame} — for single-sheet returns {'sheet1': df}
    Tries to handle csv, tsv, xlsx, json (ndjson or json array), parquet.
    Raises ValueError with descriptive messages for parsing failures.
    """
    name = filename.lower()
    tmp = None
    
    # Check if file is empty
    if len(contents) == 0:
        raise ValueError('File is empty. Please upload a file with data.')
    
    try:
        if name.endswith('.csv') or name.endswith('.txt'):
            s = None
            try:
                s = contents.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    s = contents.decode('latin1', errors='ignore')
                except Exception:
                    raise ValueError('Unable to decode file. Please ensure it is a valid text file with UTF-8 or Latin-1 encoding.')
            try:
                df = safe_read_csv(s, sep=',', nrows=sample_rows)
                if df.empty:
                    raise ValueError('CSV file contains no data rows.')
                return {os.path.splitext(filename)[0]: df}
            except Exception as e:
                raise ValueError(f'Failed to parse CSV file: {str(e)}. Please ensure it is a valid CSV format.')

        elif name.endswith('.tsv') or '\t' in contents.decode('utf-8', errors='ignore')[:200]:
            s = contents.decode('utf-8', errors='ignore')
            try:
                df = safe_read_csv(s, sep='\t', nrows=sample_rows)
                if df.empty:
                    raise ValueError('TSV file contains no data rows.')
                return {os.path.splitext(filename)[0]: df}
            except Exception as e:
                raise ValueError(f'Failed to parse TSV file: {str(e)}. Please ensure it is a valid tab-separated format.')

        elif name.endswith('.xlsx') or name.endswith('.xls'):
            # write to temp file and use pandas.read_excel with sheet_name=None
            try:
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1])
                tmp.write(contents); tmp.close()
                sheets = pd.read_excel(tmp.name, sheet_name=None)
                # limit rows per sheet for safety
                sheets = {k: v.head(sample_rows) for k,v in sheets.items()}
                if not sheets or all(df.empty for df in sheets.values()):
                    raise ValueError('Excel file contains no data.')
                return sheets
            except Exception as e:
                if 'openpyxl' in str(e) or 'xlrd' in str(e):
                    raise ValueError('Missing required library for Excel files. Please ensure openpyxl is installed.')
                raise ValueError(f'Failed to parse Excel file: {str(e)}. Please ensure it is a valid Excel file.')

        elif name.endswith('.json'):
            # try ndjson first
            s = None
            try:
                s = contents.decode('utf-8')
            except Exception:
                try:
                    s = contents.decode('latin1', errors='ignore')
                except Exception:
                    raise ValueError('Unable to decode JSON file. Please ensure it is valid UTF-8 encoded JSON.')
            
            try:
                lines = [l for l in s.splitlines() if l.strip()]
                if len(lines) > 1 and all(l.strip().startswith('{') for l in lines[:5]):
                    # ndjson
                    records = [json.loads(l) for l in lines[:sample_rows]]
                    df = pd.json_normalize(records)
                    if df.empty:
                        raise ValueError('JSON file contains no data.')
                    return {os.path.splitext(filename)[0]: df}
                else:
                    # try full json array
                    try:
                        obj = json.loads(s)
                        if isinstance(obj, list):
                            if not obj:
                                raise ValueError('JSON array is empty.')
                            df = pd.json_normalize(obj[:sample_rows])
                            return {os.path.splitext(filename)[0]: df}
                        elif isinstance(obj, dict):
                            # single object -> flatten
                            df = pd.json_normalize([obj])
                            return {os.path.splitext(filename)[0]: df}
                    except json.JSONDecodeError as e:
                        raise ValueError(f'Invalid JSON format: {str(e)}')
                    except Exception:
                        pass
                    # fallback to csv parse
                    df = safe_read_csv(s, sep=',', nrows=sample_rows)
                    return {os.path.splitext(filename)[0]: df}
            except ValueError:
                raise
            except Exception as e:
                raise ValueError(f'Failed to parse JSON file: {str(e)}. Please ensure it is valid JSON or NDJSON format.')

        elif name.endswith('.parquet'):
            try:
                # pandas will use pyarrow/fastparquet
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.parquet')
                tmp.write(contents); tmp.close()
                df = pd.read_parquet(tmp.name)
                if df.empty:
                    raise ValueError('Parquet file contains no data.')
                return {os.path.splitext(filename)[0]: df.head(sample_rows)}
            except Exception as e:
                if 'pyarrow' in str(e) or 'fastparquet' in str(e):
                    raise ValueError('Missing required library for Parquet files. Please ensure pyarrow is installed.')
                raise ValueError(f'Failed to parse Parquet file: {str(e)}. Please ensure it is a valid Parquet file.')

        else:
            # unknown extension — attempt csv then json
            ext = os.path.splitext(filename)[1]
            supported = ', '.join(SUPPORTED_EXTENSIONS)
            raise ValueError(f'Unsupported file extension "{ext}". Supported formats: {supported}')
    finally:
        if tmp is not None:
            try:
                os.unlink(tmp.name)
            except Exception:
                pass


def detect_column_types(df: pd.DataFrame) -> Dict[str, str]:
    """Return a mapping column -> detected type: numeric, datetime, categorical, boolean, text, geo"""
    types = {}
    for col in df.columns:
        ser = df[col]
        # drop nulls for detection
        s = ser.dropna()
        if s.empty:
            types[col] = 'unknown'
            continue
        # booleans
        if pd.api.types.is_bool_dtype(s) or set(s.dropna().unique()) <= {0,1,True,False}:
            types[col] = 'boolean'; continue
        # numeric
        if pd.api.types.is_numeric_dtype(s):
            types[col] = 'numeric'; continue
        # datetime
        try:
            parsed = pd.to_datetime(s.sample(min(len(s), min(100, len(s)))), errors='coerce', utc=True)
            if parsed.notnull().sum() >= max(1, int(0.6 * len(parsed))):
                types[col] = 'datetime'; continue
        except Exception:
            pass
        # geo detection: lat/lon pairs
        if col.lower() in ('lat','latitude') or col.lower() in ('lon','lng','longitude'):
            types[col] = 'geo'; continue
        # small cardinality -> categorical
        unique_frac = s.nunique(dropna=True) / max(1, len(s))
        if unique_frac < 0.05 and s.nunique() < 200:
            types[col] = 'categorical'; continue
        # text/varchar
        if pd.api.types.is_string_dtype(s):
            types[col] = 'text'; continue
        # fallback
        types[col] = 'unknown'
    return types


def safe_float(v):
    if pd.isna(v) or np.isnan(v) or np.isinf(v):
        return None
    return float(v)

def profile_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    """Return a lightweight profile — per-column stats and dataset-level notes"""
    profile = {}
    total_rows = len(df)
    profile['total_rows'] = int(total_rows)
    profile['total_columns'] = int(df.shape[1])
    col_types = detect_column_types(df)
    profile['columns'] = {}
    for col in df.columns:
        ser = df[col]
        non_null = ser.dropna()
        col_prof = {
            'type': col_types.get(col, 'unknown'),
            'count': int(len(ser)),
            'missing': int(ser.isnull().sum()),
            'missing_pct': safe_float(ser.isnull().mean()),
            'unique': int(ser.nunique(dropna=True)),
        }
        t = col_prof['type']
        if t == 'numeric':
            try:
                s = pd.to_numeric(non_null, errors='coerce').dropna()
                if not s.empty:
                    col_prof.update({
                        'mean': safe_float(s.mean()),
                        'median': safe_float(s.median()),
                        'std': safe_float(s.std(ddof=0)),
                        'min': safe_float(s.min()),
                        'max': safe_float(s.max())
                    })
            except Exception:
                pass
        elif t == 'datetime':
            try:
                s = pd.to_datetime(non_null, errors='coerce', utc=True).dropna()
                if not s.empty:
                    col_prof.update({
                        'min': str(s.min()),
                        'max': str(s.max())
                    })
            except Exception:
                pass
        elif t in ('categorical','text','boolean'):
            try:
                top = non_null.astype(str).value_counts().head(5).to_dict()
                col_prof['top_values'] = {k: int(v) for k,v in top.items()}
            except:
                pass
        profile['columns'][col] = col_prof
    # quick notes
    notes = []
    if total_rows > 200000:
        notes.append('Large dataset — profiling was sampled and some operations limited for performance')
    profile['notes'] = notes
    return profile


def detect_duplicates(df: pd.DataFrame) -> Dict[str, Any]:
    """Return duplicate stats"""
    total_rows = len(df)
    duplicates = df[df.duplicated()]
    num_duplicates = len(duplicates)
    
    return {
        'count': int(num_duplicates),
        'percentage': safe_float(num_duplicates / max(1, total_rows)),
        'samples': duplicates.head(5).to_dict(orient='records') if num_duplicates > 0 else []
    }

def detect_quality_issues(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Return list of potential issues"""
    issues = []
    # Check for empty columns
    for col in df.columns:
        missing = df[col].isnull().mean()
        if missing > 0.4:
            issues.append({'type': 'critical', 'column': col, 'message': f'High missing values ({missing:.1%})'})
        elif missing > 0.1:
            issues.append({'type': 'warning', 'column': col, 'message': f'Identify missing values ({missing:.1%})'})
            
    # Check for constant columns
    for col in df.columns:
        if df[col].nunique() <= 1 and len(df) > 1:
            issues.append({'type': 'warning', 'column': col, 'message': 'Constant column (zero variance)'})
            
    return issues

def preprocess_dataset(df: pd.DataFrame, options: Dict[str, bool]) -> pd.DataFrame:
    """Apply cleaning operations"""
    df_clean = df.copy()
    
    # 1. Drop duplicates
    if options.get('remove_duplicates'):
        df_clean = df_clean.drop_duplicates()
        
    # 2. Handle missing values
    if options.get('impute_missing'):
        # Numeric -> median
        numeric_cols = df_clean.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if df_clean[col].isnull().any():
                df_clean[col] = df_clean[col].fillna(df_clean[col].median())
        
        # Categorical -> mode
        cat_cols = df_clean.select_dtypes(include=['object', 'category']).columns
        for col in cat_cols:
            if df_clean[col].isnull().any():
                if not df_clean[col].mode().empty:
                    df_clean[col] = df_clean[col].fillna(df_clean[col].mode()[0])
                    
    # 3. Drop constant columns
    if options.get('drop_constant'):
        cols_to_drop = [c for c in df_clean.columns if df_clean[c].nunique() <= 1]
        df_clean = df_clean.drop(columns=cols_to_drop)
        
    return df_clean


def recommend_visualizations(df: pd.DataFrame, col_types: Dict[str,str]) -> List[Dict[str,Any]]:
    """Return a list of recommended visualizations based on detected types and cardinalities"""
    recs = []
    # detect time series candidates
    time_cols = [c for c,t in col_types.items() if t == 'datetime']
    numeric_cols = [c for c,t in col_types.items() if t == 'numeric']
    cat_cols = [c for c,t in col_types.items() if t == 'categorical']
    geo_cols = [c for c,t in col_types.items() if t == 'geo']

    if time_cols and numeric_cols:
        recs.append({'type':'line', 'x': time_cols[0], 'y': numeric_cols[:3], 'reason':'Datetime + numeric columns -> time series'})
    if numeric_cols:
        for n in numeric_cols[:6]:
            recs.append({'type':'histogram', 'column': n, 'reason':'Numeric distribution'})
    if len(numeric_cols) >= 2:
        recs.append({'type':'scatter', 'x': numeric_cols[0], 'y': numeric_cols[1], 'reason':'Two numeric columns -> scatter'})
    if cat_cols:
        for c in cat_cols[:6]:
            # Recommend Pie chart if cardinality is low (<= 10)
            if df[c].nunique() <= 10:
                 recs.append({'type':'pie', 'column': c, 'reason':'Categorical composition (Pie)'})
            else:
                 recs.append({'type':'bar', 'column': c, 'reason':'Categorical counts'})
    if geo_cols:
        recs.append({'type':'map', 'lat': [c for c in geo_cols if 'lat' in c.lower()][0] if any('lat' in c.lower() for c in geo_cols) else geo_cols[0],
                    'lon': [c for c in geo_cols if 'lon' in c.lower()][0] if any('lon' in c.lower() for c in geo_cols) else None,
                    'reason':'Geo columns -> scatter map'})
    # correlation heatmap if many numerics
    if len(numeric_cols) >= 2:
        recs.append({'type':'heatmap', 'columns': numeric_cols[:12], 'reason':'Correlation/heatmap for numeric columns'})
    return recs

# ---------- Routes ----------

@app.get('/', response_class=HTMLResponse)
async def index():
    with open('static/index.html', 'r', encoding='utf-8') as f:
        return f.read()

@app.post('/upload')
async def upload(file: UploadFile = File(...), sample_rows: int = Form(5000)):
    # Validate file is provided
    if not file.filename:
        return JSONResponse({
            'error': 'No file provided',
            'suggestion': 'Please select a file to upload'
        }, status_code=400)
    
    # Validate file extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return JSONResponse({
            'error': f'Unsupported file type: {ext}',
            'suggestion': f'Please upload one of these formats: {', '.join(SUPPORTED_EXTENSIONS)}'
        }, status_code=400)
    
    # Validate file size (content-length header if available, otherwise check during stream)
    content_length = file.size
    if content_length and content_length > MAX_FILE_SIZE:
        size_gb = content_length / (1024 * 1024 * 1024)
        return JSONResponse({
            'error': f'File size ({size_gb:.1f}GB) exceeds maximum limit of 25GB',
            'suggestion': 'Please upload a smaller file'
        }, status_code=400)
    
    file_size = 0
    temp_file_path = None
    
    try:
        # Stream file to temporary disk storage
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            temp_file_path = tmp.name
            # Copy in chunks to avoid memory issues
            import shutil
            shutil.copyfileobj(file.file, tmp)
            file_size = os.path.getsize(temp_file_path)
    except Exception as e:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        return JSONResponse({'error': f'Upload failed: {str(e)}'}, status_code=500)

    # Re-validate size after upload
    if file_size > MAX_FILE_SIZE:
        os.unlink(temp_file_path)
        return JSONResponse({
            'error': 'File size exceeds maximum limit of 25GB',
        }, status_code=400)

    if file_size == 0:
        os.unlink(temp_file_path)
        return JSONResponse({
            'error': 'File is empty',
        }, status_code=400)
    
    # Select optimal backend
    backend = select_backend(file_size, ext)
    is_large_file = file_size > LARGE_FILE_THRESHOLD
    file_size_mb = file_size / (1024 * 1024)
    
    # Process based on backend
    try:
        if backend == 'duckdb' and ext in ['.csv', '.parquet']:
             # Use DuckDB backend with the temp file
            with DuckDBBackend(temp_file_path) as db:
                load_result = db.load_file()
                if not load_result['success']:
                    raise ValueError(f"DuckDB loading failed: {load_result['error']}")
                
                total_rows = load_result['rows']
                sample_size = adaptive_sample_size(total_rows, file_size_mb)
                df = db.get_sample(n=sample_size, method='random')
                original_rows = total_rows
                
            # Create sheets dict for compatibility
            sheets = {'sheet1': df}
            
        else:
            # For pandas, we need to read the file content from the temp file
            # This is less efficient for >1GB files but necessary if not using DuckDB
            with open(temp_file_path, 'rb') as f:
                contents = f.read()
            sheets = parse_uploaded_file(contents, file.filename, sample_rows=sample_rows if not is_large_file else MAX_SAMPLE_ROWS)
            original_rows = len(sheets[list(sheets.keys())[0]]) # Approx for non-DuckDB
            
    except Exception as e:
        if os.path.exists(temp_file_path):
             os.unlink(temp_file_path)
        return JSONResponse({
            'error': str(e),
            'suggestion': 'Processing failed. Try a different format.'
        }, status_code=500)
    finally:
        # Clean up temp file
        if os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except:
                pass
        
    # coerce columns to strings
    df.columns = [str(c) for c in df.columns]

    # lightweight coercions: try numeric conversion where many values look numeric
    numeric_cols = []
    for col in df.columns:
        coerced = pd.to_numeric(df[col], errors='coerce')
        if coerced.notnull().sum() >= max(1, int(0.5 * len(coerced))):
            df[col] = coerced
            numeric_cols.append(col)
    # try parse datetimes
    for col in df.columns:
        if col in numeric_cols: continue
        coerced = pd.to_datetime(df[col], errors='coerce', utc=True)
        if coerced.notnull().sum() >= max(1, int(0.5 * len(coerced))):
            df[col] = coerced

    profile = profile_dataframe(df)
    col_types = detect_column_types(df)
    recs = recommend_visualizations(df, col_types)

    # Prepare preview data (convert to json-friendly)
    # Use pandas to_json for robust serialization of NaNs, Infinity, and Timestamps
    df_preview = df.head(sample_rows).copy()
    try:
        # orient='records' gives list of dicts
        # date_format='iso' converts timestamps to standard ISO strings
        # double_precision=15 preserves float precision
        # default_handler=str handles unknown objects
        json_str = df_preview.to_json(orient='records', date_format='iso', double_precision=15, default_handler=str)
        preview = json.loads(json_str)
    except Exception as e:
        # Fallback if to_json fails (rare)
        print(f"Serialization warning: {e}")
        df_preview = df_preview.astype(str)
        preview = df_preview.to_dict(orient='records')

    response = {
        'filename': file.filename,
        'headers': list(df.columns),
        'data_preview': preview,
        'total_rows': int(original_rows),  # Original row count before sampling
        'sampled_rows': int(len(df)),  # Actual rows used for visualization
        'is_sampled': original_rows > len(df),
        'is_large_file': is_large_file,
        'file_size_mb': round(file_size_mb, 2),
        'backend': backend,  # Show which backend was used
        'profile': profile,
        'column_types': col_types,
        'recommendations': recs,
        'duplicates': detect_duplicates(df),
        'quality_issues': detect_quality_issues(df)
    }
    return JSONResponse(response)


@app.post('/preprocess')
async def preprocess_data(
    file_id: str = Form(None), # Not used in this stateless version, we re-upload or would need persistence. 
    # For this single-file demo, we will accept the file again OR just assume the user re-uploads.
    # To make it "smooth", let's assume the user sends the file again for preprocessing OR we cache the last upload.
    # Let's simple-store the last dataframe in memory for this demo session or accept file again.
    # BETTER APPROACH for this stateless app: User re-uploads file with options.
    file: UploadFile = File(...),
    remove_duplicates: bool = Form(False),
    impute_missing: bool = Form(False),
    drop_constant: bool = Form(False)
):
    try:
        contents = await file.read()
        sheets = parse_uploaded_file(contents, file.filename, sample_rows=1000000) # Read all for cleaning
        df = sheets[list(sheets.keys())[0]]
        
        # Preprocess
        options = {
            'remove_duplicates': remove_duplicates,
            'impute_missing': impute_missing,
            'drop_constant': drop_constant
        }
        df_clean = preprocess_dataset(df, options)
        
        # Store for download
        download_id = str(uuid.uuid4())
        cleaned_datasets_store[download_id] = {
            'df': df_clean,
            'filename': f"clean_{file.filename}"
        }
        
        # Return summary of cleaned data
        return JSONResponse({
            'status': 'success',
            'original_rows': len(df),
            'cleaned_rows': len(df_clean),
            'download_id': download_id,
            'download_url': f"/download/{download_id}"
        })
        
    except Exception as e:
        return JSONResponse({'error': str(e)}, status_code=400)

@app.get('/download/{download_id}')
async def download_clean(download_id: str, format: str = 'csv'):
    """Download cleaned dataset in specified format"""
    if download_id not in cleaned_datasets_store:
        return JSONResponse({'error': 'Download ID not found or expired'}, status_code=404)
    
    data = cleaned_datasets_store[download_id]
    df = data['df']
    orig_name = data['filename']
    base_name = orig_name.rsplit('.', 1)[0] if '.' in orig_name else orig_name
    
    # Support multiple formats
    if format == 'csv':
        stream = io.StringIO()
        df.to_csv(stream, index=False)
        content = stream.getvalue()
        media_type = "text/csv"
        filename = f"{base_name}.csv"
        
    elif format == 'xlsx':
        output = io.BytesIO()
        df.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)
        content = output.getvalue()
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"{base_name}.xlsx"
        
    elif format == 'json':
        content = df.to_json(orient='records', indent=2)
        media_type = "application/json"
        filename = f"{base_name}.json"
        
    elif format == 'parquet':
        output = io.BytesIO()
        df.to_parquet(output, index=False, engine='pyarrow')
        output.seek(0)
        content = output.getvalue()
        media_type = "application/octet-stream"
        filename = f"{base_name}.parquet"
        
    else:
        return JSONResponse({'error': 'Unsupported format. Use: csv, xlsx, json, or parquet'}, status_code=400)
    
    response = Response(content=content, media_type=media_type)
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response


@app.post('/generate_report')
async def generate_report(file: UploadFile = File(...)):
    """Generate a comprehensive analysis report"""
    try:
        # Read file
        contents = await file.read()
        
        # Parse file (reuse existing logic)
        sheets = parse_uploaded_file(contents, file.filename, sample_rows=10000)
        primary_name = list(sheets.keys())[0]
        df = sheets[primary_name].copy()
        
        # Optimize and sample if needed
        if len(df) > 50000:
            df = smart_sample(df, 50000)
        
        df.columns = [str(c) for c in df.columns]
        
        # Get analysis
        col_types = infer_column_types(df)
        profile = profile_columns(df, col_types)
        duplicates = detect_duplicates(df)
        quality_issues = detect_quality_issues(df)
        
        # Generate HTML report
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Dataset Analysis Report - {file.filename}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px;
            background: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #6366f1, #a855f7);
            color: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5rem;
        }}
        .header p {{
            margin: 10px 0 0 0;
            opacity: 0.9;
        }}
        .section {{
            background: white;
            padding: 25px;
            margin-bottom: 20px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .section h2 {{
            color: #6366f1;
            margin-top: 0;
            border-bottom: 2px solid #e5e7eb;
            padding-bottom: 10px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .stat-card {{
            background: #f9fafb;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #6366f1;
        }}
        .stat-label {{
            font-size: 0.9rem;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .stat-value {{
            font-size: 2rem;
            font-weight: bold;
            color: #1f2937;
            margin-top: 5px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e5e7eb;
        }}
        th {{
            background: #f9fafb;
            font-weight: 600;
            color: #374151;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85rem;
            font-weight: 600;
        }}
        .badge-numeric {{ background: #dbeafe; color: #1e40af; }}
        .badge-categorical {{ background: #fce7f3; color: #9f1239; }}
        .badge-datetime {{ background: #d1fae5; color: #065f46; }}
        .issue-warning {{ color: #f59e0b; }}
        .issue-critical {{ color: #ef4444; }}
        .footer {{
            text-align: center;
            color: #6b7280;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Dataset Analysis Report</h1>
        <p><strong>File:</strong> {file.filename}</p>
        <p><strong>Generated:</strong> {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="section">
        <h2>📈 Dataset Overview</h2>
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Rows</div>
                <div class="stat-value">{len(df):,}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Columns</div>
                <div class="stat-value">{len(df.columns)}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Duplicates</div>
                <div class="stat-value">{duplicates['count']}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Quality Issues</div>
                <div class="stat-value">{len(quality_issues)}</div>
            </div>
        </div>
    </div>
    
    <div class="section">
        <h2>📋 Column Information</h2>
        <table>
            <thead>
                <tr>
                    <th>Column Name</th>
                    <th>Type</th>
                    <th>Missing</th>
                    <th>Unique</th>
                    <th>Details</th>
                </tr>
            </thead>
            <tbody>
"""
        
        # Add column details
        for col, info in profile.items():
            col_type = col_types.get(col, 'unknown')
            badge_class = f"badge-{col_type}" if col_type in ['numeric', 'categorical', 'datetime'] else 'badge'
            
            details = ""
            if col_type == 'numeric':
                details = f"Mean: {info.get('mean', 'N/A'):.2f}" if isinstance(info.get('mean'), (int, float)) else ""
            elif col_type == 'categorical':
                details = f"Top: {info.get('top', 'N/A')}"
            elif col_type == 'datetime':
                details = f"Range: {info.get('min', 'N/A')} to {info.get('max', 'N/A')}"
            
            html_content += f"""
                <tr>
                    <td><strong>{col}</strong></td>
                    <td><span class="badge {badge_class}">{col_type}</span></td>
                    <td>{info.get('missing', 0)} ({info.get('missing_pct', 0):.1f}%)</td>
                    <td>{info.get('unique', 0)}</td>
                    <td>{details}</td>
                </tr>
"""
        
        html_content += """
            </tbody>
        </table>
    </div>
"""
        
        # Quality issues section
        if quality_issues:
            html_content += """
    <div class="section">
        <h2>⚠️ Data Quality Issues</h2>
        <table>
            <thead>
                <tr>
                    <th>Column</th>
                    <th>Issue</th>
                    <th>Severity</th>
                </tr>
            </thead>
            <tbody>
"""
            for issue in quality_issues:
                severity_class = 'issue-critical' if issue['severity'] == 'critical' else 'issue-warning'
                html_content += f"""
                <tr>
                    <td><strong>{issue['column']}</strong></td>
                    <td>{issue['issue']}</td>
                    <td class="{severity_class}">{issue['severity'].upper()}</td>
                </tr>
"""
            html_content += """
            </tbody>
        </table>
    </div>
"""
        
        html_content += """
    <div class="footer">
        <p>Generated by Dataset Visualization & Preprocessing Tool</p>
        <p>Powered by FastAPI, Pandas, and DuckDB</p>
    </div>
</body>
</html>
"""
        
        # Convert to PDF
        if WEASYPRINT_AVAILABLE:
            pdf_io = io.BytesIO()
            HTML(string=html_content).write_pdf(pdf_io)
            pdf_io.seek(0)
            
            return Response(
                content=pdf_io.getvalue(),
                media_type='application/pdf',
                headers={
                    'Content-Disposition': f'attachment; filename="report_{file.filename.rsplit(".", 1)[0]}.pdf"'
                }
            )
        else:
            # Fallback to HTML if WeasyPrint is not installed
            return HTMLResponse(
                content=html_content,
                headers={
                    'Content-Disposition': f'attachment; filename="report_{file.filename.rsplit(".", 1)[0]}.html"'
                }
            )
        
    except Exception as e:
        return JSONResponse({
            'error': f'Failed to generate report: {str(e)}'
        }, status_code=500)


@app.post('/correlation_matrix')
async def correlation_matrix(file: UploadFile = File(...)):
    """Generate correlation matrix for numeric columns"""
    try:
        contents = await file.read()
        sheets = parse_uploaded_file(contents, file.filename, sample_rows=50000)
        df = sheets[list(sheets.keys())[0]].copy()
        
        # Get numeric columns only
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        if len(numeric_cols) < 2:
            return JSONResponse({
                'error': 'Need at least 2 numeric columns for correlation analysis'
            }, status_code=400)
        
        # Calculate correlation
        corr_matrix = df[numeric_cols].corr()
        
        # Convert to format suitable for heatmap
        correlation_data = {
            'columns': numeric_cols,
            'matrix': corr_matrix.values.tolist(),
            'pairs': []
        }
        
        # Find strong correlations (|r| > 0.7)
        for i in range(len(numeric_cols)):
            for j in range(i+1, len(numeric_cols)):
                corr_val = corr_matrix.iloc[i, j]
                if abs(corr_val) > 0.7:
                    correlation_data['pairs'].append({
                        'col1': numeric_cols[i],
                        'col2': numeric_cols[j],
                        'correlation': round(corr_val, 3),
                        'strength': 'strong' if abs(corr_val) > 0.9 else 'moderate'
                    })
        
        return JSONResponse(correlation_data)
        
    except Exception as e:
        return JSONResponse({'error': str(e)}, status_code=500)


@app.post('/advanced_preprocess')
async def advanced_preprocess(
    file: UploadFile = File(...),
    normalize: bool = Form(False),
    standardize: bool = Form(False),
    one_hot_encode: bool = Form(False),
    handle_outliers: str = Form('none'),  # none, remove, cap
    create_date_features: bool = Form(False),
    selected_columns: str = Form(None)  # JSON string of column names
):
    """Advanced preprocessing with more options"""
    try:
        contents = await file.read()
        sheets = parse_uploaded_file(contents, file.filename, sample_rows=100000)
        df = sheets[list(sheets.keys())[0]].copy()
        
        # Filter columns if specified
        if selected_columns:
            cols = json.loads(selected_columns)
            df = df[cols]
        
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        datetime_cols = df.select_dtypes(include=['datetime64']).columns.tolist()
        
        changes = []
        
        # Normalize (0-1 scaling)
        if normalize and numeric_cols:
            for col in numeric_cols:
                min_val = df[col].min()
                max_val = df[col].max()
                if max_val > min_val:
                    df[col] = (df[col] - min_val) / (max_val - min_val)
            changes.append(f"Normalized {len(numeric_cols)} numeric columns to 0-1 range")
        
        # Standardize (z-score)
        if standardize and numeric_cols:
            for col in numeric_cols:
                mean_val = df[col].mean()
                std_val = df[col].std()
                if std_val > 0:
                    df[col] = (df[col] - mean_val) / std_val
            changes.append(f"Standardized {len(numeric_cols)} numeric columns (z-score)")
        
        # One-hot encode categorical
        if one_hot_encode and categorical_cols:
            # Limit to columns with <10 unique values
            cols_to_encode = [col for col in categorical_cols if df[col].nunique() < 10]
            if cols_to_encode:
                df = pd.get_dummies(df, columns=cols_to_encode, prefix=cols_to_encode)
                changes.append(f"One-hot encoded {len(cols_to_encode)} categorical columns")
        
        # Handle outliers
        if handle_outliers != 'none' and numeric_cols:
            for col in numeric_cols:
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                if handle_outliers == 'remove':
                    df = df[(df[col] >= lower_bound) & (df[col] <= upper_bound)]
                elif handle_outliers == 'cap':
                    df[col] = df[col].clip(lower=lower_bound, upper=upper_bound)
            
            changes.append(f"Handled outliers in {len(numeric_cols)} columns ({handle_outliers})")
        
        # Create date features
        if create_date_features and datetime_cols:
            for col in datetime_cols:
                df[f'{col}_year'] = df[col].dt.year
                df[f'{col}_month'] = df[col].dt.month
                df[f'{col}_day'] = df[col].dt.day
                df[f'{col}_dayofweek'] = df[col].dt.dayofweek
                df = df.drop(columns=[col])
            changes.append(f"Created date features from {len(datetime_cols)} datetime columns")
        
        # Store for download
        download_id = str(uuid.uuid4())
        cleaned_datasets_store[download_id] = {
            'df': df,
            'filename': f"advanced_{file.filename}"
        }
        
        return JSONResponse({
            'status': 'success',
            'original_rows': len(sheets[list(sheets.keys())[0]]),
            'processed_rows': len(df),
            'original_cols': len(sheets[list(sheets.keys())[0]].columns),
            'processed_cols': len(df.columns),
            'changes': changes,
            'download_id': download_id,
            'download_url': f"/download/{download_id}"
        })
        
    except Exception as e:
        return JSONResponse({'error': str(e)}, status_code=500)


@app.post('/column_info')
async def column_info(file: UploadFile = File(...)):
    """Get detailed column information for filtering"""
    try:
        contents = await file.read()
        sheets = parse_uploaded_file(contents, file.filename, sample_rows=10000)
        df = sheets[list(sheets.keys())[0]].copy()
        
        col_types = infer_column_types(df)
        
        columns_info = []
        for col in df.columns:
            col_type = col_types.get(col, 'unknown')
            columns_info.append({
                'name': col,
                'type': col_type,
                'missing': int(df[col].isnull().sum()),
                'missing_pct': round(df[col].isnull().sum() / len(df) * 100, 1),
                'unique': int(df[col].nunique()),
                'sample_values': df[col].dropna().head(3).tolist() if len(df[col].dropna()) > 0 else []
            })
        
        return JSONResponse({
            'columns': columns_info,
            'total_columns': len(columns_info),
            'types_summary': {
                'numeric': sum(1 for c in columns_info if c['type'] == 'numeric'),
                'categorical': sum(1 for c in columns_info if c['type'] == 'categorical'),
                'datetime': sum(1 for c in columns_info if c['type'] == 'datetime'),
                'other': sum(1 for c in columns_info if c['type'] not in ['numeric', 'categorical', 'datetime'])
            }
        })
        
    except Exception as e:
        return JSONResponse({'error': str(e)}, status_code=500)


if __name__ == '__main__':
    print('Starting enhanced EDA server on http://localhost:8081')
    uvicorn.run('app:app', host='0.0.0.0', port=8081, reload=False)
