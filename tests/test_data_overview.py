import pytest
from src.data_overview import analyze_data
import pandas as pd
import sqlite3
from pathlib import Path
import matplotlib.pyplot as plt

class TestDataOverview:
    def test_analyze_data_basic(self, temp_db):
        """Test basic data analysis functionality"""
        # Create test data
        with sqlite3.connect(temp_db) as conn:
            df = pd.DataFrame({
                'date': ['2024-01-01', '2024-01-02'],
                'avevol': [1000, 2000],
                'yield': [0.05, 0.06],
                'Dividend_Y10': [1.0, 1.1],
                'Rev_Growth_Y9': [0.1, 0.2],
                'OpeInc_Growth_Y9': [0.15, 0.25],
                'NetInc_Growth_Y9': [0.12, 0.22],
                'PE_TTM': [20.0, 21.0],
                'PB_TTM': [2.0, 2.1],
                'PS_TTM': [3.0, 3.1],
                'PC_TTM': [4.0, 4.1]
            })
            df.to_sql('sample_rules', conn, index=False)
        
        # Run analysis
        analyze_data(temp_db)
        
        # Verify output files exist
        assert Path('data_overview.png').exists()
        assert Path('data_overview.txt').exists()

    def test_analyze_data_empty_db(self, temp_db):
        """Test analysis with empty database"""
        with pytest.raises(ValueError):
            analyze_data(temp_db)

    def test_analyze_data_missing_columns(self, temp_db):
        """Test analysis with missing required columns"""
        with sqlite3.connect(temp_db) as conn:
            df = pd.DataFrame({
                'date': ['2024-01-01'],
                'other_col': [1]
            })
            df.to_sql('sample_rules', conn, index=False)
        
        with pytest.raises(ValueError):
            analyze_data(temp_db)

    def test_analyze_data_statistics(self, temp_db):
        """Test statistical calculations"""
        # Create test data with known values
        with sqlite3.connect(temp_db) as conn:
            df = pd.DataFrame({
                'date': ['2024-01-01', '2024-01-02'],
                'avevol': [1000, 2000],
                'yield': [0.05, 0.06],
                'Dividend_Y10': [1.0, 1.1],
                'Rev_Growth_Y9': [0.1, 0.2],
                'OpeInc_Growth_Y9': [0.15, 0.25],
                'NetInc_Growth_Y9': [0.12, 0.22],
                'PE_TTM': [20.0, 21.0],
                'PB_TTM': [2.0, 2.1],
                'PS_TTM': [3.0, 3.1],
                'PC_TTM': [4.0, 4.1]
            })
            df.to_sql('sample_rules', conn, index=False)
        
        # Run analysis
        analyze_data(temp_db)
        
        # Verify statistics in output file
        with open('data_overview.txt', 'r') as f:
            content = f.read()
            assert 'Mean PE_TTM: 20.5' in content
            assert 'Mean yield: 0.055' in content

    def test_analyze_data_visualizations(self, temp_db):
        """Test visualization generation"""
        # Create test data
        with sqlite3.connect(temp_db) as conn:
            df = pd.DataFrame({
                'date': ['2024-01-01', '2024-01-02'],
                'avevol': [1000, 2000],
                'yield': [0.05, 0.06],
                'Dividend_Y10': [1.0, 1.1],
                'Rev_Growth_Y9': [0.1, 0.2],
                'OpeInc_Growth_Y9': [0.15, 0.25],
                'NetInc_Growth_Y9': [0.12, 0.22],
                'PE_TTM': [20.0, 21.0],
                'PB_TTM': [2.0, 2.1],
                'PS_TTM': [3.0, 3.1],
                'PC_TTM': [4.0, 4.1]
            })
            df.to_sql('sample_rules', conn, index=False)
        
        # Run analysis
        analyze_data(temp_db)
        
        # Verify visualization file
        assert Path('data_overview.png').exists()
        
        # Clean up
        Path('data_overview.png').unlink()
        Path('data_overview.txt').unlink()

    def test_analyze_data_outliers(self, temp_db):
        """Test outlier detection"""
        # Create test data with outliers
        with sqlite3.connect(temp_db) as conn:
            df = pd.DataFrame({
                'date': ['2024-01-01', '2024-01-02', '2024-01-03'],
                'avevol': [1000, 2000, 10000],  # Outlier
                'yield': [0.05, 0.06, 0.07],
                'Dividend_Y10': [1.0, 1.1, 1.2],
                'Rev_Growth_Y9': [0.1, 0.2, 0.3],
                'OpeInc_Growth_Y9': [0.15, 0.25, 0.35],
                'NetInc_Growth_Y9': [0.12, 0.22, 0.32],
                'PE_TTM': [20.0, 21.0, 22.0],
                'PB_TTM': [2.0, 2.1, 2.2],
                'PS_TTM': [3.0, 3.1, 3.2],
                'PC_TTM': [4.0, 4.1, 4.2]
            })
            df.to_sql('sample_rules', conn, index=False)
        
        # Run analysis
        analyze_data(temp_db)
        
        # Verify outlier detection in output file
        with open('data_overview.txt', 'r') as f:
            content = f.read()
            assert 'Outliers detected in avevol' in content 