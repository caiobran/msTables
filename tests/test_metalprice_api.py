import pytest
from src.metalprice.metalprice_api import MetalPriceAPI
import pandas as pd
from pathlib import Path
import sqlite3
from unittest.mock import patch, MagicMock

class TestMetalPriceAPI:
    def test_init(self, temp_db):
        """Test MetalPriceAPI initialization"""
        api = MetalPriceAPI(db_path=temp_db)
        assert api.db_path == temp_db
        assert api.base_url == "https://api.metalpriceapi.com/v1/latest"
        assert api.api_key is not None

    def test_init_db(self, temp_db):
        """Test database initialization"""
        api = MetalPriceAPI(db_path=temp_db)
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='metal_prices'")
            assert cursor.fetchone() is not None

    @patch('requests.get')
    def test_fetch_metal_price(self, mock_get, temp_db):
        """Test metal price fetching"""
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "rates": {
                "XAU": 2000.0,
                "XAG": 25.0
            }
        }
        mock_get.return_value = mock_response

        api = MetalPriceAPI(db_path=temp_db)
        result = api.fetch_metal_price("XAU")
        
        assert result == 2000.0
        mock_get.assert_called_once()

    @patch('requests.get')
    def test_fetch_metal_price_error(self, mock_get, temp_db):
        """Test metal price fetching with error"""
        # Mock error API response
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "success": False,
            "error": "Invalid API key"
        }
        mock_get.return_value = mock_response

        api = MetalPriceAPI(db_path=temp_db)
        result = api.fetch_metal_price("XAU")
        
        assert result is None

    def test_save_metal_price(self, temp_db):
        """Test saving metal price to database"""
        api = MetalPriceAPI(db_path=temp_db)
        api.save_metal_price("XAU", 2000.0)
        
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.execute("SELECT price FROM metal_prices WHERE symbol = ?", ("XAU",))
            row = cursor.fetchone()
            assert row is not None
            assert row[0] == 2000.0

    def test_log_unavailable_symbol(self, temp_db):
        """Test logging unavailable symbols"""
        api = MetalPriceAPI(db_path=temp_db)
        api.log_unavailable_symbol("XAU", "API error")
        
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.execute("SELECT * FROM unavailable_symbols WHERE symbol = ?", ("XAU",))
            row = cursor.fetchone()
            assert row is not None
            assert row[1] == "XAU"  # symbol
            assert row[2] == "API error"  # reason

    @patch('src.metalprice.metalprice_api.MetalPriceAPI.fetch_metal_price')
    def test_fetch_and_save_all_metals(self, mock_fetch, temp_db):
        """Test fetching and saving all metals"""
        # Mock successful price fetching
        mock_fetch.return_value = 2000.0
        
        api = MetalPriceAPI(db_path=temp_db)
        api.fetch_and_save_all_metals()
        
        # Verify all metals were processed
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM metal_prices")
            count = cursor.fetchone()[0]
            assert count == len(api.metal_symbols)

    def test_get_latest_prices(self, temp_db):
        """Test getting latest prices"""
        api = MetalPriceAPI(db_path=temp_db)
        
        # Insert test data
        with sqlite3.connect(temp_db) as conn:
            conn.execute("""
                INSERT INTO metal_prices (symbol, price, timestamp)
                VALUES (?, ?, ?)
            """, ("XAU", 2000.0, "2024-01-01"))
            conn.execute("""
                INSERT INTO metal_prices (symbol, price, timestamp)
                VALUES (?, ?, ?)
            """, ("XAG", 25.0, "2024-01-01"))
        
        prices = api.get_latest_prices()
        assert "XAU" in prices
        assert "XAG" in prices
        assert prices["XAU"] == 2000.0
        assert prices["XAG"] == 25.0 