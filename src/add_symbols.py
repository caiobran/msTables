#!/usr/bin/env python
# coding: utf-8

"""
Add common stock symbols to the master_symbols table
"""

import sqlite3
from datetime import datetime

# List of common stock symbols to add
COMMON_SYMBOLS = [
    'AAPL',  # Apple
    'MSFT',  # Microsoft
    'GOOGL', # Alphabet
    'AMZN',  # Amazon
    'META',  # Meta (Facebook)
    'TSLA',  # Tesla
    'NVDA',  # NVIDIA
    'JPM',   # JPMorgan Chase
    'V',     # Visa
    'WMT',   # Walmart
    'JNJ',   # Johnson & Johnson
    'PG',    # Procter & Gamble
    'MA',    # Mastercard
    'HD',    # Home Depot
    'BAC',   # Bank of America
    'XOM',   # Exxon Mobil
    'DIS',   # Disney
    'NFLX',  # Netflix
    'KO',    # Coca-Cola
    'PFE'    # Pfizer
]

def add_symbols():
    """Add symbols to the master_symbols table"""
    conn = sqlite3.connect('data/mstables.sqlite')
    cursor = conn.cursor()

    try:
        # Check if table exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS master_symbols (
                symbol TEXT PRIMARY KEY,
                name TEXT,
                sector TEXT,
                industry TEXT,
                exchange TEXT,
                country TEXT,
                currency TEXT,
                last_updated TEXT
            )
        """)

        # Add symbols
        for symbol in COMMON_SYMBOLS:
            cursor.execute("""
                INSERT OR REPLACE INTO master_symbols (
                    symbol, last_updated
                ) VALUES (?, ?)
            """, (symbol, datetime.now().isoformat()))

        conn.commit()
        print(f"Successfully added {len(COMMON_SYMBOLS)} symbols to master_symbols table")

    except Exception as e:
        conn.rollback()
        print(f"Error adding symbols: {str(e)}")
        raise

    finally:
        conn.close()

if __name__ == "__main__":
    add_symbols() 