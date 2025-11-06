"""
End-to-End Tests for import_stock_prices.py

Domain Driven Design (DDD) Test Pyramid - E2E Level
Tests complete user workflows and system behavior
"""

import pytest
import pandas as pd
import sqlite3
from pathlib import Path
import tempfile
import os
from unittest.mock import patch, MagicMock

from src.utils.import_stock_prices import main


class TestImportStockPricesE2E:
    """End-to-end tests for import_stock_prices module"""
    
    @patch('src.utils.import_stock_prices.STOCK_FOLDER')
    @patch('src.utils.import_stock_prices.DB_PATH')
    def test_main_function_complete_workflow(self, mock_db_path, mock_stock_folder):
        """Test the main() function completes full workflow"""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create mock stock folder with files
            stock_folder = Path(tmpdir) / "stocks"
            stock_folder.mkdir()
            
            # Create test files
            symbols = ['AAPL', 'MSFT']
            for symbol in symbols:
                csv_file = stock_folder / f"{symbol}.txt"
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
            
            # Mock the constants
            mock_stock_folder.__str__ = lambda x: str(stock_folder)
            mock_db_path.__str__ = lambda x: str(db_file)
            
            # Patch the actual module constants
            import src.utils.import_stock_prices as import_module
            original_stock_folder = import_module.STOCK_FOLDER
            original_db_path = import_module.DB_PATH
            
            import_module.STOCK_FOLDER = str(stock_folder)
            import_module.DB_PATH = str(db_file)
            
            try:
                # Act
                main()
                
                # Assert
                conn = sqlite3.connect(str(db_file))
                for symbol in symbols:
                    count = conn.execute(
                        "SELECT COUNT(*) FROM stock_prices WHERE symbol = ?", (symbol,)
                    ).fetchone()[0]
                    assert count == 2
                conn.close()
            finally:
                # Restore original values
                import_module.STOCK_FOLDER = original_stock_folder
                import_module.DB_PATH = original_db_path
    
    def test_main_handles_missing_files_gracefully(self):
        """Test that main() handles missing or invalid files without crashing"""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            stock_folder = Path(tmpdir) / "stocks"
            stock_folder.mkdir()
            
            # Create one valid file and one invalid file
            valid_file = stock_folder / "AAPL.txt"
            df = pd.DataFrame({
                'Date': ['2024-01-01'],
                'Open': [100.0],
                'High': [105.0],
                'Low': [95.0],
                'Close': [102.0],
                'Volume': [1000000]
            })
            df.to_csv(valid_file, index=False)
            
            # Create invalid file (missing columns)
            invalid_file = stock_folder / "INVALID.txt"
            invalid_file.write_text("invalid,data\n1,2")
            
            db_file = Path(tmpdir) / "test.db"
            
            # Patch constants
            import src.utils.import_stock_prices as import_module
            original_stock_folder = import_module.STOCK_FOLDER
            original_db_path = import_module.DB_PATH
            
            import_module.STOCK_FOLDER = str(stock_folder)
            import_module.DB_PATH = str(db_file)
            
            try:
                # Act - should not crash
                main()
                
                # Assert - valid file should be processed
                conn = sqlite3.connect(str(db_file))
                count = conn.execute(
                    "SELECT COUNT(*) FROM stock_prices WHERE symbol = 'AAPL'"
                ).fetchone()[0]
                assert count == 1
                conn.close()
            finally:
                import_module.STOCK_FOLDER = original_stock_folder
                import_module.DB_PATH = original_db_path
    
    def test_main_creates_table_if_not_exists(self):
        """Test that main() creates stock_prices table if it doesn't exist"""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            stock_folder = Path(tmpdir) / "stocks"
            stock_folder.mkdir()
            
            csv_file = stock_folder / "AAPL.txt"
            df = pd.DataFrame({
                'Date': ['2024-01-01'],
                'Open': [100.0],
                'High': [105.0],
                'Low': [95.0],
                'Close': [102.0],
                'Volume': [1000000]
            })
            df.to_csv(csv_file, index=False)
            
            db_file = Path(tmpdir) / "test.db"
            
            # Patch constants
            import src.utils.import_stock_prices as import_module
            original_stock_folder = import_module.STOCK_FOLDER
            original_db_path = import_module.DB_PATH
            
            import_module.STOCK_FOLDER = str(stock_folder)
            import_module.DB_PATH = str(db_file)
            
            try:
                # Act
                main()
                
                # Assert - table should exist
                conn = sqlite3.connect(str(db_file))
                cursor = conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='stock_prices'
                """)
                assert cursor.fetchone() is not None
                
                # Verify schema
                cursor = conn.execute("PRAGMA table_info(stock_prices)")
                columns = [row[1] for row in cursor.fetchall()]
                expected_columns = ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume', 'adj_close']
                assert all(col in columns for col in expected_columns)
                
                conn.close()
            finally:
                import_module.STOCK_FOLDER = original_stock_folder
                import_module.DB_PATH = original_db_path

