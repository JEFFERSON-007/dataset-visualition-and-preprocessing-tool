
import os
import sys
import logging
import json
import uuid
import shutil
import asyncio
import tempfile
import threading
import webbrowser
import warnings
import io
import time
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# Data Science
import pandas as pd
import numpy as np

# FastAPI
from fastapi import FastAPI, UploadFile, File, Form, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

# --- Configuration & Setup ---

# Constants
MAX_FILE_SIZE = 25 * 1024 * 1024 * 1024  # 25GB
LARGE_FILE_THRESHOLD = 500 * 1024 * 1024 # 500MB (Switch to DuckDB/Chunking)
MAX_SAMPLE_ROWS = 10000
SESSION_STORE = {} 
BUILD_VERSION = "19:05" # Unique marker to verify build

# Optional Dependencies
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
except Exception:
    WEASYPRINT_AVAILABLE = False

app = FastAPI(title="DataLyze - Premium EDA Tool")

# Logging Setup
import logging
import sys
import os
import traceback

def get_log_path():
    try:
        if getattr(sys, 'frozen', False):
            # If frozen, store log next to exe
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.getcwd()
        return os.path.join(base_path, 'datalyze_debug.log')
    except Exception:
        return 'datalyze_debug.log'

log_file = get_log_path()

try:
    logging.basicConfig(
        filename=log_file,
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
except Exception as e:
    # If logging fails, just print to stderr (will show in console if open)
    sys.stderr.write(f"Failed to setup logging: {e}\n")

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Static Files with versioning
static_path = resource_path("static")
if not os.path.exists(static_path):
    os.makedirs(static_path, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_path), name="static")

templates = Jinja2Templates(directory=static_path)

# Ignore warnings
warnings.filterwarnings('ignore')

# --- Core Logic (Refactored) ---

