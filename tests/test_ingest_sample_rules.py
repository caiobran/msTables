import pytest
from src.utils.ingest_sample_rules import ingest_sample_rules
import pandas as pd
import sqlite3
from pathlib import Path

class TestIngestSampleRules:
    def test_ingest_sample_rules_basic(self, sample_csv, temp_db):
        """Test basic ingestion functionality"""
        # Run ingestion
        ingest_sample_rules(sample_csv, temp_db)
        
        # Verify data was ingested
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM sample_rules")
            count = cursor.fetchone()[0]
            assert count == 2  # Two rows in sample CSV
            
            # Verify column names
            cursor = conn.execute("PRAGMA table_info(sample_rules)")
            columns = [row[1] for row in cursor.fetchall()]
            assert all(col in columns for col in [
                'avevol', 'yield', 'Dividend_Y10', 'Rev_Growth_Y9',
                'OpeInc_Growth_Y9', 'NetInc_Growth_Y9', 'PE_TTM',
                'PB_TTM', 'PS_TTM', 'PC_TTM'
            ])

    def test_ingest_sample_rules_missing_file(self, temp_db):
        """Test handling of missing input file"""
        with pytest.raises(FileNotFoundError):
            ingest_sample_rules('nonexistent.csv', temp_db)

    def test_ingest_sample_rules_missing_columns(self, tempfile, temp_db):
        """Test handling of missing required columns"""
        # Create CSV with missing columns
        df = pd.DataFrame({'date': ['2024-01-01'], 'other_col': [1]})
        df.to_csv(tempfile, index=False)
        
        with pytest.raises(ValueError):
            ingest_sample_rules(tempfile, temp_db)

    def test_ingest_sample_rules_duplicate_data(self, sample_csv, temp_db):
        """Test handling of duplicate data"""
        # First ingestion
        ingest_sample_rules(sample_csv, temp_db)
        
        # Second ingestion of same data
        ingest_sample_rules(sample_csv, temp_db)
        
        # Verify no duplicates
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM sample_rules")
            count = cursor.fetchone()[0]
            assert count == 2  # Should still be 2 rows

    def test_ingest_sample_rules_data_types(self, sample_csv, temp_db):
        """Test data type preservation"""
        ingest_sample_rules(sample_csv, temp_db)
        
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.execute("PRAGMA table_info(sample_rules)")
            columns = {row[1]: row[2] for row in cursor.fetchall()}
            
            # Verify numeric columns
            numeric_cols = [
                'avevol', 'yield', 'Dividend_Y10', 'Rev_Growth_Y9',
                'OpeInc_Growth_Y9', 'NetInc_Growth_Y9', 'PE_TTM',
                'PB_TTM', 'PS_TTM', 'PC_TTM'
            ]
            for col in numeric_cols:
                assert columns[col] == 'REAL'

    def test_ingest_sample_rules_null_handling(self, tempfile, temp_db):
        """Test handling of null values"""
        # Create CSV with null values
        df = pd.DataFrame({
            'date': ['2024-01-01'],
            'avevol': [None],
            'yield': [0.05],
            'Dividend_Y10': [1.0],
            'Rev_Growth_Y9': [0.1],
            'OpeInc_Growth_Y9': [0.15],
            'NetInc_Growth_Y9': [0.12],
            'PE_TTM': [20.0],
            'PB_TTM': [2.0],
            'PS_TTM': [3.0],
            'PC_TTM': [4.0]
        })
        df.to_csv(tempfile, index=False)
        
        ingest_sample_rules(tempfile, temp_db)
        
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.execute("SELECT avevol FROM sample_rules")
            value = cursor.fetchone()[0]
            assert value == 0  # Null should be converted to 0 