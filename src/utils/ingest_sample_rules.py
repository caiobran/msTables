import pandas as pd
import sqlite3
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ingest_sample_rules.log'),
        logging.StreamHandler()
    ]
)

def ingest_sample_rules(csv_path='data/sample_rules_cleaned.csv', db_path='data/mstables.sqlite'):
    csv_path = Path(csv_path)
    if not csv_path.exists():
        logging.error(f"CSV file not found: {csv_path}")
        return

    # Read CSV
    df = pd.read_csv(csv_path)
    logging.info(f"Read {len(df)} rows from {csv_path}")

    # Ingest into database
    table_name = 'sample_rules'
    with sqlite3.connect(db_path) as conn:
        df.to_sql(table_name, conn, if_exists='replace', index=False)
    logging.info(f"Ingested {len(df)} rows into {table_name}")

if __name__ == "__main__":
    ingest_sample_rules() 