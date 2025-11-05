#!/usr/bin/env python
# coding: utf-8

"""
Tiingo Data Fetcher
This script fetches financial data from Tiingo's API and stores it in our database.
"""

import requests
import pandas as pd
import sqlite3
from datetime import datetime
import time
import logging
import os
import traceback
from tiingo import TiingoClient

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db_path():
    """Get the absolute path to the database file"""
    # Get the project root directory (2 levels up from this file)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    db_path = os.path.join(project_root, 'data', 'mstables.sqlite')
    
    # Create data directory if it doesn't exist
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    return db_path

class TiingoFetcher:
    def __init__(self, db_path=None):
        self.db_path = db_path or get_db_path()
        self.config = {
            'api_key': "5b49a6c9c981826034492cb8b2d32f3b7a54cd4c",
            'session': True
        }
        self.client = TiingoClient(self.config)
        
        # Create database tables if they don't exist
        self._create_tables()

    def _create_tables(self):
        """Create necessary database tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Create error_log table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS error_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    source TEXT,
                    symbol TEXT,
                    error_type TEXT,
                    error_message TEXT,
                    stack_trace TEXT,
                    context TEXT
                )
            """)
            
            # Create table_updates table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS table_updates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    table_name TEXT,
                    operation TEXT,
                    symbol TEXT,
                    rows_affected INTEGER,
                    status TEXT,
                    details TEXT
                )
            """)
            
            # Create tiingo tables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tiingo_metadata (
                    symbol TEXT PRIMARY KEY,
                    name TEXT,
                    description TEXT,
                    exchange TEXT,
                    currency TEXT,
                    last_updated TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tiingo_prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT,
                    date TEXT,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume INTEGER,
                    adj_open REAL,
                    adj_high REAL,
                    adj_low REAL,
                    adj_close REAL,
                    adj_volume INTEGER,
                    div_cash REAL,
                    split_factor REAL,
                    last_updated TEXT,
                    UNIQUE(symbol, date)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tiingo_fundamentals (
                    symbol TEXT,
                    date TEXT,
                    market_cap REAL,
                    enterprise_val REAL,
                    pe_ratio REAL,
                    pb_ratio REAL,
                    ps_ratio REAL,
                    pcf_ratio REAL,
                    last_updated TEXT,
                    PRIMARY KEY (symbol, date)
                )
            """)
            
            conn.commit()
            logger.info("Database tables created successfully")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error creating tables: {str(e)}")
            raise
        finally:
            conn.close()

    def _log_error(self, source, symbol, error_type, error_message, stack_trace=None, context=None):
        """Log an error to the error_log table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO error_log (
                    timestamp, source, symbol, error_type, 
                    error_message, stack_trace, context
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                source,
                symbol,
                error_type,
                str(error_message),
                stack_trace,
                context
            ))
            conn.commit()
        finally:
            conn.close()

    def _log_table_update(self, table_name, operation, symbol, rows_affected, status, details=None):
        """Log a table update to the table_updates table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO table_updates (
                    timestamp, table_name, operation, symbol,
                    rows_affected, status, details
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                table_name,
                operation,
                symbol,
                rows_affected,
                status,
                details
            ))
            conn.commit()
        finally:
            conn.close()

    def fetch_stock_data(self, symbol):
        """Fetch all available data for a specific stock symbol"""
        try:
            logger.info(f"Starting data fetch for {symbol}")
            
            # 1. Metadata
            logger.info(f"Fetching metadata for {symbol}")
            metadata = self._fetch_metadata(symbol)
            if metadata:
                logger.info(f"Storing metadata for {symbol}")
                self._store_metadata(symbol, metadata)
            else:
                logger.warning(f"No metadata available for {symbol}")

            # 2. Price Data
            logger.info(f"Fetching price data for {symbol}")
            prices = self._fetch_prices(symbol)
            if prices:
                logger.info(f"Storing price data for {symbol}")
                self._store_prices(symbol, prices)
            else:
                logger.warning(f"No price data available for {symbol}")

            # 3. Fundamentals
            logger.info(f"Fetching fundamentals for {symbol}")
            fundamentals = self._fetch_fundamentals(symbol)
            if fundamentals:
                logger.info(f"Storing fundamentals for {symbol}")
                self._store_fundamentals(symbol, fundamentals)
            else:
                logger.warning(f"No fundamentals available for {symbol}")

            logger.info(f"Successfully completed data fetch for {symbol}")
            return True

        except Exception as e:
            self._log_error(
                'tiingo_fetcher',
                symbol,
                'FETCH_ERROR',
                str(e),
                stack_trace=traceback.format_exc(),
                context=f"Failed to fetch data for {symbol}"
            )
            logger.error(f"Error fetching data for {symbol}: {str(e)}")
            return False

    def _fetch_metadata(self, symbol):
        """Fetch stock metadata"""
        try:
            metadata = self.client.get_ticker_metadata(symbol)
            logger.debug(f"Metadata response for {symbol}: {metadata}")
            return metadata
        except Exception as e:
            logger.error(f"Failed to fetch metadata for {symbol}: {str(e)}")
            return None

    def _fetch_prices(self, symbol):
        """Fetch historical price data"""
        try:
            # Get last 30 days of daily prices
            end_date = datetime.now()
            start_date = end_date.replace(day=1)  # First day of current month
            
            prices = self.client.get_ticker_price(
                symbol,
                fmt='json',
                startDate=start_date.strftime('%Y-%m-%d'),
                endDate=end_date.strftime('%Y-%m-%d'),
                frequency='daily'
            )
            logger.debug(f"Price response for {symbol}: {prices}")
            return prices
        except Exception as e:
            logger.error(f"Failed to fetch prices for {symbol}: {str(e)}")
            return None

    def _fetch_fundamentals(self, symbol):
        """Fetch fundamental data"""
        try:
            # Get last 30 days of daily fundamentals
            end_date = datetime.now()
            start_date = end_date.replace(day=1)  # First day of current month
            
            fundamentals = self.client.get_fundamentals_daily(
                symbol,
                startDate=start_date.strftime('%Y-%m-%d'),
                endDate=end_date.strftime('%Y-%m-%d')
            )
            logger.debug(f"Fundamentals response for {symbol}: {fundamentals}")
            return fundamentals
        except Exception as e:
            logger.error(f"Failed to fetch fundamentals for {symbol}: {str(e)}")
            return None

    def _store_metadata(self, symbol, data):
        """Store stock metadata"""
        if not data:
            logger.warning(f"No metadata to store for {symbol}")
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            logger.info(f"Storing metadata for {symbol}: {data}")
            cursor.execute("""
                INSERT OR REPLACE INTO tiingo_metadata (
                    symbol, name, description, exchange,
                    currency, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                symbol,
                data.get('name'),
                data.get('description'),
                data.get('exchangeCode'),
                data.get('currency'),
                datetime.now().isoformat()
            ))
            conn.commit()
            logger.info(f"Successfully stored metadata for {symbol}")
            self._log_table_update(
                'tiingo_metadata',
                'INSERT_OR_REPLACE',
                symbol,
                1,
                'SUCCESS',
                f"Updated metadata for {symbol}"
            )
        except Exception as e:
            logger.error(f"Error storing metadata for {symbol}: {str(e)}")
            self._log_error(
                'tiingo_metadata',
                symbol,
                'DATABASE_ERROR',
                str(e),
                context=f"Failed to store metadata for {symbol}"
            )
            raise
        finally:
            conn.close()

    def _store_prices(self, symbol, data):
        """Store price data"""
        if not data:
            logger.warning(f"No price data to store for {symbol}")
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            logger.info(f"Storing price data for {symbol}")
            rows_affected = 0
            
            for price in data:
                cursor.execute("""
                    INSERT OR REPLACE INTO tiingo_prices (
                        symbol, date, open, high, low, close, volume,
                        adj_open, adj_high, adj_low, adj_close, adj_volume,
                        div_cash, split_factor, last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    symbol,
                    price.get('date'),
                    price.get('open'),
                    price.get('high'),
                    price.get('low'),
                    price.get('close'),
                    price.get('volume'),
                    price.get('adjOpen'),
                    price.get('adjHigh'),
                    price.get('adjLow'),
                    price.get('adjClose'),
                    price.get('adjVolume'),
                    price.get('divCash'),
                    price.get('splitFactor'),
                    datetime.now().isoformat()
                ))
                rows_affected += 1
            
            conn.commit()
            logger.info(f"Successfully stored {rows_affected} price records for {symbol}")
            self._log_table_update(
                'tiingo_prices',
                'INSERT_OR_REPLACE',
                symbol,
                rows_affected,
                'SUCCESS',
                f"Updated {rows_affected} price records for {symbol}"
            )
        except Exception as e:
            logger.error(f"Error storing price data for {symbol}: {str(e)}")
            self._log_error(
                'tiingo_prices',
                symbol,
                'DATABASE_ERROR',
                str(e),
                context=f"Failed to store price data for {symbol}"
            )
            raise
        finally:
            conn.close()

    def _store_fundamentals(self, symbol, data):
        """Store fundamental data"""
        if not data:
            logger.warning(f"No fundamental data to store for {symbol}")
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            logger.info(f"Storing fundamental data for {symbol}")
            rows_affected = 0
            
            for fundamental in data:
                cursor.execute("""
                    INSERT OR REPLACE INTO tiingo_fundamentals (
                        symbol, date, market_cap, enterprise_val,
                        pe_ratio, pb_ratio, ps_ratio, pcf_ratio,
                        last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    symbol,
                    fundamental.get('date'),
                    fundamental.get('marketCap'),
                    fundamental.get('enterpriseVal'),
                    fundamental.get('peRatio'),
                    fundamental.get('pbRatio'),
                    fundamental.get('psRatio'),
                    fundamental.get('pcfRatio'),
                    datetime.now().isoformat()
                ))
                rows_affected += 1
            
            conn.commit()
            logger.info(f"Successfully stored {rows_affected} fundamental records for {symbol}")
            self._log_table_update(
                'tiingo_fundamentals',
                'INSERT_OR_REPLACE',
                symbol,
                rows_affected,
                'SUCCESS',
                f"Updated {rows_affected} fundamental records for {symbol}"
            )
        except Exception as e:
            logger.error(f"Error storing fundamental data for {symbol}: {str(e)}")
            self._log_error(
                'tiingo_fundamentals',
                symbol,
                'DATABASE_ERROR',
                str(e),
                context=f"Failed to store fundamental data for {symbol}"
            )
            raise
        finally:
            conn.close()

    def fetch_all_symbols(self, symbols, batch_size=25, delay_between_batches=30, test_mode=False):
        """
        Fetch data for all symbols in batches with rate limiting
        
        Args:
            symbols (list): List of symbols to fetch
            batch_size (int): Number of symbols to process in each batch
            delay_between_batches (int): Seconds to wait between batches
            test_mode (bool): If True, only process first batch
        """
        # Ensure symbols is a list
        if not isinstance(symbols, list):
            symbols = list(symbols)
            
        if test_mode:
            symbols = symbols[:batch_size]
            logger.info(f"Running in test mode with {len(symbols)} symbols")
        
        total_symbols = len(symbols)
        total_success = 0
        total_failed = 0
        
        # Process symbols in batches
        for i in range(0, total_symbols, batch_size):
            batch = symbols[i:i + batch_size]
            batch_success = 0
            batch_start_time = time.time()
            
            logger.info(f"\nProcessing batch {i//batch_size + 1} of {(total_symbols + batch_size - 1)//batch_size}")
            logger.info(f"Symbols in this batch: {', '.join(str(s) for s in batch)}")
            
            # Process each symbol in the batch
            for symbol in batch:
                try:
                    if self.fetch_stock_data(str(symbol)):  # Ensure symbol is a string
                        batch_success += 1
                        total_success += 1
                    else:
                        total_failed += 1
                    time.sleep(1)  # Rate limit between individual symbols (1 second)
                except Exception as e:
                    logger.error(f"Error processing {symbol}: {str(e)}")
                    total_failed += 1
            
            # Calculate time taken for this batch
            batch_time = time.time() - batch_start_time
            logger.info(f"Batch {i//batch_size + 1} complete in {batch_time:.1f} seconds:")
            logger.info(f"  - Success: {batch_success}/{len(batch)}")
            logger.info(f"  - Failed: {len(batch) - batch_success}/{len(batch)}")
            
            # If not the last batch, wait before next batch
            if i + batch_size < total_symbols:
                logger.info(f"Waiting {delay_between_batches} seconds before next batch...")
                time.sleep(delay_between_batches)
        
        # Log final results
        logger.info("\nFetch complete:")
        logger.info(f"Total symbols processed: {total_symbols}")
        logger.info(f"Total successful: {total_success}")
        logger.info(f"Total failed: {total_failed}")
        logger.info(f"Success rate: {(total_success/total_symbols)*100:.1f}%")
        
        return total_success


def main():
    # Example usage
    fetcher = TiingoFetcher()
    
    # Get list of symbols from master_symbols table
    conn = sqlite3.connect(fetcher.db_path)
    try:
        symbols = pd.read_sql('SELECT symbol FROM master_symbols', conn)['symbol'].tolist()
    except Exception as e:
        logger.error(f"Error reading symbols: {str(e)}")
        symbols = []
    finally:
        conn.close()

    if not symbols:
        logger.warning("No symbols found in master_symbols table. Please add some symbols first.")
        return

    # Ask user for mode
    print("\nSelect mode:")
    print("1. Test mode (process first 25 symbols)")
    print("2. Full mode (process all symbols)")
    mode = input("Enter mode (1 or 2): ").strip()
    
    if mode == "1":
        # Test mode: process first 25 symbols
        fetcher.fetch_all_symbols(
            symbols,
            batch_size=25,
            delay_between_batches=15,  # 15 seconds between batches in test mode
            test_mode=True
        )
    else:
        # Full mode: process all symbols
        fetcher.fetch_all_symbols(
            symbols,
            batch_size=25,
            delay_between_batches=30,  # 30 seconds between batches in full mode
            test_mode=False
        )


if __name__ == "__main__":
    main()