class DataProcessor:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=min(32, (os.cpu_count() or 1) + 4))

    def detect_column_types(self, df: pd.DataFrame) -> Dict[str, str]:
        """Heuristic type detection"""
        types = {}
        for col in df.columns:
            s = df[col].dropna()
            if s.empty:
                types[col] = 'unknown'
                continue
            
            # Boolean
            if pd.api.types.is_bool_dtype(s) or set(s.unique()) <= {0, 1, True, False, 'True', 'False'}:
                types[col] = 'boolean'
                continue
            
            # Numeric
            if pd.api.types.is_numeric_dtype(s):
                types[col] = 'numeric'
                continue
            
            # Datetime (Sampling for speed)
            try:
                sample = s.sample(min(len(s), 500), random_state=42)
                parsed = pd.to_datetime(sample, errors='coerce', utc=True)
                if parsed.notnull().mean() > 0.6:
                    types[col] = 'datetime'
                    continue
            except:
                pass
            
            # Geo
            lower_col = col.lower()
            if 'fat' in lower_col or 'lat' in lower_col or 'lon' in lower_col:
                if pd.to_numeric(s, errors='coerce').notnull().all():
                     types[col] = 'geo'
                     continue

            # Categorical vs Text
            if s.nunique() / len(s) < 0.1 or s.nunique() < 20: 
                types[col] = 'categorical'
                continue
                
            types[col] = 'text'
        return types

    def _profile_column(self, col: str, series: pd.Series, dtype: str) -> tuple:
        """Worker for column profiling"""
        stats = {
            'type': dtype,
            'missing': int(series.isnull().sum()),
            'unique': int(series.nunique())
        }
        
        if dtype == 'numeric':
            stats.update({
                'min': float(series.min()) if not series.empty else None,
                'max': float(series.max()) if not series.empty else None,
                'mean': float(series.mean()) if not series.empty else None,
            })
        elif dtype == 'categorical':
            stats['top'] = series.value_counts().head(5).to_dict()
            
        return col, stats

    def profile_dataframe(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Multi-threaded profiling of all columns and health check"""
        col_types = self.detect_column_types(df)
        
        # Health Checks
        duplicates = int(df.duplicated().sum())
        health_issues = []
        
        if duplicates > 0:
            health_issues.append({
                'type': 'warning',
                'title': f'{duplicates} Duplicate Rows',
                'desc': 'Identical rows detected. Consider clearing them.'
            })

        profile = {
            'total_rows': int(len(df)),
            'total_columns': int(df.shape[1]),
            'columns': {},
            'duplicates': duplicates,
            'health': health_issues,
            'notes': []
        }
        
        # Parallel execution for column stats
        futures = {self.executor.submit(self._profile_column, col, df[col], col_types[col]): col for col in df.columns}
        
        for future in as_completed(futures):
            col, stats = future.result()
            profile['columns'][col] = stats
            
            # Additional column-level health checks
            if stats['missing'] > 0:
                health_issues.append({
                    'type': 'info',
                    'title': f'Missing: {col}',
                    'desc': f'{stats["missing"]} records are empty.'
                })
            if stats['unique'] == 1 and len(df) > 1:
                health_issues.append({
                    'type': 'warning',
                    'title': f'Constant: {col}',
                    'desc': 'Column has only one value.'
                })

        if len(df) > 200000:
            profile['notes'].append("Warning: Profiling sampled for performance.")
            
        return profile

    def recommend_visualizations(self, df: pd.DataFrame, col_types: Dict[str, str]) -> List[Dict]:
        """Rule-based Viz Recommendation Engine"""
        recs = []
        
        # 1. Timeline (Datetime + Numeric)
        date_cols = [c for c, t in col_types.items() if t == 'datetime']
        num_cols = [c for c, t in col_types.items() if t == 'numeric']
        cat_cols = [c for c, t in col_types.items() if t == 'categorical']
        
        if date_cols and num_cols:
            recs.append({
                'type': 'line',
                'title': f'{num_cols[0]} over Time',
                'x': date_cols[0],
                'y': num_cols[0],
                'reason': 'Found time-series data'
            })
            
        # 2. Distribution (Numeric)
        for col in num_cols[:2]:
            recs.append({
                'type': 'histogram',
                'title': f'Distribution of {col}',
                'column': col,
                'reason': f'Analyze distribution of {col}'
            })
            # Box plot
            recs.append({
                'type': 'box',
                'title': f'Box Plot of {col}',
                'column': col,
                'reason': 'Detect outliers'
            })

        # 3. Categorical Counts
        for col in cat_cols[:2]:
            recs.append({
                'type': 'bar',
                'title': f'Count by {col}',
                'column': col,
                'reason': f'Compare categories in {col}'
            })
            recs.append({
                'type': 'pie',
                'title': f'Market Share: {col}',
                'column': col,
                'reason': 'Part-to-whole relationship'
            })
            
        # 4. Correlation (Num vs Num)
        if len(num_cols) >= 2:
            recs.append({
                'type': 'scatter',
                'title': f'{num_cols[0]} vs {num_cols[1]}',
                'x': num_cols[0],
                'y': num_cols[1],
                'reason': 'Correlation check'
            })
            
        return recs

    def merge_datasets(self, df_left: pd.DataFrame, df_right: pd.DataFrame, 
                       left_on: str, right_on: str, how: str = 'inner') -> pd.DataFrame:
        """Merge two dataframes with memory safety and DuckDB efficiency"""
        if left_on not in df_left.columns:
            raise ValueError(f"Column '{left_on}' not found in primary dataset")
        if right_on not in df_right.columns:
            raise ValueError(f"Column '{right_on}' not found in secondary dataset")

        # --- Memory Guard: Prevent Cartesian Explosion ---
        # Very large joins (e.g. many duplicates on both sides) crash standard RAM.
        # Estimate row count using value frequency overlap.
        try:
            l_counts = df_left[left_on].value_counts().head(50)
            r_counts = df_right[right_on].value_counts().head(50)
            
            est_explosion = 0
            for val, count in l_counts.items():
                if val in r_counts:
                    est_explosion += count * r_counts[val]
            
            # If top 50 keys alone create 20M+ rows, it's likely a dangerous merge
            if est_explosion > 20_000_000:
                raise MemoryError(f"Merge safety limit reached. This join would create too many rows (est. >{est_explosion}). Ensure your keys are unique or filter the data first.")
        except Exception as e:
            if isinstance(e, MemoryError): raise e
            logging.warning(f"Merge guard check failed: {e}")

        if left_on == right_on:
            # Drop the redundant key column from the right
            cols_to_keep = [col for col in merged.columns if not col.endswith(':1')]
            merged = merged[cols_to_keep]

        return merged

    def merge_datasets(self, df_left: pd.DataFrame, df_right: pd.DataFrame, 
                       left_on: str, right_on: str, how: str = 'inner') -> pd.DataFrame:
        """Merge two dataframes with multi-key support, memory safety and DuckDB efficiency"""
        # Parse potential multi-keys
        l_keys = [k.strip() for k in left_on.split(',') if k.strip()]
        r_keys = [k.strip() for k in right_on.split(',') if k.strip()]
        
        if len(l_keys) != len(r_keys):
            raise ValueError(f"Number of keys must match (Left: {len(l_keys)}, Right: {len(r_keys)})")

        for k in l_keys:
            if k not in df_left.columns: raise ValueError(f"Primary key '{k}' not found")
        for k in r_keys:
            if k not in df_right.columns: raise ValueError(f"Secondary key '{k}' not found")

        # --- Memory Guard ---
        try:
            # Quick check on first key for explosion
            l_counts = df_left[l_keys[0]].value_counts().head(20)
            r_counts = df_right[r_keys[0]].value_counts().head(20)
            est = sum(l_counts.get(k, 0) * r_counts.get(k, 0) for k in l_counts.index if k in r_counts.index)
            if est > 20_000_000:
                raise MemoryError(f"Safety Limit: This join is too large (est. >{est} rows).")
        except MemoryError as e: raise e
        except: pass

        # --- DuckDB Join ---
        import duckdb
        con = duckdb.connect(':memory:')
        try:
            sql_how = how.upper() if how != 'outer' else 'FULL'
            
            # Construct ON clause
            on_clause = " AND ".join([f'df_left."{lk}" = df_right."{rk}"' for lk, rk in zip(l_keys, r_keys)])
            
            # Select columns to handle collisions (suffixes)
            # Find overlapping columns (excluding keys)
            l_cols = set(df_left.columns)
            r_cols = set(df_right.columns)
            common = (l_cols & r_cols) - set(l_keys) - set(r_keys)
            
            select_parts = []
            for col in df_left.columns:
                select_parts.append(f'df_left."{col}"')
            for col in df_right.columns:
                if col in common:
                    select_parts.append(f'df_right."{col}" AS "{col}_secondary"')
                elif col not in l_keys and col not in r_keys:
                    select_parts.append(f'df_right."{col}"')
            
            query = f"""
            SELECT {', '.join(select_parts)}
            FROM df_left 
            {sql_how} JOIN df_right ON {on_clause}
            """
            return con.execute(query).df()
        except Exception as e:
            logging.error(f"DuckDB fail: {e}")
            return pd.merge(df_left, df_right, left_on=l_keys, right_on=r_keys, how=how, suffixes=('', '_secondary'))
        finally: con.close()

processor = DataProcessor()

# --- Helpers ---

def select_backend(file_size, ext):
    if file_size > LARGE_FILE_THRESHOLD and ext in ['.csv', '.parquet'] and DUCKDB_AVAILABLE:
        return 'duckdb'
    return 'pandas'

def save_to_session(session_id, df, filename):
    SESSION_STORE[session_id] = {
        'df': df,
        'filename': filename,
        'timestamp': pd.Timestamp.now()
    }
    # Simple Cleanup: Keep instances low
    if len(SESSION_STORE) > 10:
        oldest = min(SESSION_STORE.keys(), key=lambda k: SESSION_STORE[k]['timestamp'])
        del SESSION_STORE[oldest]

def get_from_session(session_id):
    return SESSION_STORE.get(session_id)

# --- Routes ---

@app.get('/', response_class=HTMLResponse)
async def index(request: Request):
    try:
        return templates.TemplateResponse("index.html", {
            "request": request, 
            "v": f"{BUILD_VERSION}_{int(time.time())}"
        })
    except Exception as e:
        return f"<h1>Critical Error</h1><p>{e}</p>"

@app.post('/upload')
async def upload_file(file: UploadFile = File(...), session_id: str = Form(None)):
    if not file.filename:
        return JSONResponse({'error': 'No file selected'}, 400)

    try:
        # Generate Session ID if new
        if not session_id:
            session_id = str(uuid.uuid4())

        # Save to temp
        ext = os.path.splitext(file.filename)[1].lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
        
        file_size = os.path.getsize(tmp_path)
        backend = select_backend(file_size, ext)
        
        # Load Data
        df = None
        if backend == 'duckdb':
            with DuckDBBackend(tmp_path) as db:
                res = db.load_file()
                if res['success']:
                    df = db.get_sample(n=MAX_SAMPLE_ROWS) # Load sample for analysis
                    # Note: DuckDB handling for merge/clean needs more complex connection management
        
        if df is None:
            # Pandas fallback
            if ext == '.csv':
                df = pd.read_csv(tmp_path, nrows=None if file_size < LARGE_FILE_THRESHOLD else 100000)
            elif ext == '.xlsx':
                df = pd.read_excel(tmp_path)
            elif ext == '.parquet':
                df = pd.read_parquet(tmp_path)
            elif ext == '.json':
                df = pd.read_json(tmp_path)
            else:
                # Text/TSV fallback
                try:
                    df = pd.read_csv(tmp_path, sep=None, engine='python')
                except:
                    os.unlink(tmp_path)
                    return JSONResponse({'error': 'Unsupported file format'}, 400)

        # Cleanup
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

        # Process
        df.columns = df.columns.astype(str) # Ensure string columns
        
        # Profile
        profile = processor.profile_dataframe(df)
        col_types = processor.detect_column_types(df)
        recs = processor.recommend_visualizations(df, col_types)
        
        # Preview
        preview = json.loads(df.head(1000).to_json(orient='records', date_format='iso', default_handler=str))

        # Save session
        save_to_session(session_id, df, file.filename)

        return JSONResponse({
            'session_id': session_id,
            'filename': file.filename,
            'total_rows': len(df),
            'columns': list(df.columns),
            'profile': profile,
            'recommendations': recs,
            'preview': preview,
            'col_types': col_types
        })

    except Exception as e:
        logging.exception("Upload failed")
        return JSONResponse({'error': str(e)}, 500)

@app.post('/merge')
async def merge_datasets(
    primary_id: str = Form(...),
    secondary_files: List[UploadFile] = File(...),
    left_key: str = Form(...),
    right_key: str = Form(...),
    how: str = Form('inner')
):
    """Merge one or more uploaded files with an existing session dataset"""
    try:
        session_data = get_from_session(primary_id)
        if not session_data: return JSONResponse({'error': 'Primary session expired'}, 404)
        
        # Process files one by one (Sequential merge)
        for s_file in secondary_files:
            ext = os.path.splitext(s_file.filename)[1].lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                shutil.copyfileobj(s_file.file, tmp)
                tmp_path = tmp.name
                
            try:
                if ext == '.csv': df_sec = pd.read_csv(tmp_path)
                elif ext == '.xlsx': df_sec = pd.read_excel(tmp_path)
                elif ext == '.parquet': df_sec = pd.read_parquet(tmp_path)
                else: df_sec = pd.read_csv(tmp_path, sep=None, engine='python')
                
                # Apply merge
                session_data['df'] = processor.merge_datasets(session_data['df'], df_sec, left_key, right_key, how)
            finally:
                if os.path.exists(tmp_path): os.unlink(tmp_path)
        
        session_data['filename'] = f"merged_result_{int(time.time())}.csv"
        df_final = session_data['df']

        return JSONResponse({
            'success': True,
            'total_rows': len(df_final),
            'columns': list(df_final.columns),
            'filename': session_data['filename']
        })

    except Exception as e:
        logging.exception("Merge failed")
        return JSONResponse({'error': str(e)}, 500)

@app.post('/clean')
async def clean_data(
    session_id: str = Form(...),
    remove_duplicates: bool = Form(False),
    impute_missing: bool = Form(False),
    drop_constant: bool = Form(False)
):
    try:
        data = get_from_session(session_id)
        if not data: return JSONResponse({'error': 'Session expired'}, 404)
        
        df = data['df']
        rows_before = len(df)
        
        if remove_duplicates:
            df = df.drop_duplicates()
            
        if drop_constant:
            df = df.loc[:, df.nunique() > 1]
            
        if impute_missing:
            # Simple imputation: Median for numeric, Mode for others
            for col in df.columns:
                if pd.api.types.is_numeric_dtype(df[col]):
                    df[col] = df[col].fillna(df[col].median())
                else:
                    df[col] = df[col].fillna(df[col].mode()[0] if not df[col].mode().empty else "Unknown")
        
        # Update session
        data['df'] = df
        
        return JSONResponse({
            'status': 'success',
            'rows_before': rows_before,
            'rows_after': len(df),
            'preview': json.loads(df.head(100).to_json(orient='records', date_format='iso', default_handler=str))
        })

    except Exception as e:
        return JSONResponse({'error': str(e)}, 500)

@app.post('/auto_prep_ml')
async def auto_prep_ml(session_id: str = Form(...), target_col: str = Form(None)):
    try:
        data = get_from_session(session_id)
        if not data: return JSONResponse({'error': 'Session expired'}, 404)
        
        df = data['df'].copy()
        
        # Basic Auto-Prep Pipeline
        # Fill missing numeric with median
        num_cols = df.select_dtypes(include=np.number).columns
        df[num_cols] = df[num_cols].fillna(df[num_cols].median())
        
        # Fill missing cat with 'Missing'
        cat_cols = df.select_dtypes(include='object').columns
        df[cat_cols] = df[cat_cols].fillna('Missing')
        
        # One-Hot Encode (limit cardinality)
        if len(df) < 100000: # Only for smaller datasets in this demo
            df = pd.get_dummies(df, columns=[c for c in cat_cols if df[c].nunique() < 20], dummy_na=True)
            
        buffer = io.StringIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)
        
        return Response(content=buffer.getvalue(), media_type="text/csv", 
                       headers={"Content-Disposition": f"attachment; filename=ml_ready_data.csv"})

    except Exception as e:
        logging.exception("Auto Prep failed")
        return JSONResponse({'error': f"Auto-Prep failed: {str(e)}"}, 500)

@app.get('/download/{session_id}')
async def download_current_data_get(session_id: str):
    return await download_current_data(session_id)

@app.post('/download')
async def download_current_data(session_id: str = Form(...)):
    """General purpose endpoint to download the current session's dataset (Streaming)"""
    try:
        data = get_from_session(session_id)
        if not data: return JSONResponse({'error': 'Session expired'}, 404)
        
        df = data['df']
        filename = data.get('filename', 'dataset.csv')
        if not filename.endswith('.csv'): filename += '.csv'

        # Streaming response for large files
        def iter_csv():
            buffer = io.StringIO()
            # Header
            df.head(0).to_csv(buffer, index=False)
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)
            
            # Chunks
            chunk_size = 10000
            for i in range(0, len(df), chunk_size):
                df.iloc[i:i+chunk_size].to_csv(buffer, index=False, header=False)
                yield buffer.getvalue()
                buffer.seek(0)
                buffer.truncate(0)

        from fastapi.responses import StreamingResponse
        return StreamingResponse(
            iter_csv(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        logging.exception("Download failed")
        return JSONResponse({'error': f"Download failed: {str(e)}"}, 500)

@app.post('/generate_report')
async def generate_report(session_id: str = Form(...)):
    try:
        data = get_from_session(session_id)
        if not data: return JSONResponse({'error': 'Session expired'}, 404)
        
        df = data['df']
        
        # Generate simple HTML report
        stats_html = df.describe().to_html(classes="table")
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: 'Helvetica', sans-serif; padding: 40px; color: #333; }}
                h1 {{ color: #4F46E5; border-bottom: 2px solid #4F46E5; padding-bottom: 10px; }}
                h2 {{ margin-top: 30px; color: #1e293b; }}
                .table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                .table th, .table td {{ padding: 8px; border: 1px solid #ddd; text-align: right; }}
                .table th {{ background-color: #f8fafc; }}
                .summary-box {{ background: #f1f5f9; padding: 20px; border-radius: 8px; margin-bottom: 30px; }}
            </style>
        </head>
        <body>
            <h1>Data Analysis Report</h1>
            <div class="summary-box">
                <p><strong>Filename:</strong> {data['filename']}</p>
                <p><strong>Total Rows:</strong> {len(df)}</p>
                <p><strong>Total Columns:</strong> {len(df.columns)}</p>
                <p><strong>Generated:</strong> {pd.Timestamp.now()}</p>
            </div>
            
            <h2>Statistical Summary</h2>
            {stats_html}
            
            <h2>Data Structure</h2>
            <ul>
                {''.join(f"<li><strong>{c}</strong>: {t}</li>" for c, t in df.dtypes.items())}
            </ul>
        </body>
        </html>
        """
        
        if WEASYPRINT_AVAILABLE:
            pdf_io = io.BytesIO()
            HTML(string=html).write_pdf(pdf_io)
            pdf_io.seek(0)
            return Response(content=pdf_io.getvalue(), media_type="application/pdf", 
                           headers={"Content-Disposition": "attachment; filename=report.pdf"})
        else:
            return Response(content=html, media_type="text/html", 
                           headers={"Content-Disposition": "attachment; filename=report.html"})

    except Exception as e:
        logging.exception("Report Generation Failed")
        return JSONResponse({'error': str(e)}, 500)

# --- Entry Point ---

if __name__ == '__main__':
    import socket
    
    def open_browser(port):
        """Open browser after a short delay"""
        time.sleep(1.5)
        webbrowser.open(f'http://localhost:{port}')
    
    base_port = 8085
    max_tries = 20
    
    for offset in range(max_tries):
        target_port = base_port + offset
        try:
            # Create a socket to test if we can BIND to it (not just connect)
            # This is more reliable on Windows
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('0.0.0.0', target_port))
                
            # If bind succeeded, start the actual server
            threading.Thread(target=open_browser, args=(target_port,), daemon=True).start()
            print(f"🚀 DataLyze Pro starting at http://localhost:{target_port}")
            
            uvicorn.run(app, host='0.0.0.0', port=target_port, log_level="info")
            break # Exit if successful
            
        except OSError as e:
            if e.errno == 10048: # Address already in use
                print(f"⚠️ Port {target_port} is busy, trying {target_port + 1}...")
                continue
            else:
                logging.exception("Fatal socket error")
                print(f"❌ Error binding to port {target_port}: {e}")
                break
        except Exception as e:
            logging.exception("Fatal startup error")
            print(f"❌ Startup failed: {e}")
            break
