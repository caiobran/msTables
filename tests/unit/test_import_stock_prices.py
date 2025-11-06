"""
Unit Tests for import_stock_prices.py

Domain Driven Design (DDD) Test Pyramid - Unit Level
Tests individual functions and methods in isolation
"""

import pytest
import pandas as pd
import sqlite3
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os

from src.utils.import_stock_prices import upsert_stock_prices


class TestUpsertStockPrices:
    """Unit tests for upsert_stock_prices function"""
    
    def test_upsert_stock_prices_inserts_new_record(self):
        """Test that upsert_stock_prices inserts a new record when none exists"""
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
        
        df = pd.DataFrame({
            'Date': ['2024-01-01'],
            'Open': [100.0],
            'High': [105.0],
            'Low': [95.0],
            'Close': [102.0],
            'Volume': [1000000]
        })
        
        # Act
        upsert_stock_prices(df, 'AAPL', conn)
        conn.commit()
        
        # Assert
        result = conn.execute("SELECT * FROM stock_prices WHERE symbol = 'AAPL'").fetchone()
        assert result is not None
        assert result[0] == 'AAPL'  # symbol
        assert result[1] == '2024-01-01'  # date
        assert result[2] == 100.0  # open
        assert result[3] == 105.0  # high
        assert result[4] == 95.0  # low
        assert result[5] == 102.0  # close
        assert result[6] == 1000000  # volume
        assert result[7] == 102.0  # adj_close (should be same as close)
        
        conn.close()
        os.unlink(db_path)
    
    def test_upsert_stock_prices_updates_existing_record(self):
        """Test that upsert_stock_prices updates an existing record"""
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
        conn.execute("""
            INSERT INTO stock_prices (symbol, date, open, high, low, close, volume, adj_close)
            VALUES ('AAPL', '2024-01-01', 100.0, 105.0, 95.0, 102.0, 1000000, 102.0)
        """)
        conn.commit()
        
        df = pd.DataFrame({
            'Date': ['2024-01-01'],
            'Open': [110.0],
            'High': [115.0],
            'Low': [105.0],
            'Close': [112.0],
            'Volume': [2000000]
        })
        
        # Act
        upsert_stock_prices(df, 'AAPL', conn)
        conn.commit()
        
        # Assert
        result = conn.execute("SELECT * FROM stock_prices WHERE symbol = 'AAPL' AND date = '2024-01-01'").fetchone()
        assert result[2] == 110.0  # open updated
        assert result[3] == 115.0  # high updated
        assert result[5] == 112.0  # close updated
        assert result[6] == 2000000  # volume updated
        
        conn.close()
        os.unlink(db_path)
    
    def test_upsert_stock_prices_handles_multiple_rows(self):
        """Test that upsert_stock_prices handles multiple rows in DataFrame"""
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
        
        df = pd.DataFrame({
            'Date': ['2024-01-01', '2024-01-02', '2024-01-03'],
            'Open': [100.0, 102.0, 104.0],
            'High': [105.0, 107.0, 109.0],
            'Low': [95.0, 97.0, 99.0],
            'Close': [102.0, 104.0, 106.0],
            'Volume': [1000000, 1100000, 1200000]
        })
        
        # Act
        upsert_stock_prices(df, 'AAPL', conn)
        conn.commit()
        
        # Assert
        results = conn.execute("SELECT COUNT(*) FROM stock_prices WHERE symbol = 'AAPL'").fetchone()
        assert results[0] == 3
        
        conn.close()
        os.unlink(db_path)
    
    def test_upsert_stock_prices_handles_missing_columns_gracefully(self):
        """Test that upsert_stock_prices handles missing columns without crashing"""
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
        
        # Missing some columns
        df = pd.DataFrame({
            'Date': ['2024-01-01'],
            'Open': [100.0],
            'Close': [102.0]
            # Missing High, Low, Volume
        })
        
        # Act & Assert - should raise KeyError or handle gracefully
        with pytest.raises((KeyError, ValueError)):
            upsert_stock_prices(df, 'AAPL', conn)
        
        conn.close()
        os.unlink(db_path)
    
    @patch('src.utils.import_stock_prices.logging')
    def test_upsert_stock_prices_logs_errors(self, mock_logging):
        """Test that upsert_stock_prices logs errors appropriately"""
        # Arrange
        with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as tmp:
            db_path = tmp.name
        
        conn = sqlite3.connect(db_path)
        # Create table with wrong schema to cause error
        conn.execute("""
            CREATE TABLE IF NOT EXISTS stock_prices (
                symbol TEXT,
                date TEXT
            )
        """)
        conn.commit()
        
        df = pd.DataFrame({
            'Date': ['2024-01-01'],
            'Open': [100.0],
            'High': [105.0],
            'Low': [95.0],
            'Close': [102.0],
            'Volume': [1000000]
        })
        
        # Act
        upsert_stock_prices(df, 'AAPL', conn)
        
        # Assert - error should be logged
        mock_logging.error.assert_called()
        
        conn.close()
        os.unlink(db_path)

