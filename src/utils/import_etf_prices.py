import os
import pandas as pd
import sqlite3
import logging
from tqdm import tqdm

ETF_FOLDER = '/Users/xavier/sbox/Financial_Data/ETFs'
DB_PATH = 'data/mstables.sqlite'

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('etf_import.log'),
        logging.StreamHandler()
    ]
)

def upsert_etf_prices(df, symbol, conn):
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
                INSERT INTO etf_prices (symbol, date, open, high, low, close, volume, adj_close)
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
    conn = sqlite3.connect(DB_PATH)
    files = [f for f in os.listdir(ETF_FOLDER) if f.endswith('.txt')]
    logging.info(f"Found {len(files)} ETF files to process.")
    for file in tqdm(files, desc="Importing ETF files"):
        symbol = file.replace('.txt', '')
        file_path = os.path.join(ETF_FOLDER, file)
        try:
            df = pd.read_csv(file_path)
            # Ensure correct columns
            required_cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
            if not all(col in df.columns for col in required_cols):
                logging.warning(f"Skipping {file}: missing required columns.")
                continue
            # Only keep required columns
            df = df[required_cols]
            upsert_etf_prices(df, symbol, conn)
            conn.commit()
            logging.info(f"Imported {len(df)} rows for {symbol}")
        except Exception as e:
            logging.error(f"Failed to import {file}: {e}")
    conn.close()
    logging.info("ETF import process completed.")

if __name__ == "__main__":
    main() 