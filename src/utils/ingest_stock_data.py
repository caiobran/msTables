import pandas as pd
import sqlite3
from datetime import datetime
import logging
from pathlib import Path
import sys
from typing import Dict, List, Tuple, Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_ingestion.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

class StockDataIngester:
    def __init__(self, csv_path: str = 'data/data_stocks.csv', db_path: str = 'data/mstables.sqlite'):
        self.csv_path = csv_path
        self.db_path = db_path
        self.conn = None
        self.ingestion_stats = {
            'tickers_processed': 0,
            'records_added': 0,
            'records_updated': 0,
            'errors': 0
        }
        
    def __enter__(self):
        self.conn = sqlite3.connect(self.db_path)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()
            
    def get_existing_data(self, ticker: str) -> pd.DataFrame:
        """Get existing data for a ticker from tiingo_prices table"""
        query = f"""
            SELECT symbol, date, open, high, low, close, volume
            FROM tiingo_prices
            WHERE symbol = '{ticker}'
        """
        return pd.read_sql_query(query, self.conn)
    
    def validate_price_data(self, df: pd.DataFrame) -> Tuple[bool, str]:
        """Validate price data for quality issues"""
        if df.empty:
            return False, "Empty dataframe"
            
        # Check for missing values
        if df[['open', 'high', 'low', 'close']].isnull().any().any():
            return False, "Missing price values"
            
        # Check for negative prices
        if (df[['open', 'high', 'low', 'close']] < 0).any().any():
            return False, "Negative price values"
            
        # Check for high-low consistency
        if not (df['high'] >= df['low']).all():
            return False, "High price less than low price"
            
        # Check for open/close within high/low range
        if not ((df['open'] >= df['low']) & (df['open'] <= df['high'])).all():
            return False, "Open price outside high-low range"
        if not ((df['close'] >= df['low']) & (df['close'] <= df['high'])).all():
            return False, "Close price outside high-low range"
            
        return True, "Valid"
    
    def prepare_csv_data(self, ticker: str) -> Optional[pd.DataFrame]:
        """Read and prepare data from CSV for a specific ticker"""
        try:
            # Read CSV file
            df = pd.read_csv(self.csv_path)
            
            # Convert Unix timestamp to datetime
            df['DATE'] = pd.to_datetime(df['DATE'], unit='s')
            
            # Get the column name for the ticker
            ticker_col = f'NASDAQ.{ticker}' if f'NASDAQ.{ticker}' in df.columns else f'NYSE.{ticker}'
            if ticker_col not in df.columns:
                logging.warning(f"Ticker {ticker} not found in CSV")
                return None
                
            # Prepare the data
            result = df[['DATE', ticker_col]].copy()
            result.columns = ['date', 'close']
            
            # Since CSV only has close prices, we'll use the same value for open, high, low
            result['open'] = result['close']
            result['high'] = result['close']
            result['low'] = result['close']
            result['volume'] = None  # Volume not available in CSV
            result['symbol'] = ticker
            
            return result
            
        except Exception as e:
            logging.error(f"Error preparing CSV data for {ticker}: {str(e)}")
            return None
    
    def update_database(self, ticker: str, new_data: pd.DataFrame) -> None:
        """Update the database with new data"""
        try:
            # Get existing data
            existing_data = self.get_existing_data(ticker)
            
            if not existing_data.empty:
                # Convert both date columns to timezone-naive datetime
                existing_data['date'] = pd.to_datetime(existing_data['date']).dt.tz_localize(None)
                new_data['date'] = pd.to_datetime(new_data['date']).dt.tz_localize(None)
                
                # Find new and updated records
                merged = pd.merge(
                    new_data, 
                    existing_data, 
                    on=['symbol', 'date'], 
                    how='left', 
                    suffixes=('_new', '_existing')
                )
                
                # New records (no existing data)
                new_records = merged[merged['close_existing'].isna()]
                if not new_records.empty:
                    new_records = new_records[['symbol', 'date', 'open_new', 'high_new', 
                                             'low_new', 'close_new', 'volume_new']]
                    new_records.columns = ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']
                    # Convert date to string format for SQLite
                    new_records['date'] = new_records['date'].dt.strftime('%Y-%m-%d')
                    new_records.to_sql('tiingo_prices', self.conn, if_exists='append', index=False)
                    self.ingestion_stats['records_added'] += len(new_records)
                
                # Updated records (different prices)
                updated_records = merged[
                    (merged['close_new'] != merged['close_existing']) & 
                    (~merged['close_existing'].isna())
                ]
                if not updated_records.empty:
                    for _, row in updated_records.iterrows():
                        self.conn.execute("""
                            UPDATE tiingo_prices 
                            SET open = ?, high = ?, low = ?, close = ?, volume = ?
                            WHERE symbol = ? AND date = ?
                        """, (
                            row['open_new'], row['high_new'], row['low_new'],
                            row['close_new'], row['volume_new'], ticker, 
                            row['date'].strftime('%Y-%m-%d')
                        ))
                    self.ingestion_stats['records_updated'] += len(updated_records)
            else:
                # No existing data, insert all records
                # Convert date to string format for SQLite
                new_data['date'] = new_data['date'].dt.strftime('%Y-%m-%d')
                new_data.to_sql('tiingo_prices', self.conn, if_exists='append', index=False)
                self.ingestion_stats['records_added'] += len(new_data)
                
            self.conn.commit()
            
        except Exception as e:
            self.conn.rollback()
            logging.error(f"Error updating database for {ticker}: {str(e)}")
            self.ingestion_stats['errors'] += 1
    
    def process_ticker(self, ticker: str) -> None:
        """Process a single ticker"""
        logging.info(f"Processing ticker: {ticker}")
        
        # Get data from CSV
        csv_data = self.prepare_csv_data(ticker)
        if csv_data is None:
            return
            
        # Validate data
        is_valid, message = self.validate_price_data(csv_data)
        if not is_valid:
            logging.warning(f"Data validation failed for {ticker}: {message}")
            return
            
        # Update database
        self.update_database(ticker, csv_data)
        self.ingestion_stats['tickers_processed'] += 1
        
    def get_all_tickers(self) -> List[str]:
        """Get all tickers from CSV file"""
        df = pd.read_csv(self.csv_path, nrows=1)
        tickers = []
        for col in df.columns:
            if col not in ['DATE', 'SP500']:
                ticker = col.split('.')[-1]
                if ticker not in tickers:
                    tickers.append(ticker)
        return tickers
    
    def run(self) -> None:
        """Run the ingestion process"""
        logging.info("Starting data ingestion process")
        
        # Get all tickers
        tickers = self.get_all_tickers()
        logging.info(f"Found {len(tickers)} tickers to process")
        
        # Process each ticker
        for ticker in tickers:
            self.process_ticker(ticker)
            
        # Log final statistics
        logging.info("Ingestion process completed")
        logging.info(f"Statistics: {self.ingestion_stats}")

if __name__ == "__main__":
    with StockDataIngester() as ingester:
        ingester.run() 