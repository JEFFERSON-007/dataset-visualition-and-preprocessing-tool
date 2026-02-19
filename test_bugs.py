"""
Bug Detection Test Suite
Tests critical functionality and edge cases
"""

import requests
import io
import pandas as pd

BASE_URL = "http://localhost:8081"

def test_file_upload_validation():
    """Test file upload with invalid files"""
    print("Testing file upload validation...")
    
    # Test 1: Empty file
    files = {'file': ('empty.csv', io.BytesIO(b''), 'text/csv')}
    response = requests.post(f"{BASE_URL}/upload", files=files)
    print(f"  Empty file: {response.status_code} - {response.json().get('error', 'OK')}")
    
    # Test 2: Unsupported format
    files = {'file': ('test.pdf', io.BytesIO(b'fake pdf'), 'application/pdf')}
    response = requests.post(f"{BASE_URL}/upload", files=files)
    print(f"  Unsupported format: {response.status_code} - {response.json().get('error', 'OK')}")
    
    # Test 3: Malformed CSV
    malformed_csv = b"col1,col2\nval1\nval2,val3,val4"
    files = {'file': ('malformed.csv', io.BytesIO(malformed_csv), 'text/csv')}
    response = requests.post(f"{BASE_URL}/upload", files=files)
    print(f"  Malformed CSV: {response.status_code}")
    
    # Test 4: Valid small CSV
    valid_csv = b"name,age,city\nAlice,25,NYC\nBob,30,LA\nCharlie,35,Chicago"
    files = {'file': ('valid.csv', io.BytesIO(valid_csv), 'text/csv')}
    response = requests.post(f"{BASE_URL}/upload", files=files)
    print(f"  Valid CSV: {response.status_code} - Success: {response.json().get('status') == 'success'}")

def test_download_formats():
    """Test all download formats"""
    print("\nTesting download formats...")
    
    # First upload a file and preprocess it
    csv_data = b"name,age,salary\nAlice,25,50000\nBob,30,60000\nCharlie,35,70000"
    files = {'file': ('test.csv', io.BytesIO(csv_data), 'text/csv')}
    data = {'remove_duplicates': 'false', 'impute_missing': 'false', 'drop_constant': 'false'}
    
    response = requests.post(f"{BASE_URL}/preprocess", files=files, data=data)
    if response.status_code == 200:
        download_id = response.json().get('download_id')
        
        # Test each format
        for fmt in ['csv', 'xlsx', 'json', 'parquet']:
            dl_response = requests.get(f"{BASE_URL}/download/{download_id}?format={fmt}")
            print(f"  Format {fmt}: {dl_response.status_code} - Size: {len(dl_response.content)} bytes")
        
        # Test invalid format
        dl_response = requests.get(f"{BASE_URL}/download/{download_id}?format=invalid")
        print(f"  Invalid format: {dl_response.status_code} - {dl_response.json().get('error', 'OK')}")
    else:
        print(f"  Failed to preprocess: {response.status_code}")

def test_correlation_matrix():
    """Test correlation matrix endpoint"""
    print("\nTesting correlation matrix...")
    
    # Test with numeric data
    csv_data = b"age,salary,score\n25,50000,85\n30,60000,90\n35,70000,95\n40,80000,88"
    files = {'file': ('numeric.csv', io.BytesIO(csv_data), 'text/csv')}
    response = requests.post(f"{BASE_URL}/correlation_matrix", files=files)
    print(f"  Numeric data: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"    Columns: {data.get('columns')}")
        print(f"    Strong pairs: {len(data.get('pairs', []))}")
    
    # Test with insufficient numeric columns
    csv_data = b"name,age\nAlice,25\nBob,30"
    files = {'file': ('insufficient.csv', io.BytesIO(csv_data), 'text/csv')}
    response = requests.post(f"{BASE_URL}/correlation_matrix", files=files)
    print(f"  Insufficient numeric cols: {response.status_code} - {response.json().get('error', 'OK')}")

def test_advanced_preprocessing():
    """Test advanced preprocessing options"""
    print("\nTesting advanced preprocessing...")
    
    csv_data = b"name,age,salary,city,date\nAlice,25,50000,NYC,2023-01-01\nBob,30,60000,LA,2023-02-01\nCharlie,35,70000,Chicago,2023-03-01\nDave,100,1000000,NYC,2023-04-01"
    
    # Test normalization
    files = {'file': ('test.csv', io.BytesIO(csv_data), 'text/csv')}
    data = {'normalize': 'true', 'standardize': 'false', 'one_hot_encode': 'false', 
            'handle_outliers': 'none', 'create_date_features': 'false'}
    response = requests.post(f"{BASE_URL}/advanced_preprocess", files=files, data=data)
    print(f"  Normalization: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"    Changes: {result.get('changes')}")
    
    # Test outlier removal
    files = {'file': ('test.csv', io.BytesIO(csv_data), 'text/csv')}
    data = {'normalize': 'false', 'standardize': 'false', 'one_hot_encode': 'false', 
            'handle_outliers': 'remove', 'create_date_features': 'false'}
    response = requests.post(f"{BASE_URL}/advanced_preprocess", files=files, data=data)
    print(f"  Outlier removal: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"    Rows: {result.get('original_rows')} -> {result.get('processed_rows')}")

def test_column_info():
    """Test column info endpoint"""
    print("\nTesting column info...")
    
    csv_data = b"name,age,salary,active\nAlice,25,50000,true\nBob,30,60000,false\nCharlie,35,,true"
    files = {'file': ('test.csv', io.BytesIO(csv_data), 'text/csv')}
    response = requests.post(f"{BASE_URL}/column_info", files=files)
    print(f"  Column info: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"    Total columns: {data.get('total_columns')}")
        print(f"    Types: {data.get('types_summary')}")
        for col in data.get('columns', [])[:2]:
            print(f"    - {col['name']}: {col['type']}, missing: {col['missing_pct']}%")

def test_report_generation():
    """Test report generation"""
    print("\nTesting report generation...")
    
    csv_data = b"name,age,salary\nAlice,25,50000\nBob,30,60000\nCharlie,35,70000"
    files = {'file': ('test.csv', io.BytesIO(csv_data), 'text/csv')}
    response = requests.post(f"{BASE_URL}/generate_report", files=files)
    print(f"  Report generation: {response.status_code} - Size: {len(response.content)} bytes")
    print(f"  Content-Type: {response.headers.get('Content-Type')}")

if __name__ == "__main__":
    print("=" * 60)
    print("DATASET VISUALIZATION - BUG DETECTION TEST SUITE")
    print("=" * 60)
    
    try:
        test_file_upload_validation()
        test_download_formats()
        test_correlation_matrix()
        test_advanced_preprocessing()
        test_column_info()
        test_report_generation()
        
        print("\n" + "=" * 60)
        print("ALL TESTS COMPLETED")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ TEST SUITE ERROR: {e}")
        import traceback
        traceback.print_exc()
