import pandas as pd
import sqlite3
import logging
from pathlib import Path
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('reference_data_ingest.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

class ReferenceDataIngester:
    def __init__(self, 
                 db_path: str = 'data/mstables.sqlite',
                 input_dir: str = 'input'):
        self.db_path = db_path
        self.input_dir = Path(input_dir)
        self.data_dir = self.input_dir / 'data'
        
    def ingest_symbols(self) -> None:
        """Ingest symbols.csv into the database"""
        try:
            df = pd.read_csv(self.data_dir / 'symbols.csv')
            with sqlite3.connect(self.db_path) as conn:
                df.to_sql('symbols', conn, if_exists='replace', index=False)
            logging.info(f"Ingested {len(df)} symbols into database")
        except Exception as e:
            logging.error(f"Error ingesting symbols: {str(e)}")
            raise
            
    def ingest_country_codes(self) -> None:
        """Ingest ctycodes.csv into the database"""
        try:
            df = pd.read_csv(self.data_dir / 'ctycodes.csv')
            with sqlite3.connect(self.db_path) as conn:
                df.to_sql('country_codes', conn, if_exists='replace', index=False)
            logging.info(f"Ingested {len(df)} country codes into database")
        except Exception as e:
            logging.error(f"Error ingesting country codes: {str(e)}")
            raise
            
    def ingest_investment_types(self) -> None:
        """Ingest ms_investment-types.csv into the database"""
        try:
            df = pd.read_csv(self.data_dir / 'ms_investment-types.csv')
            with sqlite3.connect(self.db_path) as conn:
                df.to_sql('investment_types', conn, if_exists='replace', index=False)
            logging.info(f"Ingested {len(df)} investment types into database")
        except Exception as e:
            logging.error(f"Error ingesting investment types: {str(e)}")
            raise
            
    def run(self) -> None:
        """Run the ingestion process"""
        try:
            self.ingest_symbols()
            self.ingest_country_codes()
            self.ingest_investment_types()
            logging.info("Successfully ingested all reference data")
        except Exception as e:
            logging.error(f"Process failed: {str(e)}")
            raise

if __name__ == "__main__":
    ingester = ReferenceDataIngester()
    ingester.run() 