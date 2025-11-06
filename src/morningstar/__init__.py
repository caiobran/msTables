"""
Morningstar Data Module

This module provides functionality to fetch data from Morningstar.
It uses the MorningstarFetcher class to fetch and store data in the database.
"""

from .fetcher import MorningstarFetcher
import sqlite3
import pandas as pd

def fetch_morningstar_data():
    """Fetch data from Morningstar API."""
    fetcher = MorningstarFetcher()
    conn = sqlite3.connect(fetcher.db_path)
    symbols = pd.read_sql('SELECT symbol FROM master_symbols', conn)['symbol'].tolist()
    conn.close()
    if not symbols:
        print("No symbols found in master_symbols table. Please add some symbols first.")
        return []
    return fetcher.fetch_all_symbols(symbols, test_mode=True)

__all__ = ['fetch_morningstar_data'] 