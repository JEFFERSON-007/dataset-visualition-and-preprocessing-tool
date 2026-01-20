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
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import pandas as pd
import numpy as np
import io
import json
from typing import List, Dict, Any
import tempfile
import os
import uuid
from typing import Optional

app = FastAPI(title="Generic EDA Web Tool — Premium")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Store for cleaned datasets (in-memory for simple demo, use Redis/DB for prod)
cleaned_datasets_store = {}

# ---------- Helpers ----------

def safe_read_csv(s: str, sep=',', nrows=None):
    try:
        return pd.read_csv(io.StringIO(s), nrows=nrows)
    except Exception:
        # try with python engine
        return pd.read_csv(io.StringIO(s), engine='python', sep=sep, nrows=nrows)


def parse_uploaded_file(contents: bytes, filename: str, sample_rows: int = 5000):
    """Return a dict of {name: DataFrame} — for single-sheet returns {'sheet1': df}
    Tries to handle csv, tsv, xlsx, json (ndjson or json array), parquet.
    """
    name = filename.lower()
    tmp = None
    try:
        if name.endswith('.csv') or name.endswith('.txt'):
            s = None
            try:
                s = contents.decode('utf-8')
            except UnicodeDecodeError:
                s = contents.decode('latin1', errors='ignore')
            df = safe_read_csv(s, sep=',', nrows=sample_rows)
            return {os.path.splitext(filename)[0]: df}

        elif name.endswith('.tsv') or '\t' in contents.decode('utf-8', errors='ignore')[:200]:
            s = contents.decode('utf-8', errors='ignore')
            df = safe_read_csv(s, sep='\t', nrows=sample_rows)
            return {os.path.splitext(filename)[0]: df}

        elif name.endswith('.xlsx') or name.endswith('.xls'):
            # write to temp file and use pandas.read_excel with sheet_name=None
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1])
            tmp.write(contents); tmp.close()
            sheets = pd.read_excel(tmp.name, sheet_name=None)
            # limit rows per sheet for safety
            sheets = {k: v.head(sample_rows) for k,v in sheets.items()}
            return sheets

        elif name.endswith('.json'):
            # try ndjson first
            s = None
            try:
                s = contents.decode('utf-8')
            except Exception:
                s = contents.decode('latin1', errors='ignore')
            lines = [l for l in s.splitlines() if l.strip()]
            if len(lines) > 1 and all(l.strip().startswith('{') for l in lines[:5]):
                # ndjson
                records = [json.loads(l) for l in lines[:sample_rows]]
                df = pd.json_normalize(records)
                return {os.path.splitext(filename)[0]: df}
            else:
                # try full json array
                try:
                    obj = json.loads(s)
                    if isinstance(obj, list):
                        df = pd.json_normalize(obj[:sample_rows])
                        return {os.path.splitext(filename)[0]: df}
                    elif isinstance(obj, dict):
                        # single object -> flatten
                        df = pd.json_normalize([obj])
                        return {os.path.splitext(filename)[0]: df}
                except Exception:
                    pass
                # fallback to csv parse
                df = safe_read_csv(s, sep=',', nrows=sample_rows)
                return {os.path.splitext(filename)[0]: df}

        elif name.endswith('.parquet'):
            try:
                # pandas will use pyarrow/fastparquet
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.parquet')
                tmp.write(contents); tmp.close()
                df = pd.read_parquet(tmp.name)
                return {os.path.splitext(filename)[0]: df.head(sample_rows)}
            except Exception:
                # try reading with duckdb from buffer
                raise

        else:
            # unknown extension — attempt csv then json
            try:
                s = contents.decode('utf-8')
            except Exception:
                s = contents.decode('latin1', errors='ignore')
            # try csv
            try:
                df = safe_read_csv(s, sep=',', nrows=sample_rows)
                return {os.path.splitext(filename)[0]: df}
            except Exception:
                try:
                    obj = json.loads(s)
                    if isinstance(obj, list):
                        df = pd.json_normalize(obj[:sample_rows])
                        return {os.path.splitext(filename)[0]: df}
                except Exception:
                    pass
            raise ValueError('Unsupported file or failed to parse')
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
            parsed = pd.to_datetime(s.sample(min(len(s), min(100, len(s)))), errors='coerce')
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
                s = pd.to_datetime(non_null, errors='coerce').dropna()
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
    if not file.filename:
        return JSONResponse({'error':'no file provided'}, status_code=400)
    contents = await file.read()
    try:
        sheets = parse_uploaded_file(contents, file.filename, sample_rows=sample_rows)
    except Exception as e:
        return JSONResponse({'error': f'Failed to parse file: {str(e)}'}, status_code=400)

    # For multi-sheet files, pick first sheet as primary
    primary_name = list(sheets.keys())[0]
    df = sheets[primary_name].copy()
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
        coerced = pd.to_datetime(df[col], errors='coerce')
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
        'total_rows': int(len(df)),
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
async def download_clean(download_id: str):
    if download_id not in cleaned_datasets_store:
        return JSONResponse({'error': 'File not found or expired'}, status_code=404)
        
    data = cleaned_datasets_store[download_id]
    df = data['df']
    orig_name = data['filename']
    
    # Export to CSV
    stream = io.StringIO()
    df.to_csv(stream, index=False)
    
    response = HTMLResponse(content=stream.getvalue(), media_type="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename={orig_name}"
    return response

if __name__ == '__main__':
    print('Starting enhanced EDA server on http://localhost:8081')
    uvicorn.run('app:app', host='0.0.0.0', port=8081, reload=False)
