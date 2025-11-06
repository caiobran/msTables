import pytest
from src.utils.clean_sample_rules import clean_sample_rules
import pandas as pd
from pathlib import Path
import tempfile

class TestCleanSampleRules:
    def test_clean_sample_rules_basic(self, sample_csv):
        """Test basic cleaning functionality"""
        output_path = 'data/sample_rules_cleaned.csv'
        clean_sample_rules(sample_csv, output_path)
        
        # Verify output file exists
        assert Path(output_path).exists()
        
        # Verify cleaned data
        df = pd.read_csv(output_path)
        assert not df.isnull().any().any()
        assert all(col in df.columns for col in [
            'avevol', 'yield', 'Dividend_Y10', 'Rev_Growth_Y9',
            'OpeInc_Growth_Y9', 'NetInc_Growth_Y9', 'PE_TTM',
            'PB_TTM', 'PS_TTM', 'PC_TTM'
        ])

    def test_clean_sample_rules_missing_file(self):
        """Test handling of missing input file"""
        with pytest.raises(FileNotFoundError):
            clean_sample_rules('nonexistent.csv')

    def test_clean_sample_rules_missing_columns(self, tempfile):
        """Test handling of missing required columns"""
        # Create CSV with missing columns
        df = pd.DataFrame({'date': ['2024-01-01'], 'other_col': [1]})
        df.to_csv(tempfile, index=False)
        
        with pytest.raises(ValueError):
            clean_sample_rules(tempfile)

    def test_clean_sample_rules_numeric_validation(self, sample_csv):
        """Test numeric value validation"""
        output_path = 'data/sample_rules_cleaned.csv'
        clean_sample_rules(sample_csv, output_path)
        
        df = pd.read_csv(output_path)
        numeric_cols = [
            'avevol', 'yield', 'Dividend_Y10', 'Rev_Growth_Y9',
            'OpeInc_Growth_Y9', 'NetInc_Growth_Y9', 'PE_TTM',
            'PB_TTM', 'PS_TTM', 'PC_TTM'
        ]
        
        for col in numeric_cols:
            assert df[col].dtype in ['int64', 'float64']
            assert df[col].round(2).equals(df[col])  # Check rounding

    def test_clean_sample_rules_negative_values(self, tempfile):
        """Test handling of negative values"""
        # Create CSV with negative values
        df = pd.DataFrame({
            'date': ['2024-01-01'],
            'avevol': [-1000],
            'yield': [0.05],
            'Dividend_Y10': [1.0],
            'Rev_Growth_Y9': [-0.1],  # Allowed negative
            'OpeInc_Growth_Y9': [-0.15],  # Allowed negative
            'NetInc_Growth_Y9': [-0.12],  # Allowed negative
            'PE_TTM': [-20.0],
            'PB_TTM': [2.0],
            'PS_TTM': [3.0],
            'PC_TTM': [4.0]
        })
        df.to_csv(tempfile, index=False)
        
        output_path = 'data/sample_rules_cleaned.csv'
        clean_sample_rules(tempfile, output_path)
        
        df = pd.read_csv(output_path)
        assert df['PE_TTM'].iloc[0] == 0  # Should be zeroed
        assert df['Rev_Growth_Y9'].iloc[0] == -0.1  # Should remain negative 