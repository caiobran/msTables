import pandas as pd
import sqlite3
import logging
import sys
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pot_stocks_ingest.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

class PotStocksIngester:
    def __init__(self, 
                 db_path: str = 'data/mstables.sqlite',
                 csv_path: str = 'input/data/pot_stocks.csv'):
        self.db_path = db_path
        self.csv_path = csv_path

    def ingest(self) -> None:
        try:
            df = pd.read_csv(self.csv_path)
            with sqlite3.connect(self.db_path) as conn:
                df.to_sql('pot_stocks', conn, if_exists='replace', index=False)
            logging.info(f"Ingested {len(df)} rows into pot_stocks table in {self.db_path}")
        except Exception as e:
            logging.error(f"Error ingesting pot_stocks: {str(e)}")
            raise

if __name__ == "__main__":
    ingester = PotStocksIngester()
    ingester.ingest() 