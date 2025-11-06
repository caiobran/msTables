import os
import logging
import requests
import pandas as pd
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from ..database import get_db_path

logger = logging.getLogger(__name__)

class AlphaVantageFetcher:
    """
    Class for interacting with Alpha Vantage API and managing stock data.

    Attributes
    ----------
    api_key : str
        Alpha Vantage API key
    db_path : str
        Path to the SQLite database
    """

    def __init__(self, db_path=None):
        """
        Initialize the AlphaVantageFetcher instance.

        Parameters
        ----------
        db_path : str, optional
            Path to the SQLite database. If None, uses the default path.
        """
        load_dotenv()
        self.api_key = os.getenv('ALPHAVANTAGE_API_KEY')
        self.db_path = db_path or get_db_path()

        if not self.api_key:
            logger.warning("No Alpha Vantage API key provided or found in environment variables")

        logger.info(f"AlphaVantageFetcher initialized with database path: {self.db_path}")
        
        # Create database tables if they don't exist
        self._create_tables()

    def _create_tables(self):
        """Create necessary database tables if they don't exist."""
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
            
            # Create alphavantage tables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alphavantage_intraday (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT,
                    date TEXT,
                    time TEXT,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume INTEGER,
                    last_updated TEXT,
                    UNIQUE(symbol, date, time)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alphavantage_daily (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT,
                    date TEXT,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume INTEGER,
                    last_updated TEXT,
                    UNIQUE(symbol, date)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alphavantage_fundamentals (
                    symbol TEXT PRIMARY KEY,
                    name TEXT,
                    description TEXT,
                    exchange TEXT,
                    currency TEXT,
                    sector TEXT,
                    industry TEXT,
                    market_cap REAL,
                    pe_ratio REAL,
                    eps REAL,
                    dividend_yield REAL,
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
        """Log an error to the error_log table."""
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
        """Log a table update to the table_updates table."""
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

    def fetch_all_symbols(self, symbols, batch_size=25, delay_between_batches=30, test_mode=False):
        """
        Fetch data for all symbols in batches.

        Parameters
        ----------
        symbols : list
            List of stock symbols to fetch
        batch_size : int, optional
            Number of symbols to process in each batch
        delay_between_batches : int, optional
            Delay in seconds between batches
        test_mode : bool, optional
            If True, only process first batch

        Returns
        -------
        int
            Number of successfully processed symbols
        """
        success_count = 0
        total_symbols = len(symbols)
        
        for i in range(0, total_symbols, batch_size):
            batch = symbols[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1} of {(total_symbols + batch_size - 1)//batch_size}")
            
            for symbol in batch:
                try:
                    # Fetch and store data
                    self._fetch_and_store_data(symbol)
                    success_count += 1
                    logger.info(f"Successfully processed {symbol}")
                except Exception as e:
                    error_msg = f"Error processing {symbol}: {str(e)}"
                    logger.error(error_msg)
                    self._log_error(
                        'alphavantage',
                        symbol,
                        'FETCH_ERROR',
                        error_msg,
                        context=f"Batch {i//batch_size + 1}"
                    )
            
            if test_mode and i + batch_size >= batch_size:
                logger.info("Test mode: stopping after first batch")
                break
                
            if i + batch_size < total_symbols:
                logger.info(f"Waiting {delay_between_batches} seconds before next batch...")
                time.sleep(delay_between_batches)
        
        return success_count

    def _fetch_and_store_data(self, symbol):
        """
        Fetch and store all available data for a symbol.

        Parameters
        ----------
        symbol : str
            Stock symbol to fetch data for
        """
        # Fetch intraday data
        intraday_data = self._fetch_intraday(symbol)
        if intraday_data is not None:
            self._store_intraday(symbol, intraday_data)
        
        # Fetch daily data
        daily_data = self._fetch_daily(symbol)
        if daily_data is not None:
            self._store_daily(symbol, daily_data)
        
        # Fetch fundamental data
        fundamental_data = self._fetch_fundamentals(symbol)
        if fundamental_data is not None:
            self._store_fundamentals(symbol, fundamental_data)

    def _fetch_intraday(self, symbol, interval='5min'):
        """
        Fetch intraday time series data.

        Parameters
        ----------
        symbol : str
            Stock symbol
        interval : str, optional
            Time interval between data points

        Returns
        -------
        pandas.DataFrame or None
            DataFrame containing intraday data or None if fetch fails
        """
        url = f'https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={symbol}&interval={interval}&apikey={self.api_key}'
        
        try:
            response = requests.get(url)
            data = response.json()
            
            if "Error Message" in data:
                raise ValueError(data['Error Message'])
            
            time_series_key = f'Time Series ({interval})'
            if time_series_key not in data:
                raise ValueError("Unexpected data format received from API")
            
            df = pd.DataFrame.from_dict(data[time_series_key], orient='index')
            df.index = pd.to_datetime(df.index)
            df = df.rename(columns=lambda x: x.split(' ')[1])
            
            df['symbol'] = symbol
            df['date'] = df.index.date.astype(str)
            df['time'] = df.index.time.astype(str)
            df = df.reset_index(drop=True)
            
            return df[['symbol', 'date', 'time', 'open', 'high', 'low', 'close', 'volume']]
            
        except Exception as e:
            self._log_error(
                'alphavantage',
                symbol,
                'INTRADAY_FETCH_ERROR',
                str(e),
                context=f"Interval: {interval}"
            )
            return None

    def _fetch_daily(self, symbol):
        """
        Fetch daily time series data.

        Parameters
        ----------
        symbol : str
            Stock symbol

        Returns
        -------
        pandas.DataFrame or None
            DataFrame containing daily data or None if fetch fails
        """
        url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={self.api_key}'
        
        try:
            response = requests.get(url)
            data = response.json()
            
            if "Error Message" in data:
                raise ValueError(data['Error Message'])
            
            if 'Time Series (Daily)' not in data:
                raise ValueError("Unexpected data format received from API")
            
            df = pd.DataFrame.from_dict(data['Time Series (Daily)'], orient='index')
            df.index = pd.to_datetime(df.index)
            df = df.rename(columns=lambda x: x.split(' ')[1])
            
            df['symbol'] = symbol
            df['date'] = df.index.date.astype(str)
            df = df.reset_index(drop=True)
            
            return df[['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']]
            
        except Exception as e:
            self._log_error(
                'alphavantage',
                symbol,
                'DAILY_FETCH_ERROR',
                str(e)
            )
            return None

    def _fetch_fundamentals(self, symbol):
        """
        Fetch fundamental data.

        Parameters
        ----------
        symbol : str
            Stock symbol

        Returns
        -------
        dict or None
            Dictionary containing fundamental data or None if fetch fails
        """
        url = f'https://www.alphavantage.co/query?function=OVERVIEW&symbol={symbol}&apikey={self.api_key}'
        
        try:
            response = requests.get(url)
            data = response.json()
            
            if "Error Message" in data:
                raise ValueError(data['Error Message'])
            
            if not data:
                raise ValueError("No data received from API")
            
            return data
            
        except Exception as e:
            self._log_error(
                'alphavantage',
                symbol,
                'FUNDAMENTALS_FETCH_ERROR',
                str(e)
            )
            return None

    def _store_intraday(self, symbol, df):
        """
        Store intraday data in the database.

        Parameters
        ----------
        symbol : str
            Stock symbol
        df : pandas.DataFrame
            DataFrame containing intraday data
        """
        if df.empty:
            return
        
        conn = sqlite3.connect(self.db_path)
        try:
            df['last_updated'] = datetime.now().isoformat()
            df.to_sql('alphavantage_intraday', conn, if_exists='append', index=False)
            self._log_table_update(
                'alphavantage_intraday',
                'INSERT',
                symbol,
                len(df),
                'SUCCESS'
            )
        except Exception as e:
            self._log_error(
                'alphavantage',
                symbol,
                'INTRADAY_STORE_ERROR',
                str(e)
            )
        finally:
            conn.close()

    def _store_daily(self, symbol, df):
        """
        Store daily data in the database.

        Parameters
        ----------
        symbol : str
            Stock symbol
        df : pandas.DataFrame
            DataFrame containing daily data
        """
        if df.empty:
            return
        
        conn = sqlite3.connect(self.db_path)
        try:
            df['last_updated'] = datetime.now().isoformat()
            df.to_sql('alphavantage_daily', conn, if_exists='append', index=False)
            self._log_table_update(
                'alphavantage_daily',
                'INSERT',
                symbol,
                len(df),
                'SUCCESS'
            )
        except Exception as e:
            self._log_error(
                'alphavantage',
                symbol,
                'DAILY_STORE_ERROR',
                str(e)
            )
        finally:
            conn.close()

    def _store_fundamentals(self, symbol, data):
        """
        Store fundamental data in the database.

        Parameters
        ----------
        symbol : str
            Stock symbol
        data : dict
            Dictionary containing fundamental data
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO alphavantage_fundamentals (
                    symbol, name, description, exchange, currency,
                    sector, industry, market_cap, pe_ratio, eps,
                    dividend_yield, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol,
                data.get('Name'),
                data.get('Description'),
                data.get('Exchange'),
                data.get('Currency'),
                data.get('Sector'),
                data.get('Industry'),
                data.get('MarketCapitalization'),
                data.get('PERatio'),
                data.get('EPS'),
                data.get('DividendYield'),
                datetime.now().isoformat()
            ))
            conn.commit()
            self._log_table_update(
                'alphavantage_fundamentals',
                'INSERT',
                symbol,
                1,
                'SUCCESS'
            )
        except Exception as e:
            self._log_error(
                'alphavantage',
                symbol,
                'FUNDAMENTALS_STORE_ERROR',
                str(e)
            )
        finally:
            conn.close() 