#!/usr/bin/env python
# coding: utf-8

"""
Morningstar Data Fetcher
This script fetches financial data from Morningstar's API and stores it in our database.
"""

import requests
import pandas as pd
import sqlite3
from datetime import datetime
import time
import logging
import os
import traceback

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

class MorningstarFetcher:
    def __init__(self, db_path=None):
        self.db_path = db_path or get_db_path()
        self.headers = {
            'apikey': 'lstzFDEOhfFNMLikKa0am9mgEKLBl49T',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36'
        }
        self.base_url = 'https://api-global.morningstar.com/sal-service/v1'
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # Common payload parameters
        self.common_payload = {
            'languageId': 'en',
            'locale': 'en',
            'clientId': 'MDC',
            'version': '3.59.1'
        }
        
        # Create database tables if they don't exist
        self._create_tables()

    def _create_tables(self):
        """Create necessary database tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Create master_symbols table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS master_symbols (
                    symbol TEXT PRIMARY KEY,
                    name TEXT,
                    sector TEXT,
                    industry TEXT,
                    exchange TEXT,
                    country TEXT,
                    currency TEXT,
                    last_updated TEXT
                )
            """)
            
            # Create error_log table
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
            
            # Create table_updates table
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
            
            # Create morningstar tables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS morningstar_valuation (
                    symbol TEXT PRIMARY KEY,
                    pe_ratio REAL,
                    price_to_book REAL,
                    price_to_sales REAL,
                    dividend_yield REAL,
                    last_updated TEXT
                )
            """)
            
            # Drop and recreate the table to ensure correct schema
            cursor.execute("DROP TABLE IF EXISTS morningstar_valuation")
            cursor.execute("""
                CREATE TABLE morningstar_valuation (
                    symbol TEXT PRIMARY KEY,
                    pe_ratio REAL,
                    price_to_book REAL,
                    price_to_sales REAL,
                    dividend_yield REAL,
                    last_updated TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS morningstar_financial_health (
                    symbol TEXT PRIMARY KEY,
                    current_ratio REAL,
                    debt_to_equity REAL,
                    interest_coverage REAL,
                    last_updated TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS morningstar_profitability (
                    symbol TEXT PRIMARY KEY,
                    operating_margin REAL,
                    net_margin REAL,
                    roe REAL,
                    roa REAL,
                    last_updated TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS morningstar_growth (
                    symbol TEXT PRIMARY KEY,
                    revenue_growth REAL,
                    earnings_growth REAL,
                    dividend_growth REAL,
                    last_updated TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS morningstar_cash_flow (
                    symbol TEXT PRIMARY KEY,
                    operating_cash_flow REAL,
                    free_cash_flow REAL,
                    cash_flow_to_debt REAL,
                    last_updated TEXT
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
            
            # 1. Valuation Data
            logger.info(f"Fetching valuation data for {symbol}")
            valuation_data = self._fetch_valuation(symbol)
            if valuation_data:
                logger.info(f"Storing valuation data for {symbol}")
                self._store_valuation(symbol, valuation_data)
            else:
                logger.warning(f"No valuation data available for {symbol}")

            # 2. Financial Health Data
            logger.info(f"Fetching financial health data for {symbol}")
            financial_health = self._fetch_financial_health(symbol)
            if financial_health:
                logger.info(f"Storing financial health data for {symbol}")
                self._store_financial_health(symbol, financial_health)
            else:
                logger.warning(f"No financial health data available for {symbol}")

            # 3. Profitability Data
            logger.info(f"Fetching profitability data for {symbol}")
            profitability = self._fetch_profitability(symbol)
            if profitability:
                logger.info(f"Storing profitability data for {symbol}")
                self._store_profitability(symbol, profitability)
            else:
                logger.warning(f"No profitability data available for {symbol}")

            # 4. Growth Data
            logger.info(f"Fetching growth data for {symbol}")
            growth = self._fetch_growth(symbol)
            if growth:
                logger.info(f"Storing growth data for {symbol}")
                self._store_growth(symbol, growth)
            else:
                logger.warning(f"No growth data available for {symbol}")

            # 5. Cash Flow Data
            logger.info(f"Fetching cash flow data for {symbol}")
            cash_flow = self._fetch_cash_flow(symbol)
            if cash_flow:
                logger.info(f"Storing cash flow data for {symbol}")
                self._store_cash_flow(symbol, cash_flow)
            else:
                logger.warning(f"No cash flow data available for {symbol}")

            logger.info(f"Successfully completed data fetch for {symbol}")
            return True

        except Exception as e:
            self._log_error(
                'morningstar_fetcher',
                symbol,
                'FETCH_ERROR',
                str(e),
                stack_trace=traceback.format_exc(),
                context=f"Failed to fetch data for {symbol}"
            )
            logger.error(f"Error fetching data for {symbol}: {str(e)}")
            return False

    def _fetch_valuation(self, symbol):
        """Fetch valuation metrics"""
        url = f"{self.base_url}/stock/valuation/{symbol}"
        payload = {
            **self.common_payload,
            'component': 'sal-components-mip-valuation'
        }
        response = self.session.get(url, params=payload)
        if response.status_code == 200:
            data = response.json()
            logger.debug(f"Valuation response for {symbol}: {data}")
            if 'data' in data and 'valuation' in data['data']:
                return {
                    'peRatio': data['data']['valuation'].get('peRatio'),
                    'priceToBook': data['data']['valuation'].get('priceToBook'),
                    'priceToSales': data['data']['valuation'].get('priceToSales'),
                    'dividendYield': data['data']['valuation'].get('dividendYield')
                }
            else:
                logger.warning(f"Unexpected valuation data structure for {symbol}: {data}")
        else:
            logger.error(f"Failed to fetch valuation data for {symbol}. Status code: {response.status_code}")
        return None

    def _fetch_financial_health(self, symbol):
        """Fetch financial health metrics"""
        url = f"{self.base_url}/stock/financial-health/{symbol}"
        payload = {
            **self.common_payload,
            'component': 'sal-components-mip-financial-health'
        }
        response = self.session.get(url, params=payload)
        if response.status_code == 200:
            data = response.json()
            logger.debug(f"Financial health response for {symbol}: {data}")
            if 'data' in data and 'financialHealth' in data['data']:
                return {
                    'currentRatio': data['data']['financialHealth'].get('currentRatio'),
                    'debtToEquity': data['data']['financialHealth'].get('debtToEquity'),
                    'interestCoverage': data['data']['financialHealth'].get('interestCoverage')
                }
            else:
                logger.warning(f"Unexpected financial health data structure for {symbol}: {data}")
        else:
            logger.error(f"Failed to fetch financial health data for {symbol}. Status code: {response.status_code}")
        return None

    def _fetch_profitability(self, symbol):
        """Fetch profitability metrics"""
        url = f"{self.base_url}/stock/profitability/{symbol}"
        payload = {
            **self.common_payload,
            'component': 'sal-components-mip-profitability'
        }
        response = self.session.get(url, params=payload)
        if response.status_code == 200:
            data = response.json()
            logger.debug(f"Profitability response for {symbol}: {data}")
            if 'data' in data and 'profitability' in data['data']:
                return {
                    'operatingMargin': data['data']['profitability'].get('operatingMargin'),
                    'netMargin': data['data']['profitability'].get('netMargin'),
                    'returnOnEquity': data['data']['profitability'].get('returnOnEquity'),
                    'returnOnAssets': data['data']['profitability'].get('returnOnAssets')
                }
            else:
                logger.warning(f"Unexpected profitability data structure for {symbol}: {data}")
        else:
            logger.error(f"Failed to fetch profitability data for {symbol}. Status code: {response.status_code}")
        return None

    def _fetch_growth(self, symbol):
        """Fetch growth metrics"""
        url = f"{self.base_url}/stock/growth/{symbol}"
        payload = {
            **self.common_payload,
            'component': 'sal-components-mip-growth'
        }
        response = self.session.get(url, params=payload)
        if response.status_code == 200:
            data = response.json()
            logger.debug(f"Growth response for {symbol}: {data}")
            if 'data' in data and 'growth' in data['data']:
                return {
                    'revenueGrowth': data['data']['growth'].get('revenueGrowth'),
                    'earningsGrowth': data['data']['growth'].get('earningsGrowth'),
                    'dividendGrowth': data['data']['growth'].get('dividendGrowth')
                }
            else:
                logger.warning(f"Unexpected growth data structure for {symbol}: {data}")
        else:
            logger.error(f"Failed to fetch growth data for {symbol}. Status code: {response.status_code}")
        return None

    def _fetch_cash_flow(self, symbol):
        """Fetch cash flow metrics"""
        url = f"{self.base_url}/stock/cash-flow/{symbol}"
        payload = {
            **self.common_payload,
            'component': 'sal-components-mip-cash-flow'
        }
        response = self.session.get(url, params=payload)
        if response.status_code == 200:
            data = response.json()
            logger.debug(f"Cash flow response for {symbol}: {data}")
            if 'data' in data and 'cashFlow' in data['data']:
                return {
                    'operatingCashFlow': data['data']['cashFlow'].get('operatingCashFlow'),
                    'freeCashFlow': data['data']['cashFlow'].get('freeCashFlow'),
                    'cashFlowToDebt': data['data']['cashFlow'].get('cashFlowToDebt')
                }
            else:
                logger.warning(f"Unexpected cash flow data structure for {symbol}: {data}")
        else:
            logger.error(f"Failed to fetch cash flow data for {symbol}. Status code: {response.status_code}")
        return None

    def _store_valuation(self, symbol, data):
        """Store valuation data"""
        if not data:
            logger.warning(f"No valuation data to store for {symbol}")
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            logger.info(f"Storing valuation data for {symbol}: {data}")
            cursor.execute("""
                INSERT OR REPLACE INTO morningstar_valuation (
                    symbol, pe_ratio, price_to_book, price_to_sales,
                    dividend_yield, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                symbol,
                data.get('peRatio'),
                data.get('priceToBook'),
                data.get('priceToSales'),
                data.get('dividendYield'),
                datetime.now().isoformat()
            ))
            conn.commit()
            logger.info(f"Successfully stored valuation data for {symbol}")
            self._log_table_update(
                'morningstar_valuation',
                'INSERT_OR_REPLACE',
                symbol,
                1,
                'SUCCESS',
                f"Updated valuation data for {symbol}"
            )
        except Exception as e:
            logger.error(f"Error storing valuation data for {symbol}: {str(e)}")
            self._log_error(
                'morningstar_valuation',
                symbol,
                'DATABASE_ERROR',
                str(e),
                context=f"Failed to store valuation data for {symbol}"
            )
            raise
        finally:
            conn.close()

    def _store_financial_health(self, symbol, data):
        """Store financial health data"""
        if not data:
            logger.warning(f"No financial health data to store for {symbol}")
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            logger.info(f"Storing financial health data for {symbol}: {data}")
            cursor.execute("""
                INSERT OR REPLACE INTO morningstar_financial_health (
                    symbol, current_ratio, debt_to_equity, interest_coverage,
                    last_updated
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                symbol,
                data.get('currentRatio'),
                data.get('debtToEquity'),
                data.get('interestCoverage'),
                datetime.now().isoformat()
            ))
            conn.commit()
            logger.info(f"Successfully stored financial health data for {symbol}")
            self._log_table_update(
                'morningstar_financial_health',
                'INSERT_OR_REPLACE',
                symbol,
                1,
                'SUCCESS',
                f"Updated financial health data for {symbol}"
            )
        except Exception as e:
            logger.error(f"Error storing financial health data for {symbol}: {str(e)}")
            self._log_error(
                'morningstar_financial_health',
                symbol,
                'DATABASE_ERROR',
                str(e),
                context=f"Failed to store financial health data for {symbol}"
            )
            raise
        finally:
            conn.close()

    def _store_profitability(self, symbol, data):
        """Store profitability data"""
        if not data:
            logger.warning(f"No profitability data to store for {symbol}")
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            logger.info(f"Storing profitability data for {symbol}: {data}")
            cursor.execute("""
                INSERT OR REPLACE INTO morningstar_profitability (
                    symbol, operating_margin, net_margin, roe, roa,
                    last_updated
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                symbol,
                data.get('operatingMargin'),
                data.get('netMargin'),
                data.get('returnOnEquity'),
                data.get('returnOnAssets'),
                datetime.now().isoformat()
            ))
            conn.commit()
            logger.info(f"Successfully stored profitability data for {symbol}")
            self._log_table_update(
                'morningstar_profitability',
                'INSERT_OR_REPLACE',
                symbol,
                1,
                'SUCCESS',
                f"Updated profitability data for {symbol}"
            )
        except Exception as e:
            logger.error(f"Error storing profitability data for {symbol}: {str(e)}")
            self._log_error(
                'morningstar_profitability',
                symbol,
                'DATABASE_ERROR',
                str(e),
                context=f"Failed to store profitability data for {symbol}"
            )
            raise
        finally:
            conn.close()

    def _store_growth(self, symbol, data):
        """Store growth data"""
        if not data:
            logger.warning(f"No growth data to store for {symbol}")
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            logger.info(f"Storing growth data for {symbol}: {data}")
            cursor.execute("""
                INSERT OR REPLACE INTO morningstar_growth (
                    symbol, revenue_growth, earnings_growth, dividend_growth,
                    last_updated
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                symbol,
                data.get('revenueGrowth'),
                data.get('earningsGrowth'),
                data.get('dividendGrowth'),
                datetime.now().isoformat()
            ))
            conn.commit()
            logger.info(f"Successfully stored growth data for {symbol}")
            self._log_table_update(
                'morningstar_growth',
                'INSERT_OR_REPLACE',
                symbol,
                1,
                'SUCCESS',
                f"Updated growth data for {symbol}"
            )
        except Exception as e:
            logger.error(f"Error storing growth data for {symbol}: {str(e)}")
            self._log_error(
                'morningstar_growth',
                symbol,
                'DATABASE_ERROR',
                str(e),
                context=f"Failed to store growth data for {symbol}"
            )
            raise
        finally:
            conn.close()

    def _store_cash_flow(self, symbol, data):
        """Store cash flow data"""
        if not data:
            logger.warning(f"No cash flow data to store for {symbol}")
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            logger.info(f"Storing cash flow data for {symbol}: {data}")
            cursor.execute("""
                INSERT OR REPLACE INTO morningstar_cash_flow (
                    symbol, operating_cash_flow, free_cash_flow, cash_flow_to_debt,
                    last_updated
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                symbol,
                data.get('operatingCashFlow'),
                data.get('freeCashFlow'),
                data.get('cashFlowToDebt'),
                datetime.now().isoformat()
            ))
            conn.commit()
            logger.info(f"Successfully stored cash flow data for {symbol}")
            self._log_table_update(
                'morningstar_cash_flow',
                'INSERT_OR_REPLACE',
                symbol,
                1,
                'SUCCESS',
                f"Updated cash flow data for {symbol}"
            )
        except Exception as e:
            logger.error(f"Error storing cash flow data for {symbol}: {str(e)}")
            self._log_error(
                'morningstar_cash_flow',
                symbol,
                'DATABASE_ERROR',
                str(e),
                context=f"Failed to store cash flow data for {symbol}"
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
    fetcher = MorningstarFetcher()
    
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
 