"""
Integration Tests for import_stock_prices.py

Domain Driven Design (DDD) Test Pyramid - Integration Level
Tests interactions between components (file I/O, database, pandas)
"""

import pytest
import pandas as pd
import sqlite3
from pathlib import Path
import tempfile
import os
from unittest.mock import patch

from src.utils.import_stock_prices import main, upsert_stock_prices


class TestImportStockPricesIntegration:
    """Integration tests for import_stock_prices module"""
    
    def test_end_to_end_file_import(self):
        """Test complete flow: read CSV file, parse, insert into database"""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test CSV file
            csv_file = Path(tmpdir) / "AAPL.txt"
            df = pd.DataFrame({
                'Date': ['2024-01-01', '2024-01-02'],
                'Open': [100.0, 102.0],
                'High': [105.0, 107.0],
                'Low': [95.0, 97.0],
                'Close': [102.0, 104.0],
                'Volume': [1000000, 1100000]
            })
            df.to_csv(csv_file, index=False)
            
            # Create database
            db_file = Path(tmpdir) / "test.db"
            conn = sqlite3.connect(str(db_file))
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stock_prices (
                    symbol TEXT,
                    date TEXT,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume REAL,
                    adj_close REAL,
                    PRIMARY KEY (symbol, date)
                )
            """)
            conn.commit()
            
            # Read and process
            df_read = pd.read_csv(csv_file)
            df_read['Date'] = pd.to_datetime(df_read['Date']).dt.strftime('%Y-%m-%d')
            
            # Act
            upsert_stock_prices(df_read, 'AAPL', conn)
            conn.commit()
            
            # Assert
            result = conn.execute("SELECT COUNT(*) FROM stock_prices WHERE symbol = 'AAPL'").fetchone()
            assert result[0] == 2
            
            conn.close()
    
    def test_date_formatting_conversion(self):
        """Test that date formatting works correctly through the pipeline"""
        # Arrange
        with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as tmp:
            db_path = tmp.name
        
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS stock_prices (
                symbol TEXT,
                date TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                adj_close REAL,
                PRIMARY KEY (symbol, date)
            )
        """)
        conn.commit()
        
        # Test various date formats
        df = pd.DataFrame({
            'Date': pd.to_datetime(['2024-01-01', '2024-01-02']),
            'Open': [100.0, 102.0],
            'High': [105.0, 107.0],
            'Low': [95.0, 97.0],
            'Close': [102.0, 104.0],
            'Volume': [1000000, 1100000]
        })
        
        # Format dates
        df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
        
        # Act
        upsert_stock_prices(df, 'AAPL', conn)
        conn.commit()
        
        # Assert
        result = conn.execute("SELECT date FROM stock_prices WHERE symbol = 'AAPL'").fetchall()
        assert all(row[0] == '2024-01-01' or row[0] == '2024-01-02' for row in result)
        assert all(len(row[0]) == 10 for row in result)  # YYYY-MM-DD format
        
        conn.close()
        os.unlink(db_path)
    
    def test_multiple_symbols_import(self):
        """Test importing multiple symbols from different files"""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create multiple CSV files
            symbols = ['AAPL', 'MSFT', 'GOOGL']
            for symbol in symbols:
                csv_file = Path(tmpdir) / f"{symbol}.txt"
                df = pd.DataFrame({
                    'Date': ['2024-01-01'],
                    'Open': [100.0],
                    'High': [105.0],
                    'Low': [95.0],
                    'Close': [102.0],
                    'Volume': [1000000]
                })
                df.to_csv(csv_file, index=False)
            
            # Create database
            db_file = Path(tmpdir) / "test.db"
            conn = sqlite3.connect(str(db_file))
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stock_prices (
                    symbol TEXT,
                    date TEXT,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume REAL,
                    adj_close REAL,
                    PRIMARY KEY (symbol, date)
                )
            """)
            conn.commit()
            
            # Act - import each symbol
            for symbol in symbols:
                csv_file = Path(tmpdir) / f"{symbol}.txt"
                df = pd.read_csv(csv_file)
                df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
                upsert_stock_prices(df, symbol, conn)
            conn.commit()
            
            # Assert
            for symbol in symbols:
                result = conn.execute(
                    "SELECT COUNT(*) FROM stock_prices WHERE symbol = ?", (symbol,)
                ).fetchone()
                assert result[0] == 1
            
            conn.close()
    
    def test_duplicate_data_handling(self):
        """Test that duplicate data (same symbol, same date) is handled correctly"""
        # Arrange
        with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as tmp:
            db_path = tmp.name
        
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS stock_prices (
                symbol TEXT,
                date TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                adj_close REAL,
                PRIMARY KEY (symbol, date)
            )
        """)
        conn.commit()
        
        # First insert
        df1 = pd.DataFrame({
            'Date': ['2024-01-01'],
            'Open': [100.0],
            'High': [105.0],
            'Low': [95.0],
            'Close': [102.0],
            'Volume': [1000000]
        })
        df1['Date'] = pd.to_datetime(df1['Date']).dt.strftime('%Y-%m-%d')
        upsert_stock_prices(df1, 'AAPL', conn)
        conn.commit()
        
        # Second insert with same date but different values
        df2 = pd.DataFrame({
            'Date': ['2024-01-01'],
            'Open': [110.0],
            'High': [115.0],
            'Low': [105.0],
            'Close': [112.0],
            'Volume': [2000000]
        })
        df2['Date'] = pd.to_datetime(df2['Date']).dt.strftime('%Y-%m-%d')
        
        # Act
        upsert_stock_prices(df2, 'AAPL', conn)
        conn.commit()
        
        # Assert - should have only one record, updated with new values
        count = conn.execute("SELECT COUNT(*) FROM stock_prices WHERE symbol = 'AAPL'").fetchone()[0]
        assert count == 1
        
        result = conn.execute("SELECT * FROM stock_prices WHERE symbol = 'AAPL'").fetchone()
        assert result[2] == 110.0  # open updated
        assert result[6] == 2000000  # volume updated
        
        conn.close()
        os.unlink(db_path)

