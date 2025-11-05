#!/usr/bin/env python

import sqlite3
import os

def create_database():
    """Create the database and necessary tables if they don't exist."""
    
    # Ensure data directory exists
    os.makedirs('data', exist_ok=True)
    
    # Connect to SQLite database
    conn = sqlite3.connect('data/mstables.sqlite')
    cursor = conn.cursor()
    
    # Create master_symbols table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS master_symbols (
        symbol TEXT PRIMARY KEY,
        name TEXT,
        sector TEXT,
        industry TEXT,
        exchange TEXT,
        country TEXT,
        currency TEXT,
        last_updated TIMESTAMP
    )
    ''')
    
    # Create wsj_data table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS wsj_data (
        symbol TEXT PRIMARY KEY,
        name TEXT,
        price REAL,
        change REAL,
        change_percent REAL,
        volume INTEGER,
        market_cap REAL,
        pe_ratio REAL,
        forward_pe REAL,
        dividend_yield REAL,
        dividend_amount REAL,
        ex_dividend_date TEXT,
        beta REAL,
        eps REAL,
        earnings_date TEXT,
        last_updated TIMESTAMP,
        FOREIGN KEY (symbol) REFERENCES master_symbols(symbol)
    )
    ''')
    
    # Create Morningstar tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS morningstar_valuation (
        symbol TEXT PRIMARY KEY,
        pe_ratio REAL,
        forward_pe REAL,
        peg_ratio REAL,
        price_to_sales REAL,
        price_to_book REAL,
        price_to_cash_flow REAL,
        price_to_free_cash_flow REAL,
        effective_until TEXT,
        FOREIGN KEY (symbol) REFERENCES master_symbols(symbol)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS morningstar_financial_health (
        symbol TEXT PRIMARY KEY,
        current_ratio REAL,
        quick_ratio REAL,
        debt_to_equity REAL,
        interest_coverage REAL,
        effective_until TEXT,
        FOREIGN KEY (symbol) REFERENCES master_symbols(symbol)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS morningstar_profitability (
        symbol TEXT PRIMARY KEY,
        gross_margin REAL,
        operating_margin REAL,
        net_margin REAL,
        return_on_equity REAL,
        return_on_assets REAL,
        effective_until TEXT,
        FOREIGN KEY (symbol) REFERENCES master_symbols(symbol)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS morningstar_efficiency (
        symbol TEXT PRIMARY KEY,
        asset_turnover REAL,
        inventory_turnover REAL,
        receivables_turnover REAL,
        effective_until TEXT,
        FOREIGN KEY (symbol) REFERENCES master_symbols(symbol)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS morningstar_growth (
        symbol TEXT PRIMARY KEY,
        revenue_growth REAL,
        earnings_growth REAL,
        free_cash_flow_growth REAL,
        effective_until TEXT,
        FOREIGN KEY (symbol) REFERENCES master_symbols(symbol)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS morningstar_cash_flow (
        symbol TEXT PRIMARY KEY,
        operating_cash_flow_ratio REAL,
        free_cash_flow_ratio REAL,
        cash_conversion_cycle REAL,
        effective_until TEXT,
        FOREIGN KEY (symbol) REFERENCES master_symbols(symbol)
    )
    ''')
    
    # Create indices for better query performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_master_symbol ON master_symbols(symbol)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_wsj_symbol ON wsj_data(symbol)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ms_val_symbol ON morningstar_valuation(symbol)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ms_fh_symbol ON morningstar_financial_health(symbol)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ms_prof_symbol ON morningstar_profitability(symbol)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ms_eff_symbol ON morningstar_efficiency(symbol)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ms_growth_symbol ON morningstar_growth(symbol)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ms_cf_symbol ON morningstar_cash_flow(symbol)')
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print("Database schema created successfully.")

if __name__ == "__main__":
    create_database() 