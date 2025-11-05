#!/usr/bin/env python
# coding: utf-8

"""
Twelve Data Fetcher
This script fetches financial data from Twelve Data's API and stores it in our database.
"""

import requests
import pandas as pd
import sqlite3
from datetime import datetime
import time
import logging
import os
import traceback
from twelvedata import TDClient

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

class TwelveDataFetcher:
    def __init__(self, db_path=None):
        self.db_path = db_path or get_db_path()
        self.api_key = 'e5e916077f07497ba58ab8b38a622003'
        self.client = TDClient(apikey=self.api_key)
        
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
            
            # Verify error_log table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='error_log'")
            if not cursor.fetchone():
                raise Exception("Failed to create error_log table")
            
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
            
            # Verify table_updates table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='table_updates'")
            if not cursor.fetchone():
                raise Exception("Failed to create table_updates table")
            
            # Create twelvedata tables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS twelvedata_profile (
                    symbol TEXT PRIMARY KEY,
                    name TEXT,
                    exchange TEXT,
                    country TEXT,
                    type TEXT,
                    currency TEXT,
                    last_updated TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS twelvedata_statistics (
                    symbol TEXT PRIMARY KEY,
                    market_cap REAL,
                    pe_ratio REAL,
                    eps REAL,
                    dividend_yield REAL,
                    beta REAL,
                    last_updated TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS twelvedata_income_statement (
                    symbol TEXT,
                    period TEXT,
                    revenue REAL,
                    gross_profit REAL,
                    operating_income REAL,
                    net_income REAL,
                    eps REAL,
                    date TEXT,
                    last_updated TEXT,
                    PRIMARY KEY (symbol, period)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS twelvedata_balance_sheet (
                    symbol TEXT,
                    period TEXT,
                    total_assets REAL,
                    total_liabilities REAL,
                    total_equity REAL,
                    current_ratio REAL,
                    debt_to_equity REAL,
                    date TEXT,
                    last_updated TEXT,
                    PRIMARY KEY (symbol, period)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS twelvedata_cash_flow (
                    symbol TEXT,
                    period TEXT,
                    operating_cash_flow REAL,
                    investing_cash_flow REAL,
                    financing_cash_flow REAL,
                    free_cash_flow REAL,
                    date TEXT,
                    last_updated TEXT,
                    PRIMARY KEY (symbol, period)
                )
            """)
            
            conn.commit()
            logger.info("Database tables created successfully")
            
            # Log a test error to verify error logging works
            self._log_error(
                'system',
                'SYSTEM',
                'TEST',
                'Test error log entry',
                context='Verifying error logging functionality'
            )
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error creating tables: {str(e)}")
            raise
        finally:
            conn.close()

    def _log_error(self, source, symbol, error_type, error_message, stack_trace=None, context=None):
        """Log an error to the error_log table"""
        logger.debug(f"Attempting to log error: source={source}, symbol={symbol}, type={error_type}")
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
            logger.debug(f"Successfully logged error for {symbol}")
        except Exception as e:
            logger.error(f"Failed to log error to database: {str(e)}")
            logger.error(f"Error details - source: {source}, symbol: {symbol}, type: {error_type}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
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
            
            # Set the symbol on the client
            self.client.symbol = symbol
            
            # 1. Profile Data
            logger.info(f"Fetching profile data for {symbol}")
            profile = self._fetch_profile(symbol)
            if profile:
                logger.info(f"Storing profile data for {symbol}")
                self._store_profile(symbol, profile)
            else:
                logger.warning(f"No profile data available for {symbol}")

            # 2. Statistics Data
            logger.info(f"Fetching statistics data for {symbol}")
            statistics = self._fetch_statistics(symbol)
            if statistics:
                logger.info(f"Storing statistics data for {symbol}")
                self._store_statistics(symbol, statistics)
            else:
                logger.warning(f"No statistics data available for {symbol}")

            # 3. Income Statement
            logger.info(f"Fetching income statement for {symbol}")
            income = self._fetch_income_statement(symbol)
            if income:
                logger.info(f"Storing income statement for {symbol}")
                self._store_income_statement(symbol, income)
            else:
                logger.warning(f"No income statement available for {symbol}")

            # 4. Balance Sheet
            logger.info(f"Fetching balance sheet for {symbol}")
            balance = self._fetch_balance_sheet(symbol)
            if balance:
                logger.info(f"Storing balance sheet for {symbol}")
                self._store_balance_sheet(symbol, balance)
            else:
                logger.warning(f"No balance sheet available for {symbol}")

            # 5. Cash Flow
            logger.info(f"Fetching cash flow for {symbol}")
            cash_flow = self._fetch_cash_flow(symbol)
            if cash_flow:
                logger.info(f"Storing cash flow for {symbol}")
                self._store_cash_flow(symbol, cash_flow)
            else:
                logger.warning(f"No cash flow available for {symbol}")

            logger.info(f"Successfully completed data fetch for {symbol}")
            return True

        except Exception as e:
            self._log_error(
                'twelvedata_fetcher',
                symbol,
                'FETCH_ERROR',
                str(e),
                stack_trace=traceback.format_exc(),
                context=f"Failed to fetch data for {symbol}"
            )
            logger.error(f"Error fetching data for {symbol}: {str(e)}")
            return False

    def _fetch_profile(self, symbol):
        """Fetch stock profile data"""
        try:
            # Use the profile endpoint directly
            profile = self.client.get_profile().as_json()
            logger.debug(f"Profile response for {symbol}: {profile}")
            return profile
        except requests.exceptions.HTTPError as e:
            error_type = 'RATE_LIMIT' if e.response.status_code == 429 else 'HTTP_ERROR'
            error_msg = f"HTTP Error {e.response.status_code} for {symbol}: {e.response.text}"
            logger.error(error_msg)
            self._log_error(
                'twelvedata_profile',
                symbol,
                error_type,
                str(e),
                stack_trace=traceback.format_exc(),
                context=error_msg
            )
            return None
        except requests.exceptions.Timeout as e:
            error_msg = f"Timeout while fetching profile for {symbol}"
            logger.error(error_msg)
            self._log_error(
                'twelvedata_profile',
                symbol,
                'TIMEOUT',
                str(e),
                stack_trace=traceback.format_exc(),
                context=error_msg
            )
            return None
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error while fetching profile for {symbol}: {str(e)}"
            logger.error(error_msg)
            self._log_error(
                'twelvedata_profile',
                symbol,
                'REQUEST_ERROR',
                str(e),
                stack_trace=traceback.format_exc(),
                context=error_msg
            )
            return None
        except Exception as e:
            error_msg = f"Failed to fetch profile for {symbol}: {str(e)}"
            logger.error(error_msg)
            self._log_error(
                'twelvedata_profile',
                symbol,
                'UNKNOWN_ERROR',
                str(e),
                stack_trace=traceback.format_exc(),
                context=error_msg
            )
            return None

    def _fetch_statistics(self, symbol):
        """Fetch stock statistics"""
        try:
            # Use the statistics endpoint directly
            stats = self.client.get_statistics().as_json()
            logger.debug(f"Statistics response for {symbol}: {stats}")
            return stats
        except requests.exceptions.HTTPError as e:
            error_type = 'RATE_LIMIT' if e.response.status_code == 429 else 'HTTP_ERROR'
            error_msg = f"HTTP Error {e.response.status_code} for {symbol}: {e.response.text}"
            logger.error(error_msg)
            self._log_error(
                'twelvedata_statistics',
                symbol,
                error_type,
                str(e),
                stack_trace=traceback.format_exc(),
                context=error_msg
            )
            return None
        except requests.exceptions.Timeout as e:
            error_msg = f"Timeout while fetching statistics for {symbol}"
            logger.error(error_msg)
            self._log_error(
                'twelvedata_statistics',
                symbol,
                'TIMEOUT',
                str(e),
                stack_trace=traceback.format_exc(),
                context=error_msg
            )
            return None
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error while fetching statistics for {symbol}: {str(e)}"
            logger.error(error_msg)
            self._log_error(
                'twelvedata_statistics',
                symbol,
                'REQUEST_ERROR',
                str(e),
                stack_trace=traceback.format_exc(),
                context=error_msg
            )
            return None
        except Exception as e:
            error_msg = f"Failed to fetch statistics for {symbol}: {str(e)}"
            logger.error(error_msg)
            self._log_error(
                'twelvedata_statistics',
                symbol,
                'UNKNOWN_ERROR',
                str(e),
                stack_trace=traceback.format_exc(),
                context=error_msg
            )
            return None

    def _fetch_income_statement(self, symbol):
        """Fetch income statement data"""
        try:
            # Get last 4 quarters of income statements
            end_date = datetime.now()
            start_date = end_date.replace(month=max(1, end_date.month-12))  # Ensure month is valid
            
            # Use the income statement endpoint directly
            income = self.client.get_income_statement(
                period="quarter",
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d')
            ).as_json()
            logger.debug(f"Income statement response for {symbol}: {income}")
            return income
        except requests.exceptions.HTTPError as e:
            error_type = 'RATE_LIMIT' if e.response.status_code == 429 else 'HTTP_ERROR'
            error_msg = f"HTTP Error {e.response.status_code} for {symbol}: {e.response.text}"
            logger.error(error_msg)
            self._log_error(
                'twelvedata_income_statement',
                symbol,
                error_type,
                str(e),
                stack_trace=traceback.format_exc(),
                context=error_msg
            )
            return None
        except requests.exceptions.Timeout as e:
            error_msg = f"Timeout while fetching income statement for {symbol}"
            logger.error(error_msg)
            self._log_error(
                'twelvedata_income_statement',
                symbol,
                'TIMEOUT',
                str(e),
                stack_trace=traceback.format_exc(),
                context=error_msg
            )
            return None
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error while fetching income statement for {symbol}: {str(e)}"
            logger.error(error_msg)
            self._log_error(
                'twelvedata_income_statement',
                symbol,
                'REQUEST_ERROR',
                str(e),
                stack_trace=traceback.format_exc(),
                context=error_msg
            )
            return None
        except Exception as e:
            error_msg = f"Failed to fetch income statement for {symbol}: {str(e)}"
            logger.error(error_msg)
            self._log_error(
                'twelvedata_income_statement',
                symbol,
                'UNKNOWN_ERROR',
                str(e),
                stack_trace=traceback.format_exc(),
                context=error_msg
            )
            return None

    def _fetch_balance_sheet(self, symbol):
        """Fetch balance sheet data"""
        try:
            # Get last 4 quarters of balance sheets
            end_date = datetime.now()
            start_date = end_date.replace(month=max(1, end_date.month-12))  # Ensure month is valid
            
            # Use the balance sheet endpoint directly
            balance = self.client.get_balance_sheet(
                period="quarter",
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d')
            ).as_json()
            logger.debug(f"Balance sheet response for {symbol}: {balance}")
            return balance
        except requests.exceptions.HTTPError as e:
            error_type = 'RATE_LIMIT' if e.response.status_code == 429 else 'HTTP_ERROR'
            error_msg = f"HTTP Error {e.response.status_code} for {symbol}: {e.response.text}"
            logger.error(error_msg)
            self._log_error(
                'twelvedata_balance_sheet',
                symbol,
                error_type,
                str(e),
                stack_trace=traceback.format_exc(),
                context=error_msg
            )
            return None
        except requests.exceptions.Timeout as e:
            error_msg = f"Timeout while fetching balance sheet for {symbol}"
            logger.error(error_msg)
            self._log_error(
                'twelvedata_balance_sheet',
                symbol,
                'TIMEOUT',
                str(e),
                stack_trace=traceback.format_exc(),
                context=error_msg
            )
            return None
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error while fetching balance sheet for {symbol}: {str(e)}"
            logger.error(error_msg)
            self._log_error(
                'twelvedata_balance_sheet',
                symbol,
                'REQUEST_ERROR',
                str(e),
                stack_trace=traceback.format_exc(),
                context=error_msg
            )
            return None
        except Exception as e:
            error_msg = f"Failed to fetch balance sheet for {symbol}: {str(e)}"
            logger.error(error_msg)
            self._log_error(
                'twelvedata_balance_sheet',
                symbol,
                'UNKNOWN_ERROR',
                str(e),
                stack_trace=traceback.format_exc(),
                context=error_msg
            )
            return None

    def _fetch_cash_flow(self, symbol):
        """Fetch cash flow data"""
        try:
            # Get last 4 quarters of cash flows
            end_date = datetime.now()
            start_date = end_date.replace(month=max(1, end_date.month-12))  # Ensure month is valid
            
            # Use the cash flow endpoint directly
            cash_flow = self.client.get_cash_flow(
                period="quarter",
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d')
            ).as_json()
            logger.debug(f"Cash flow response for {symbol}: {cash_flow}")
            return cash_flow
        except requests.exceptions.HTTPError as e:
            error_type = 'RATE_LIMIT' if e.response.status_code == 429 else 'HTTP_ERROR'
            error_msg = f"HTTP Error {e.response.status_code} for {symbol}: {e.response.text}"
            logger.error(error_msg)
            self._log_error(
                'twelvedata_cash_flow',
                symbol,
                error_type,
                str(e),
                stack_trace=traceback.format_exc(),
                context=error_msg
            )
            return None
        except requests.exceptions.Timeout as e:
            error_msg = f"Timeout while fetching cash flow for {symbol}"
            logger.error(error_msg)
            self._log_error(
                'twelvedata_cash_flow',
                symbol,
                'TIMEOUT',
                str(e),
                stack_trace=traceback.format_exc(),
                context=error_msg
            )
            return None
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error while fetching cash flow for {symbol}: {str(e)}"
            logger.error(error_msg)
            self._log_error(
                'twelvedata_cash_flow',
                symbol,
                'REQUEST_ERROR',
                str(e),
                stack_trace=traceback.format_exc(),
                context=error_msg
            )
            return None
        except Exception as e:
            error_msg = f"Failed to fetch cash flow for {symbol}: {str(e)}"
            logger.error(error_msg)
            self._log_error(
                'twelvedata_cash_flow',
                symbol,
                'UNKNOWN_ERROR',
                str(e),
                stack_trace=traceback.format_exc(),
                context=error_msg
            )
            return None

    def _store_profile(self, symbol, data):
        """Store profile data"""
        if not data:
            logger.warning(f"No profile data to store for {symbol}")
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            logger.info(f"Storing profile data for {symbol}: {data}")
            cursor.execute("""
                INSERT OR REPLACE INTO twelvedata_profile (
                    symbol, name, exchange, country, type, currency, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol,
                data.get('name'),
                data.get('exchange'),
                data.get('country'),
                data.get('type'),
                data.get('currency'),
                datetime.now().isoformat()
            ))
            conn.commit()
            logger.info(f"Successfully stored profile data for {symbol}")
            self._log_table_update(
                'twelvedata_profile',
                'INSERT_OR_REPLACE',
                symbol,
                1,
                'SUCCESS',
                f"Updated profile data for {symbol}"
            )
        except Exception as e:
            logger.error(f"Error storing profile data for {symbol}: {str(e)}")
            self._log_error(
                'twelvedata_profile',
                symbol,
                'DATABASE_ERROR',
                str(e),
                context=f"Failed to store profile data for {symbol}"
            )
            raise
        finally:
            conn.close()

    def _store_statistics(self, symbol, data):
        """Store statistics data"""
        if not data:
            logger.warning(f"No statistics data to store for {symbol}")
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            logger.info(f"Storing statistics data for {symbol}: {data}")
            cursor.execute("""
                INSERT OR REPLACE INTO twelvedata_statistics (
                    symbol, market_cap, pe_ratio, eps, dividend_yield, beta, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol,
                data.get('market_cap'),
                data.get('pe_ratio'),
                data.get('eps'),
                data.get('dividend_yield'),
                data.get('beta'),
                datetime.now().isoformat()
            ))
            conn.commit()
            logger.info(f"Successfully stored statistics data for {symbol}")
            self._log_table_update(
                'twelvedata_statistics',
                'INSERT_OR_REPLACE',
                symbol,
                1,
                'SUCCESS',
                f"Updated statistics data for {symbol}"
            )
        except Exception as e:
            logger.error(f"Error storing statistics data for {symbol}: {str(e)}")
            self._log_error(
                'twelvedata_statistics',
                symbol,
                'DATABASE_ERROR',
                str(e),
                context=f"Failed to store statistics data for {symbol}"
            )
            raise
        finally:
            conn.close()

    def _store_income_statement(self, symbol, data):
        """Store income statement data"""
        if not data:
            logger.warning(f"No income statement data to store for {symbol}")
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            logger.info(f"Storing income statement data for {symbol}: {data}")
            rows_affected = 0
            
            for period_data in data:
                cursor.execute("""
                    INSERT OR REPLACE INTO twelvedata_income_statement (
                        symbol, period, revenue, gross_profit, operating_income,
                        net_income, eps, date, last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    symbol,
                    period_data.get('period'),
                    period_data.get('revenue'),
                    period_data.get('gross_profit'),
                    period_data.get('operating_income'),
                    period_data.get('net_income'),
                    period_data.get('eps'),
                    period_data.get('date'),
                    datetime.now().isoformat()
                ))
                rows_affected += 1
            
            conn.commit()
            logger.info(f"Successfully stored income statement data for {symbol}")
            self._log_table_update(
                'twelvedata_income_statement',
                'INSERT_OR_REPLACE',
                symbol,
                rows_affected,
                'SUCCESS',
                f"Updated {rows_affected} income statement records for {symbol}"
            )
        except Exception as e:
            logger.error(f"Error storing income statement data for {symbol}: {str(e)}")
            self._log_error(
                'twelvedata_income_statement',
                symbol,
                'DATABASE_ERROR',
                str(e),
                context=f"Failed to store income statement data for {symbol}"
            )
            raise
        finally:
            conn.close()

    def _store_balance_sheet(self, symbol, data):
        """Store balance sheet data"""
        if not data:
            logger.warning(f"No balance sheet data to store for {symbol}")
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            logger.info(f"Storing balance sheet data for {symbol}: {data}")
            rows_affected = 0
            
            for period_data in data:
                cursor.execute("""
                    INSERT OR REPLACE INTO twelvedata_balance_sheet (
                        symbol, period, total_assets, total_liabilities,
                        total_equity, current_ratio, debt_to_equity, date, last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    symbol,
                    period_data.get('period'),
                    period_data.get('total_assets'),
                    period_data.get('total_liabilities'),
                    period_data.get('total_equity'),
                    period_data.get('current_ratio'),
                    period_data.get('debt_to_equity'),
                    period_data.get('date'),
                    datetime.now().isoformat()
                ))
                rows_affected += 1
            
            conn.commit()
            logger.info(f"Successfully stored balance sheet data for {symbol}")
            self._log_table_update(
                'twelvedata_balance_sheet',
                'INSERT_OR_REPLACE',
                symbol,
                rows_affected,
                'SUCCESS',
                f"Updated {rows_affected} balance sheet records for {symbol}"
            )
        except Exception as e:
            logger.error(f"Error storing balance sheet data for {symbol}: {str(e)}")
            self._log_error(
                'twelvedata_balance_sheet',
                symbol,
                'DATABASE_ERROR',
                str(e),
                context=f"Failed to store balance sheet data for {symbol}"
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
            rows_affected = 0
            
            for period_data in data:
                cursor.execute("""
                    INSERT OR REPLACE INTO twelvedata_cash_flow (
                        symbol, period, operating_cash_flow, investing_cash_flow,
                        financing_cash_flow, free_cash_flow, date, last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    symbol,
                    period_data.get('period'),
                    period_data.get('operating_cash_flow'),
                    period_data.get('investing_cash_flow'),
                    period_data.get('financing_cash_flow'),
                    period_data.get('free_cash_flow'),
                    period_data.get('date'),
                    datetime.now().isoformat()
                ))
                rows_affected += 1
            
            conn.commit()
            logger.info(f"Successfully stored cash flow data for {symbol}")
            self._log_table_update(
                'twelvedata_cash_flow',
                'INSERT_OR_REPLACE',
                symbol,
                rows_affected,
                'SUCCESS',
                f"Updated {rows_affected} cash flow records for {symbol}"
            )
        except Exception as e:
            logger.error(f"Error storing cash flow data for {symbol}: {str(e)}")
            self._log_error(
                'twelvedata_cash_flow',
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
    fetcher = TwelveDataFetcher()
    
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