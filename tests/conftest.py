import pytest
import sqlite3
import pandas as pd
from pathlib import Path
import tempfile
import shutil

@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    with tempfile.NamedTemporaryFile(suffix='.sqlite') as tmp:
        yield tmp.name

@pytest.fixture
def sample_csv():
    """Create a sample CSV file for testing"""
    with tempfile.NamedTemporaryFile(suffix='.csv', mode='w') as tmp:
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
        df.to_csv(tmp.name, index=False)
        yield tmp.name 