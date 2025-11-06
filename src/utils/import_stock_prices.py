import os
import pandas as pd
import sqlite3
import logging
from tqdm import tqdm

STOCK_FOLDER = '/Users/xavier/sbox/Financial_Data/Stocks'
DB_PATH = 'data/mstables.sqlite'

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('stock_import.log'),
        logging.StreamHandler()
    ]
)

def upsert_stock_prices(df, symbol, conn):
    """Upsert stock price data into the database."""
    for _, row in df.iterrows():
        date = row['Date']
        open_ = row['Open']
        high = row['High']
        low = row['Low']
        close = row['Close']
        volume = row['Volume']
        adj_close = close  # No adj_close in file, use close
        try:
            conn.execute('''
                INSERT INTO stock_prices (symbol, date, open, high, low, close, volume, adj_close)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol, date) DO UPDATE SET
                    open=excluded.open,
                    high=excluded.high,
                    low=excluded.low,
                    close=excluded.close,
                    volume=excluded.volume,
                    adj_close=excluded.adj_close;
            ''', (symbol, date, open_, high, low, close, volume, adj_close))
        except Exception as e:
            logging.error(f"Error upserting {symbol} {date}: {e}")

def main():
    # Create stock_prices table if it doesn't exist
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS stock_prices (
            symbol TEXT,
            date TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            adj_close REAL,
            PRIMARY KEY (symbol, date)
        )
    ''')
    
    # Get list of stock files
    files = [f for f in os.listdir(STOCK_FOLDER) if f.endswith('.txt')]
    logging.info(f"Found {len(files)} stock files to process.")
    
    # Process each file
    for file in tqdm(files, desc="Importing stock files"):
        symbol = file.replace('.txt', '')
        file_path = os.path.join(STOCK_FOLDER, file)
        try:
            # Read CSV file
            df = pd.read_csv(file_path)
            
            # Ensure correct columns
            required_cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
            if not all(col in df.columns for col in required_cols):
                logging.warning(f"Skipping {file}: missing required columns.")
                continue
                
            # Only keep required columns
            df = df[required_cols]
            
            # Convert date to string format
            df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
            
            # Upsert data
            upsert_stock_prices(df, symbol, conn)
            conn.commit()
            logging.info(f"Imported {len(df)} rows for {symbol}")
            
        except Exception as e:
            logging.error(f"Failed to import {file}: {e}")
            continue
    
    conn.close()
    logging.info("Stock import process completed.")

if __name__ == "__main__":
    main() 