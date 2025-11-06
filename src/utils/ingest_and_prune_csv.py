import pandas as pd
import sqlite3
import logging
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ingest_and_prune.log'),
        logging.StreamHandler()
    ]
)

def main(csv_path='data/data_stocks.csv', db_path='data/mstables.sqlite'):
    csv_path = Path(csv_path)
    if not csv_path.exists():
        logging.error(f"CSV file not found: {csv_path}")
        return

    # Read CSV
    df = pd.read_csv(csv_path)
    date_col = df.columns[0]
    df[date_col] = pd.to_datetime(df[date_col], unit='s', errors='coerce')
    df = df.dropna(subset=[date_col])
    csv_dates = set(df[date_col].dt.date)

    # Get dates from DB
    with sqlite3.connect(db_path) as conn:
        db_dates = set(pd.read_sql_query(
            "SELECT DISTINCT date FROM tiingo_prices", conn
        )['date'].apply(lambda x: pd.to_datetime(x).date()))

    # Find new dates
    new_dates = csv_dates - db_dates
    if not new_dates:
        logging.info("All data in CSV is already present in the database. Deleting CSV.")
        csv_path.unlink()
        return

    # Keep only new dates
    df_new = df[df[date_col].dt.date.isin(new_dates)]
    logging.info(f"Rows to ingest: {len(df_new)} (out of {len(df)})")
    if df_new.empty:
        logging.info("No new data to ingest. Deleting CSV.")
        csv_path.unlink()
        return

    # Ingest new data (append to a new table for now, or you can map columns to tiingo_prices if needed)
    table_name = 'data_stocks_ingested'
    with sqlite3.connect(db_path) as conn:
        df_new.to_sql(table_name, conn, if_exists='append', index=False)
    logging.info(f"Ingested {len(df_new)} rows into {table_name}.")

    # Overwrite CSV with only new data (if any left)
    df_new.to_csv(csv_path, index=False)
    logging.info(f"CSV updated with only new data. Remaining rows: {len(df_new)}")

if __name__ == "__main__":
    main() 