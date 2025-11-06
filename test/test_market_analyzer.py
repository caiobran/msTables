"""
Test suite for MarketAnalyzer class.
"""

import unittest
import pandas as pd
import numpy as np
import os
import sqlite3
from datetime import datetime, timedelta
from src.analysis.market_analyzer import MarketAnalyzer

class TestMarketAnalyzer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        # Create test database
        cls.db_path = 'test/test_market_data.db'
        os.makedirs('test', exist_ok=True)
        
        # Create test data
        cls.create_test_database()
        
        # Initialize analyzer
        cls.analyzer = MarketAnalyzer(cls.db_path)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment."""
        if os.path.exists(cls.db_path):
            os.remove(cls.db_path)
    
    @classmethod
    def create_test_database(cls):
        """Create test database with sample data."""
        conn = sqlite3.connect(cls.db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
        CREATE TABLE MSpricehistory (
            date TEXT,
            symbol TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER
        )
        ''')
        
        # Generate test data
        dates = pd.date_range(start='2020-01-01', end='2020-12-31', freq='D')
        symbols = ['^GSPC', 'GC=F', 'CL=F', 'SI=F']
        
        for symbol in symbols:
            for date in dates:
                cursor.execute('''
                INSERT INTO MSpricehistory VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    date.strftime('%Y-%m-%d'),
                    symbol,
                    np.random.normal(100, 10),
                    np.random.normal(105, 10),
                    np.random.normal(95, 10),
                    np.random.normal(100, 10),
                    np.random.randint(1000, 10000)
                ))
        
        conn.commit()
        conn.close()
    
    def test_calculate_rsi_gpu(self):
        """Test RSI calculation on GPU."""
        # Create test data
        prices = np.random.normal(100, 10, 100)
        prices_gpu = cp.array(prices)
        
        # Calculate RSI
        rsi = self.analyzer.calculate_rsi_gpu(prices_gpu)
        
        # Verify results
        self.assertIsNotNone(rsi)
        self.assertEqual(len(rsi), len(prices) - 1)
        self.assertTrue(np.all((rsi >= 0) & (rsi <= 100)))
    
    def test_calculate_macd_gpu(self):
        """Test MACD calculation on GPU."""
        # Create test data
        prices = np.random.normal(100, 10, 100)
        prices_gpu = cp.array(prices)
        
        # Calculate MACD
        macd_line, signal_line, histogram = self.analyzer.calculate_macd_gpu(prices_gpu)
        
        # Verify results
        self.assertIsNotNone(macd_line)
        self.assertIsNotNone(signal_line)
        self.assertIsNotNone(histogram)
        self.assertEqual(len(macd_line), len(prices) - 25)  # 26-period EMA
    
    def test_process_batch_gpu(self):
        """Test batch processing on GPU."""
        # Create test data
        data = pd.DataFrame({
            'close': np.random.normal(100, 10, 100),
            'volume': np.random.randint(1000, 10000, 100),
            'high': np.random.normal(105, 10, 100),
            'low': np.random.normal(95, 10, 100)
        })
        
        # Process batch
        result = self.analyzer.process_batch_gpu(data)
        
        # Verify results
        self.assertIsNotNone(result)
        self.assertIn('rsi', result.columns)
        self.assertIn('macd', result.columns)
        self.assertIn('volatility', result.columns)
    
    def test_add_regime_indicators(self):
        """Test regime indicator calculation."""
        # Create test data
        data = pd.DataFrame({
            'returns': np.random.normal(0, 1, 100),
            'close': np.random.normal(100, 10, 100)
        })
        
        # Add regime indicators
        result = self.analyzer.add_regime_indicators(data)
        
        # Verify results
        self.assertIsNotNone(result)
        self.assertIn('volatility_regime', result.columns)
        self.assertIn('trend_regime', result.columns)
        self.assertIn('commodity_correlation', result.columns)
    
    def test_calculate_commodity_correlation(self):
        """Test commodity correlation calculation."""
        # Create test data
        data = pd.DataFrame({
            'close': np.random.normal(100, 10, 100),
            'date': pd.date_range(start='2020-01-01', periods=100)
        })
        
        # Calculate correlations
        correlations = self.analyzer.calculate_commodity_correlation(data)
        
        # Verify results
        self.assertIsNotNone(correlations)
        self.assertEqual(len(correlations), len(data))
    
    def test_validate_data(self):
        """Test data validation."""
        # Create valid data
        valid_data = pd.DataFrame({
            'close': np.random.normal(100, 10, 100),
            'volume': np.random.randint(1000, 10000, 100)
        })
        
        # Create invalid data
        invalid_data = pd.DataFrame({
            'close': [np.nan, 100, np.inf],
            'volume': [1000, 'invalid', 2000]
        })
        
        # Test validation
        self.assertTrue(self.analyzer.validate_data(valid_data))
        self.assertFalse(self.analyzer.validate_data(invalid_data))
    
    def test_monitor_system_health(self):
        """Test system health monitoring."""
        # Monitor health
        self.analyzer.monitor_system_health()
        
        # Verify log file exists
        self.assertTrue(os.path.exists('data/logs/market_analyzer.log'))

if __name__ == '__main__':
    unittest.main() 