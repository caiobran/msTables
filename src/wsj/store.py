import sqlite3
import json
import pandas as pd
from datetime import datetime
import os

def store_wsj_data(data, db_path):
    """Store parsed WSJ data in the database and save CSV/raw files.
    Returns a list of tickers that were updated."""
    if data is None or data.empty:
        print("No data to store")
        return []
    
    # Create timestamp for filenames
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    fetch_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Save raw data
    raw_dir = 'data/raw/wsj'
    os.makedirs(raw_dir, exist_ok=True)
    raw_file = os.path.join(raw_dir, f'wsj_raw_{timestamp}.json')
    with open(raw_file, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Saved raw data to {raw_file}")
    
    # Save CSV
    csv_dir = 'data/csv/wsj'
    os.makedirs(csv_dir, exist_ok=True)
    csv_file = os.path.join(csv_dir, f'wsj_data_{timestamp}.csv')
    data.to_csv(csv_file, index=False)
    print(f"Saved CSV data to {csv_file}")
    
    # Store in SQLite
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Update master_symbols table
    master_records = []
    for _, row in data.iterrows():
        master_record = (
            row['symbol'],
            row['name'],
            row['exchange'],
            row['country'],
            row['type'],
            'WSJ',
            fetch_date,
            1  # is_active
        )
        master_records.append(master_record)
    
    cursor.executemany('''
        INSERT OR REPLACE INTO master_symbols (
            symbol, name, exchange, country, type, source, last_updated, is_active
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', master_records)
    
    # Store in wsj_data table
    wsj_records = []
    for _, row in data.iterrows():
        record = (
            row['symbol'],
            row['name'],
            row['country'],
            row['exchange'],
            row['type'],
            row['last_price'],
            row['change'],
            row['percent_change'],
            row['daily_high'],
            row['daily_low'],
            row['timestamp'],
            row['url'],
            fetch_date
        )
        wsj_records.append(record)
    
    cursor.executemany('''
        INSERT INTO wsj_data (
            symbol, name, country, exchange, type,
            last_price, change, percent_change,
            daily_high, daily_low, timestamp, url, fetch_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', wsj_records)
    
    conn.commit()
    conn.close()
    
    print(f"Stored {len(wsj_records)} records in wsj_data table")
    print(f"Updated {len(master_records)} symbols in master_symbols table")
    return [record[0] for record in master_records]  # Return list of symbols 