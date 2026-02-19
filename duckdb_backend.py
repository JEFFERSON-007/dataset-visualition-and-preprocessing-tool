"""
DuckDB Backend for Multi-GB Dataset Processing

Provides efficient SQL-based analytics for large datasets using DuckDB.
Supports zero-copy reads from Parquet and fast CSV loading.
"""

import duckdb
import pandas as pd
from typing import Dict, Any, Optional
import os


class DuckDBBackend:
    """Efficient backend for multi-GB datasets using DuckDB"""
    
    def __init__(self, filepath: str):
        """Initialize DuckDB connection and store filepath"""
        self.conn = duckdb.connect(':memory:')
        self.filepath = filepath
        self.table_name = 'dataset'
        self.loaded = False
        
    def load_file(self) -> Dict[str, Any]:
        """
        Load file into DuckDB with zero-copy for Parquet
        Returns metadata about the loaded dataset
        """
        ext = os.path.splitext(self.filepath)[1].lower()
        
        try:
            if ext == '.parquet':
                # Zero-copy read for Parquet - extremely fast
                self.conn.execute(f"CREATE TABLE {self.table_name} AS SELECT * FROM '{self.filepath}'")
            elif ext in ['.csv', '.txt', '.tsv']:
                # Auto-detect CSV format
                self.conn.execute(f"CREATE TABLE {self.table_name} AS SELECT * FROM read_csv_auto('{self.filepath}')")
            else:
                raise ValueError(f"Unsupported file type for DuckDB: {ext}")
            
            self.loaded = True
            
            # Get basic metadata
            row_count = self.get_row_count()
            columns = self.get_columns()
            
            return {
                'success': True,
                'rows': row_count,
                'columns': columns,
                'backend': 'duckdb'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_sample(self, n: int = 50000, method: str = 'random') -> pd.DataFrame:
        """
        Get sample from dataset efficiently
        
        Args:
            n: Number of rows to sample
            method: 'random' for random sampling, 'first' for first N rows
        """
        if not self.loaded:
            raise RuntimeError("Dataset not loaded. Call load_file() first.")
        
        if method == 'random':
            # DuckDB's USING SAMPLE is extremely fast
            query = f"SELECT * FROM {self.table_name} USING SAMPLE {n} ROWS"
        else:
            query = f"SELECT * FROM {self.table_name} LIMIT {n}"
        
        return self.conn.execute(query).df()
    
    def get_stats(self) -> pd.DataFrame:
        """Get column statistics using SQL"""
        if not self.loaded:
            raise RuntimeError("Dataset not loaded. Call load_file() first.")
        
        # DuckDB's DESCRIBE is very efficient
        return self.conn.execute(f"DESCRIBE {self.table_name}").df()
    
    def get_row_count(self) -> int:
        """Fast row count using SQL"""
        if not self.loaded:
            raise RuntimeError("Dataset not loaded. Call load_file() first.")
        
        return self.conn.execute(f"SELECT COUNT(*) FROM {self.table_name}").fetchone()[0]
    
    def get_columns(self) -> list:
        """Get list of column names"""
        if not self.loaded:
            raise RuntimeError("Dataset not loaded. Call load_file() first.")
        
        result = self.conn.execute(f"PRAGMA table_info({self.table_name})").fetchall()
        return [row[1] for row in result]  # Column name is at index 1
    
    def get_column_stats(self, column: str) -> Dict[str, Any]:
        """Get detailed statistics for a specific column"""
        if not self.loaded:
            raise RuntimeError("Dataset not loaded. Call load_file() first.")
        
        query = f"""
        SELECT 
            COUNT(*) as count,
            COUNT(DISTINCT "{column}") as unique_count,
            COUNT("{column}") as non_null_count,
            MIN("{column}") as min_value,
            MAX("{column}") as max_value
        FROM {self.table_name}
        """
        
        result = self.conn.execute(query).fetchone()
        
        return {
            'count': result[0],
            'unique': result[1],
            'non_null': result[2],
            'missing': result[0] - result[2],
            'min': result[3],
            'max': result[4]
        }
    
    def execute_query(self, query: str) -> pd.DataFrame:
        """Execute arbitrary SQL query and return DataFrame"""
        if not self.loaded:
            raise RuntimeError("Dataset not loaded. Call load_file() first.")
        
        return self.conn.execute(query).df()
    
    def get_value_counts(self, column: str, limit: int = 20) -> pd.DataFrame:
        """Get value counts for a column (for categorical analysis)"""
        if not self.loaded:
            raise RuntimeError("Dataset not loaded. Call load_file() first.")
        
        query = f"""
        SELECT "{column}" as value, COUNT(*) as count
        FROM {self.table_name}
        GROUP BY "{column}"
        ORDER BY count DESC
        LIMIT {limit}
        """
        
        return self.conn.execute(query).df()
    
    def close(self):
        """Close DuckDB connection"""
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        """Context manager support"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup"""
        self.close()
