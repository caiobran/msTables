"""
Data Shepherd Module

This module provides functionality for identifying and retrieving missing financial data
across multiple asset classes. It works like a trickle charger or microdrip irrigation system,
fetching small batches of missing data over time.

Features:
- Stock data gap detection and filling
- Forex data support
- Cryptocurrency data support
- Bond data support
- Rate-limited API calls
- Database integration
"""

import os
import time
import logging
import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
import requests
from dotenv import load_dotenv
from pathlib import Path
import re

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/logs/data_shepherd.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('DataShepherd')

class DataShepherd:
    """
    A class that shepherds (collects and manages) missing financial data.
    Handles stock data and provides base functionality for other asset classes.
    """

    def __init__(self, db_path=None, batch_size=100):
        """
        Initialize the DataShepherd.

        Parameters
        ----------
        db_path : str, optional
            Path to the SQLite database. If None, uses the path from environment variables.
        batch_size : int, optional
            Number of data points to retrieve in each batch, default is 100.
        """
        load_dotenv()

        self.db_path = db_path or os.getenv('SECURITIES_MASTER_DB', 'data/mstables.sqlite')
        self.batch_size = batch_size
        self.logger = logger

        # Create necessary directories
        Path('data/logs').mkdir(parents=True, exist_ok=True)
        Path('data/csv').mkdir(parents=True, exist_ok=True)
        Path('data/charts').mkdir(parents=True, exist_ok=True)

        self.logger.info(f"DataShepherd initialized with database path: {self.db_path}")

    def _create_connection(self):
        """Create a database connection."""
        try:
            conn = sqlite3.connect(self.db_path)
            return conn
        except sqlite3.Error as e:
            self.logger.error(f"Database connection error: {e}")
            return None

    def find_missing_dates(self, symbol, table_name, start_date=None, end_date=None):
        """Find missing dates in the time series data for a given symbol."""
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d')

        if start_date is None:
            start_date = datetime(2000, 1, 1)
        if end_date is None:
            end_date = datetime.now()

        conn = self._create_connection()
        if conn is None:
            return []

        try:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT date FROM {table_name} WHERE ticker = ? AND date BETWEEN ? AND ?",
                (symbol, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            )

            existing_dates = {datetime.strptime(row[0], '%Y-%m-%d').date() for row in cursor.fetchall()}

            all_dates = []
            current_date = start_date.date()
            while current_date <= end_date.date():
                if current_date.weekday() < 5:  # Only include weekdays
                    all_dates.append(current_date)
                current_date += timedelta(days=1)

            missing_dates = [date for date in all_dates if date not in existing_dates]
            self.logger.info(f"Found {len(missing_dates)} missing dates for {symbol}")
            return missing_dates

        except sqlite3.Error as e:
            self.logger.error(f"Error finding missing dates: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def fetch_missing_data(self, symbol, start_date=None, end_date=None):
        """Fetch missing data for a specific symbol with rate limiting."""
        max_retries = 5
        retry_count = 0

        if isinstance(start_date, datetime):
            start_date = start_date.strftime('%Y-%m-%d')
        if isinstance(end_date, datetime):
            end_date = end_date.strftime('%Y-%m-%d')

        self.logger.info(f"Fetching data for {symbol} from {start_date} to {end_date}")

        while retry_count <= max_retries:
            try:
                time.sleep(1)  # Basic rate limiting
                df = yf.download(symbol, start=start_date, end=end_date, progress=False)

                if df.empty:
                    self.logger.warning(f"No data found for {symbol} in the specified date range")
                    return pd.DataFrame()

                df = df.reset_index()
                df['ticker'] = symbol
                df = df.rename(columns={
                    'Date': 'date', 'Open': 'open', 'High': 'high',
                    'Low': 'low', 'Close': 'close', 'Volume': 'volume',
                    'Adj Close': 'adj_close'
                })

                return df

            except Exception as e:
                if "Rate limited" in str(e) or "Too Many Requests" in str(e):
                    retry_count += 1
                    time.sleep(2 ** retry_count)  # Exponential backoff
                else:
                    self.logger.error(f"Error fetching data for {symbol}: {e}")
                    return pd.DataFrame()

        return pd.DataFrame()

    def save_to_database(self, df, table_name):
        """Save the DataFrame to the database."""
        if df.empty:
            self.logger.warning("No data to save to database")
            return 0

        conn = self._create_connection()
        if conn is None:
            return 0

        try:
            if pd.api.types.is_datetime64_any_dtype(df['date']):
                df['date'] = df['date'].dt.strftime('%Y-%m-%d')

            rows_before = self._count_rows(conn, table_name)
            df.to_sql(table_name, conn, if_exists='append', index=False)
            rows_after = self._count_rows(conn, table_name)

            rows_inserted = rows_after - rows_before
            self.logger.info(f"Inserted {rows_inserted} rows into {table_name}")
            return rows_inserted

        except sqlite3.Error as e:
            self.logger.error(f"Database error during save: {e}")
            return 0
        finally:
            if conn:
                conn.close()

    def _count_rows(self, conn, table_name):
        """Count rows in a table."""
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            return cursor.fetchone()[0]
        except sqlite3.Error as e:
            self.logger.error(f"Error counting rows: {e}")
            return 0

    def run_daily_shepherd(self, symbols, table_name='stock_data', days_back=30):
        """Run daily data shepherding for multiple symbols."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        for symbol in symbols:
            self.logger.info(f"Processing {symbol}")
            missing_dates = self.find_missing_dates(symbol, table_name, start_date, end_date)

            if missing_dates:
                # Group consecutive dates
                date_groups = self._group_consecutive_dates(missing_dates)
                
                for start, end in date_groups:
                    df = self.fetch_missing_data(symbol, start, end)
                    if not df.empty:
                        self.save_to_database(df, table_name)
                    time.sleep(1)  # Rate limiting between symbols

    def _group_consecutive_dates(self, dates):
        """Group consecutive dates into ranges."""
        if not dates:
            return []

        dates = sorted(dates)
        groups = []
        start = dates[0]
        prev = dates[0]

        for date in dates[1:]:
            if (date - prev).days > 1:
                groups.append((start, prev))
                start = date
            prev = date
        groups.append((start, prev))

        return groups

class ExtendedDataShepherd(DataShepherd):
    """Extended functionality for multiple asset classes."""

    def __init__(self, db_path=None, batch_size=100, alpha_vantage_key=None):
        """Initialize the ExtendedDataShepherd."""
        super().__init__(db_path, batch_size)
        self.alpha_vantage_key = alpha_vantage_key or os.getenv('ALPHA_VANTAGE_KEY')
        if not self.alpha_vantage_key:
            self.logger.warning("No Alpha Vantage API key provided")

    def initialize_database(self):
        """Initialize the database with tables for all asset classes."""
        conn = self._create_connection()
        if conn is None:
            return False

        try:
            cursor = conn.cursor()

            # Stock data table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stock_data (
                    id INTEGER PRIMARY KEY,
                    ticker TEXT NOT NULL,
                    date TEXT NOT NULL,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume INTEGER,
                    adj_close REAL,
                    UNIQUE (ticker, date)
                )
            ''')

            # Forex data table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS forex_data (
                    id INTEGER PRIMARY KEY,
                    pair TEXT NOT NULL,
                    date TEXT NOT NULL,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume INTEGER,
                    base_currency TEXT,
                    quote_currency TEXT,
                    UNIQUE (pair, date)
                )
            ''')

            # Crypto data table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS crypto_data (
                    id INTEGER PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    date TEXT NOT NULL,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume REAL,
                    market_cap REAL,
                    market TEXT,
                    UNIQUE (symbol, date)
                )
            ''')

            # Bond data table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bond_data (
                    id INTEGER PRIMARY KEY,
                    ticker TEXT NOT NULL,
                    date TEXT NOT NULL,
                    price REAL,
                    yield REAL,
                    duration REAL,
                    coupon REAL,
                    maturity_date TEXT,
                    issuer TEXT,
                    rating TEXT,
                    UNIQUE (ticker, date)
                )
            ''')

            # TODO 1.0.0: Add precious metals data table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS precious_metals_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    date TEXT NOT NULL,
                    price_usd REAL,
                    price_eur REAL,
                    price_gbp REAL,
                    price_jpy REAL,
                    volume REAL,
                    market_cap REAL,
                    metal_type TEXT,
                    purity TEXT,
                    unit TEXT,
                    exchange TEXT,
                    source TEXT,
                    timestamp TEXT,
                    UNIQUE (symbol, date)
                )
            ''')

            # TODO 1.0.0: Rename metal_prices to currency_prices and migrate data
            # TODO 1.0.0: Create currency_prices table for actual currency data

            # Fund Portfolio Summary table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS fund_portfolio_summary (
                    id INTEGER PRIMARY KEY,
                    fund_id TEXT NOT NULL,
                    portfolio_date TEXT NOT NULL,
                    equity_holding INTEGER,
                    active_share REAL,
                    reported_turnover REAL,
                    other_holding INTEGER,
                    top_holding REAL,
                    total_assets REAL,
                    net_assets REAL,
                    fetch_date TEXT,
                    last_updated TEXT,
                    UNIQUE (fund_id, portfolio_date)
                )
            ''')

            # Fund Portfolio Holdings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS fund_portfolio_holdings (
                    id INTEGER PRIMARY KEY,
                    fund_id TEXT NOT NULL,
                    portfolio_date TEXT NOT NULL,
                    security_id TEXT NOT NULL,
                    security_name TEXT,
                    security_type TEXT,
                    weight REAL,
                    shares_held INTEGER,
                    market_value REAL,
                    currency TEXT,
                    is_new_position BOOLEAN,
                    is_sold_position BOOLEAN,
                    fetch_date TEXT,
                    last_updated TEXT,
                    UNIQUE (fund_id, portfolio_date, security_id)
                )
            ''')

            # Fund Portfolio Allocation table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS fund_portfolio_allocation (
                    id INTEGER PRIMARY KEY,
                    fund_id TEXT NOT NULL,
                    portfolio_date TEXT NOT NULL,
                    allocation_type TEXT NOT NULL,
                    category TEXT NOT NULL,
                    weight REAL,
                    fetch_date TEXT,
                    last_updated TEXT,
                    UNIQUE (fund_id, portfolio_date, allocation_type, category)
                )
            ''')

            # Create indices for common queries
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_fund_summary_fund_id 
                ON fund_portfolio_summary(fund_id)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_fund_summary_date 
                ON fund_portfolio_summary(portfolio_date)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_fund_holdings_fund_id 
                ON fund_portfolio_holdings(fund_id)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_fund_holdings_date 
                ON fund_portfolio_holdings(portfolio_date)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_fund_holdings_security 
                ON fund_portfolio_holdings(security_id)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_fund_allocation_fund_id 
                ON fund_portfolio_allocation(fund_id)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_fund_allocation_date 
                ON fund_portfolio_allocation(portfolio_date)
            ''')

            # TODO 1.1.0: Add indices for precious_metals_data table
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_metals_symbol 
                ON precious_metals_data(symbol)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_metals_date 
                ON precious_metals_data(date)
            ''')

            conn.commit()
            self.logger.info("Database tables initialized successfully")
            return True

        except sqlite3.Error as e:
            self.logger.error(f"Error initializing database: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def _fetch_from_alpha_vantage(self, function, **params):
        """Fetch data from Alpha Vantage."""
        if not self.alpha_vantage_key:
            self.logger.error("No Alpha Vantage API key available")
            return pd.DataFrame()

        base_url = "https://www.alphavantage.co/query"
        params['function'] = function
        params['apikey'] = self.alpha_vantage_key

        try:
            # TODO 1.1.0: Add proper rate limiting for Alpha Vantage API
            response = requests.get(base_url, params=params)
            data = response.json()

            if 'Error Message' in data:
                self.logger.error(f"Alpha Vantage API error: {data['Error Message']}")
                return pd.DataFrame()

            time_series_key = {
                'FX_DAILY': "Time Series FX (Daily)",
                'DIGITAL_CURRENCY_DAILY': "Time Series (Digital Currency Daily)",
            }.get(function, "Time Series (Daily)")

            if time_series_key in data:
                df = pd.DataFrame.from_dict(data[time_series_key], orient='index')
                df.index = pd.to_datetime(df.index)
                df = df.apply(pd.to_numeric)
                return df
            else:
                self.logger.error(f"Unexpected API response structure: {list(data.keys())}")
                return pd.DataFrame()

        except Exception as e:
            self.logger.error(f"Error fetching data from Alpha Vantage: {e}")
            return pd.DataFrame()

    def fetch_forex_data(self, from_currency, to_currency, start_date=None, end_date=None):
        """Fetch forex data for a specific currency pair."""
        try:
            df = self._fetch_from_alpha_vantage(
                'FX_DAILY',
                from_symbol=from_currency,
                to_symbol=to_currency
            )

            if not df.empty:
                df = self._filter_by_date_range(df, start_date, end_date)
                df['pair'] = f"{from_currency}/{to_currency}"
                df['base_currency'] = from_currency
                df['quote_currency'] = to_currency

            return df

        except Exception as e:
            self.logger.error(f"Error fetching forex data: {e}")
            return pd.DataFrame()

    def fetch_crypto_data(self, symbol, market='USD', start_date=None, end_date=None):
        """Fetch cryptocurrency data."""
        try:
            df = self._fetch_from_alpha_vantage(
                'DIGITAL_CURRENCY_DAILY',
                symbol=symbol,
                market=market
            )

            if not df.empty:
                df = self._filter_by_date_range(df, start_date, end_date)
                df['symbol'] = symbol
                df['market'] = market

            return df

        except Exception as e:
            self.logger.error(f"Error fetching crypto data: {e}")
            return pd.DataFrame()

    def _filter_by_date_range(self, df, start_date=None, end_date=None):
        """Filter DataFrame by date range."""
        if df.empty:
            return df

        if isinstance(start_date, str):
            start_date = pd.to_datetime(start_date)
        if isinstance(end_date, str):
            end_date = pd.to_datetime(end_date)

        if start_date:
            df = df[df.index >= start_date]
        if end_date:
            df = df[df.index <= end_date]

        return df

    def initialize_commodities_table(self):
        """Initialize the commodities data table."""
        conn = self._create_connection()
        if conn is None:
            return False

        try:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS commodities_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT,
                    date TEXT,
                    price REAL,
                    volume REAL,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    commodity_type TEXT,
                    source TEXT,
                    unit TEXT,
                    region TEXT,
                    quality TEXT,
                    commodity TEXT,
                    one_month_change REAL,
                    twelve_month_change REAL,
                    ytd_change REAL,
                    year TEXT,
                    sum_of_value TEXT,
                    market_hogs TEXT,
                    feeder_pigs TEXT,
                    gross_value_of_production TEXT,
                    UNIQUE (symbol, date, commodity_type)
                )
            ''')
            
            # Create indices for common queries
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_commodities_symbol 
                ON commodities_data(symbol)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_commodities_date 
                ON commodities_data(date)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_commodities_type 
                ON commodities_data(commodity_type)
            ''')

            conn.commit()
            self.logger.info("Commodities table initialized successfully")
            return True

        except sqlite3.Error as e:
            self.logger.error(f"Error initializing commodities table: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def import_commodity_file(self, file_path: str, commodity_type: str):
        """
        Import commodity data from various file formats.
        
        Parameters
        ----------
        file_path : str
            Path to the commodity data file
        commodity_type : str
            Type of commodity (e.g., 'agricultural', 'energy', 'metals', 'livestock')
        """
        import pandas as pd
        import sqlite3
        try:
            if file_path.endswith('.csv'):
                if 'Month Change' in file_path:
                    # Handle commodity changes file with irregular whitespace
                    error_rows = []
                    # Read file line by line
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    header = re.split(r'\s{2,}|\t', lines[0].strip())
                    data = []
                    for i, line in enumerate(lines[1:], 2):
                        # Split on 2+ spaces or tabs
                        parts = re.split(r'\s{2,}|\t', line.strip())
                        if len(parts) == 4:
                            data.append(parts)
                        else:
                            error_rows.append({'file': file_path, 'line_number': i, 'raw_line': line.strip(), 'error': f'Expected 4 columns, got {len(parts)}'})
                    df = pd.DataFrame(data, columns=['commodity', 'one_month_change', 'twelve_month_change', 'ytd_change'])
                    # Clean up the data
                    for col in ['one_month_change', 'twelve_month_change', 'ytd_change']:
                        df[col] = df[col].str.replace('%', '').str.strip()
                        df[col] = pd.to_numeric(df[col], errors='coerce') / 100
                    # Add metadata
                    df['commodity_type'] = commodity_type
                    df['date'] = datetime.now().strftime('%Y-%m-%d')
                    df['source'] = 'commodity_changes'
                    df['unit'] = 'percentage'
                    # Categorize commodities
                    df['category'] = df['commodity'].apply(self._categorize_commodity)
                    # Save to database
                    self.save_to_database(df, 'commodities_data')
                    self.logger.info(f"Imported {len(df)} records from {file_path}")
                    # Log errors to commodities_import_errors table
                    if error_rows:
                        conn = self._create_connection()
                        if conn is not None:
                            try:
                                cursor = conn.cursor()
                                cursor.execute('''
                                    CREATE TABLE IF NOT EXISTS commodities_import_errors (
                                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                                        file TEXT,
                                        line_number INTEGER,
                                        raw_line TEXT,
                                        error TEXT,
                                        timestamp TEXT
                                    )
                                ''')
                                for row in error_rows:
                                    cursor.execute('''
                                        INSERT INTO commodities_import_errors (file, line_number, raw_line, error, timestamp)
                                        VALUES (?, ?, ?, ?, ?)
                                    ''', (row['file'], row['line_number'], row['raw_line'], row['error'], datetime.now().isoformat()))
                                conn.commit()
                                self.logger.warning(f"Logged {len(error_rows)} problematic rows from {file_path} to commodities_import_errors table.")
                            except Exception as e:
                                self.logger.error(f"Error logging import errors: {e}")
                            finally:
                                conn.close()
                    return True
                    
                elif 'FOSS_landings' in file_path:
                    error_rows = []
                    chunk_size = 10000
                    total_rows = 0
                    for chunk in pd.read_csv(file_path, chunksize=chunk_size, skiprows=2):
                        # Clean up column names
                        chunk.columns = [col.strip().lower().replace(' ', '_') for col in chunk.columns]
                        # Use 'year' as date if present
                        if 'year' in chunk.columns:
                            chunk['date'] = pd.to_datetime(chunk['year'], errors='coerce')
                        else:
                            chunk['date'] = pd.NaT
                        # Log rows with missing/invalid date
                        invalid = chunk[chunk['date'].isna()]
                        for idx, row in invalid.iterrows():
                            error_rows.append({'file': file_path, 'line_number': str(idx), 'raw_line': str(row.to_dict()), 'error': 'Missing or invalid date'})
                        # Keep only valid rows
                        chunk = chunk[chunk['date'].notna()]
                        # Add metadata
                        chunk['commodity_type'] = 'fisheries'
                        chunk['source'] = 'noaa_foss'
                        chunk['unit'] = 'pounds'
                        # Save chunk to database
                        self.save_to_database(chunk, 'commodities_data')
                        total_rows += len(chunk)
                    # Log errors to commodities_import_errors table
                    if error_rows:
                        conn = self._create_connection()
                        if conn is not None:
                            try:
                                cursor = conn.cursor()
                                cursor.execute('''
                                    CREATE TABLE IF NOT EXISTS commodities_import_errors (
                                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                                        file TEXT,
                                        line_number TEXT,
                                        raw_line TEXT,
                                        error TEXT,
                                        timestamp TEXT
                                    )
                                ''')
                                for row in error_rows:
                                    cursor.execute('''
                                        INSERT INTO commodities_import_errors (file, line_number, raw_line, error, timestamp)
                                        VALUES (?, ?, ?, ?, ?)
                                    ''', (row['file'], row['line_number'], row['raw_line'], row['error'], datetime.now().isoformat()))
                                conn.commit()
                                self.logger.warning(f"Logged {len(error_rows)} problematic rows from {file_path} to commodities_import_errors table.")
                            except Exception as e:
                                self.logger.error(f"Error logging import errors: {e}")
                            finally:
                                conn.close()
                    self.logger.info(f"Imported {total_rows} valid records from {file_path}")
                    return True
                    
                elif any(crypto in file_path for crypto in ['BTCUSD_d.csv', 'ETHUSD_d.csv', 'LTCUSD_d.csv']):
                    # Handle crypto CSV files
                    df = pd.read_csv(file_path, skiprows=1)  # Skip URL line
                    # Clean up column names
                    df.columns = [col.strip().lower().replace(' ', '_') for col in df.columns]
                    # Convert date to datetime
                    df['date'] = pd.to_datetime(df['date'], errors='coerce')
                    # Log rows with missing/invalid date
                    invalid = df[df['date'].isna()]
                    error_rows = []
                    for idx, row in invalid.iterrows():
                        error_rows.append({'file': file_path, 'line_number': str(idx), 'raw_line': str(row.to_dict()), 'error': 'Missing or invalid date'})
                    # Keep only valid rows
                    df = df[df['date'].notna()]
                    # Add metadata
                    df['commodity_type'] = 'crypto'
                    df['source'] = 'crypto_data_download'
                    df['unit'] = 'USD'
                    # Save to database
                    self.save_to_database(df, 'commodities_data')
                    self.logger.info(f"Imported {len(df)} records from {file_path}")
                    # Log errors to commodities_import_errors table
                    if error_rows:
                        conn = self._create_connection()
                        if conn is not None:
                            try:
                                cursor = conn.cursor()
                                cursor.execute('''
                                    CREATE TABLE IF NOT EXISTS commodities_import_errors (
                                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                                        file TEXT,
                                        line_number TEXT,
                                        raw_line TEXT,
                                        error TEXT,
                                        timestamp TEXT
                                    )
                                ''')
                                for row in error_rows:
                                    cursor.execute('''
                                        INSERT INTO commodities_import_errors (file, line_number, raw_line, error, timestamp)
                                        VALUES (?, ?, ?, ?, ?)
                                    ''', (row['file'], row['line_number'], row['raw_line'], row['error'], datetime.now().isoformat()))
                                conn.commit()
                                self.logger.warning(f"Logged {len(error_rows)} problematic rows from {file_path} to commodities_import_errors table.")
                            except Exception as e:
                                self.logger.error(f"Error logging import errors: {e}")
                            finally:
                                conn.close()
                    return True
                    
            elif file_path.endswith('.xlsx') or file_path.endswith('.xlsb'):
                if 'HogsCostReturn' in file_path:
                    # Handle hog data
                    df = pd.read_excel(file_path, skiprows=5)  # Skip header rows
                    # Clean up column names
                    df.columns = [col.strip() for col in df.columns]
                    # Use second column (Unnamed: 1) as year
                    if 'Unnamed: 1' in df.columns:
                        df['date'] = pd.to_datetime(df['Unnamed: 1'], errors='coerce')
                    else:
                        df['date'] = pd.NaT
                    # Log rows with missing/invalid date
                    invalid = df[df['date'].isna()]
                    error_rows = []
                    for idx, row in invalid.iterrows():
                        error_rows.append({'file': file_path, 'line_number': str(idx), 'raw_line': str(row.to_dict()), 'error': 'Missing or invalid date'})
                    # Keep only valid rows
                    df = df[df['date'].notna()]
                    # Add metadata
                    df['commodity_type'] = 'livestock'
                    df['source'] = 'hog_cost_return'
                    df['unit'] = 'USD'
                    # Save to database
                    self.save_to_database(df, 'commodities_data')
                    self.logger.info(f"Imported {len(df)} records from {file_path}")
                    # Log errors to commodities_import_errors table
                    if error_rows:
                        conn = self._create_connection()
                        if conn is not None:
                            try:
                                cursor = conn.cursor()
                                cursor.execute('''
                                    CREATE TABLE IF NOT EXISTS commodities_import_errors (
                                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                                        file TEXT,
                                        line_number TEXT,
                                        raw_line TEXT,
                                        error TEXT,
                                        timestamp TEXT
                                    )
                                ''')
                                for row in error_rows:
                                    cursor.execute('''
                                        INSERT INTO commodities_import_errors (file, line_number, raw_line, error, timestamp)
                                        VALUES (?, ?, ?, ?, ?)
                                    ''', (row['file'], row['line_number'], row['raw_line'], row['error'], datetime.now().isoformat()))
                                conn.commit()
                                self.logger.warning(f"Logged {len(error_rows)} problematic rows from {file_path} to commodities_import_errors table.")
                            except Exception as e:
                                self.logger.error(f"Error logging import errors: {e}")
                            finally:
                                conn.close()
                    return True
                    
                elif 'Alaska Salmon' in file_path:
                    # Handle salmon data
                    df = pd.read_excel(file_path, skiprows=1)  # Skip header row
                    # Clean up the data
                    df = df.melt(id_vars=['Area ', 'Year'], 
                               var_name='Process Category',
                               value_name='Price')
                    df['commodity_type'] = 'fisheries'
                    df['region'] = 'Alaska'
                    df['source'] = 'alaska_salmon'
                    df['date'] = pd.to_datetime(df['Year'], format='%Y').dt.strftime('%Y-%m-%d')
                    df['unit'] = 'USD'
                    
                    # Save to database
                    self.save_to_database(df, 'commodities_data')
                    self.logger.info(f"Imported {len(df)} records from {file_path}")
                    return True
                    
                elif 'A.CRE-Ai1-UW' in file_path:
                    # Handle agricultural data
                    try:
                        import pyxlsb
                        df = pd.read_excel(file_path, engine='pyxlsb')
                        # TODO: Add specific parsing for agricultural data
                        self.logger.info(f"Found agricultural data with {len(df)} rows")
                        return True
                    except ImportError:
                        self.logger.error("pyxlsb package required for .xlsb files. Please install with: pip install pyxlsb")
                        return False
                    
            else:
                self.logger.error(f"Unsupported file format: {file_path}")
                return False

        except Exception as e:
            self.logger.error(f"Error importing commodity file {file_path}: {e}")
            return False

    def _categorize_commodity(self, commodity_name: str) -> str:
        """
        Categorize commodities into main groups.
        
        Parameters
        ----------
        commodity_name : str
            Name of the commodity
            
        Returns
        -------
        str
            Category of the commodity
        """
        commodity_name = commodity_name.lower()
        
        # Energy commodities
        if any(term in commodity_name for term in ['oil', 'gas', 'coal', 'fuel', 'diesel', 'gasoline']):
            return 'energy'
        
        # Agricultural commodities
        if any(term in commodity_name for term in ['wheat', 'corn', 'soy', 'rice', 'barley', 'maize']):
            return 'agricultural'
        
        # Livestock
        if any(term in commodity_name for term in ['beef', 'pork', 'poultry', 'lamb', 'swine']):
            return 'livestock'
        
        # Metals
        if any(term in commodity_name for term in ['aluminum', 'copper', 'gold', 'silver', 'iron', 'steel']):
            return 'metals'
        
        # Soft commodities
        if any(term in commodity_name for term in ['coffee', 'cocoa', 'sugar', 'cotton', 'rubber']):
            return 'soft_commodities'
        
        # Fisheries
        if any(term in commodity_name for term in ['fish', 'salmon', 'shrimp']):
            return 'fisheries'
        
        return 'other'

    def initialize_data_sources(self):
        """Initialize the data sources table to track available data sources."""
        conn = self._create_connection()
        if conn is None:
            return False

        try:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS data_sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    data_type TEXT NOT NULL,
                    last_checked TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    description TEXT,
                    update_frequency TEXT,
                    data_format TEXT,
                    requires_api_key BOOLEAN DEFAULT 0,
                    api_key_name TEXT,
                    rate_limit TEXT,
                    timezone TEXT,
                    data_start_date TEXT,
                    data_end_date TEXT,
                    last_successful_fetch TEXT,
                    error_count INTEGER DEFAULT 0,
                    last_error TEXT,
                    preferred_download_method TEXT,
                    data_quality_score INTEGER,
                    notes TEXT,
                    UNIQUE (source_name, url)
                )
            ''')
            
            # Insert known data sources with enhanced metadata
            sources = [
                ('NOAA Fisheries', 
                 'https://www.fisheries.noaa.gov/foss/f?p=215:200', 
                 'fisheries',
                 'NOAA Fisheries landing data',
                 'daily',
                 'CSV',
                 0,
                 None,
                 '100 requests/hour',
                 'UTC',
                 '1950-01-01',
                 None,
                 None,
                 0,
                 None,
                 'direct_download',
                 90,
                 'Requires manual data extraction from web interface'),
                 
                ('IMF Commodity Prices',
                 'https://www.imf.org/en/Research/commodity-prices',
                 'commodities',
                 'IMF commodity price database',
                 'monthly',
                 'CSV/Excel',
                 0,
                 None,
                 'unlimited',
                 'UTC',
                 '1980-01-01',
                 None,
                 None,
                 0,
                 None,
                 'direct_download',
                 95,
                 'Provides historical commodity price indices'),
                 
                ('IMF Fish Data',
                 'https://data.imf.org/?sk=2CDDCCB8-0B59-43E9-B6A0-59210D5605D2',
                 'fisheries',
                 'IMF fish trade data',
                 'quarterly',
                 'CSV',
                 0,
                 None,
                 'unlimited',
                 'UTC',
                 '1990-01-01',
                 None,
                 None,
                 0,
                 None,
                 'direct_download',
                 85,
                 'Includes global fish trade statistics'),
                 
                ('NOAA Foreign Fishery',
                 'https://www.fisheries.noaa.gov/national/sustainable-fisheries/foreign-fishery-trade-data',
                 'fisheries',
                 'NOAA foreign fishery trade data',
                 'monthly',
                 'CSV/Excel',
                 0,
                 None,
                 '100 requests/hour',
                 'UTC',
                 '1980-01-01',
                 None,
                 None,
                 0,
                 None,
                 'direct_download',
                 90,
                 'Comprehensive foreign fishery trade statistics'),
                 
                ('IMF Commodity Data',
                 'https://data.imf.org/?sk=388DFA60-1D26-4ADE-B505-A05A558D9A42',
                 'commodities',
                 'IMF commodity price indices',
                 'monthly',
                 'CSV',
                 0,
                 None,
                 'unlimited',
                 'UTC',
                 '1980-01-01',
                 None,
                 None,
                 0,
                 None,
                 'direct_download',
                 95,
                 'Primary source for commodity price indices'),
                 
                ('Our World in Data',
                 'https://ourworldindata.org/fish-and-overfishing',
                 'fisheries',
                 'Global fish and overfishing statistics',
                 'annual',
                 'CSV',
                 0,
                 None,
                 'unlimited',
                 'UTC',
                 '1950-01-01',
                 None,
                 None,
                 0,
                 None,
                 'direct_download',
                 85,
                 'Provides historical overfishing data'),
                 
                ('Statista Salmon',
                 'https://www.statista.com/statistics/1195271/price-salmon-price-index/',
                 'fisheries',
                 'Salmon price index data',
                 'monthly',
                 'CSV/Excel',
                 1,
                 'STATISTA_API_KEY',
                 '100 requests/day',
                 'UTC',
                 '2010-01-01',
                 None,
                 None,
                 0,
                 None,
                 'api',
                 80,
                 'Requires Statista subscription'),
                 
                ('CryptoDataDownload',
                 'https://www.CryptoDataDownload.com',
                 'crypto',
                 'Cryptocurrency historical price data',
                 'daily',
                 'CSV',
                 0,
                 None,
                 'unlimited',
                 'UTC',
                 '2010-01-01',
                 None,
                 None,
                 0,
                 None,
                 'direct_download',
                 90,
                 'Provides historical crypto price data')
            ]
            
            cursor.executemany('''
                INSERT OR IGNORE INTO data_sources 
                (source_name, url, data_type, description, update_frequency, 
                 data_format, requires_api_key, api_key_name, rate_limit, 
                 timezone, data_start_date, data_end_date, last_successful_fetch,
                 error_count, last_error, preferred_download_method, 
                 data_quality_score, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', sources)
            
            conn.commit()
            self.logger.info("Data sources initialized successfully with enhanced metadata")
            return True

        except sqlite3.Error as e:
            self.logger.error(f"Error initializing data sources: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def get_data_source_info(self, source_name: str = None, data_type: str = None):
        """
        Get information about data sources, optionally filtered by source name or data type.
        
        Parameters
        ----------
        source_name : str, optional
            Filter by source name
        data_type : str, optional
            Filter by data type
            
        Returns
        -------
        pd.DataFrame
            Data source information
        """
        conn = self._create_connection()
        if conn is None:
            return pd.DataFrame()

        try:
            query = "SELECT * FROM data_sources WHERE 1=1"
            params = []
            
            if source_name:
                query += " AND source_name = ?"
                params.append(source_name)
            if data_type:
                query += " AND data_type = ?"
                params.append(data_type)
            
            df = pd.read_sql_query(query, conn, params=params)
            return df

        except sqlite3.Error as e:
            self.logger.error(f"Error getting data source info: {e}")
            return pd.DataFrame()
        finally:
            if conn:
                conn.close()

def check_missing_data(db_path: str):
    """Check the data_not_available table and print missing data requests."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, symbol, start_date, end_date, last_checked, num_attempts, reason
        FROM data_not_available
        ORDER BY last_checked ASC
    """)
    rows = cur.fetchall()
    conn.close()
    if not rows:
        print("No missing data requests found.")
        return
    print("Missing data requests:")
    for row in rows:
        print(f"ID: {row[0]}, Symbol: {row[1]}, Start: {row[2]}, End: {row[3]}, Last Checked: {row[4]}, Attempts: {row[5]}, Reason: {row[6]}")

    # Skeleton: Attempt to fetch/ingest missing data
    for row in rows:
        symbol = row[1]
        start_date = row[2]
        end_date = row[3]
        print(f"[TODO] Attempt to fetch/ingest data for {symbol} from {start_date} to {end_date}")
        # If successful, remove or update the entry
        # If not, increment num_attempts and update last_checked

def main():
    """Main function to demonstrate usage."""
    # Initialize the extended shepherd
    shepherd = ExtendedDataShepherd()
    
    # Initialize database tables
    shepherd.initialize_database()
    shepherd.initialize_commodities_table()
    shepherd.initialize_data_sources()
    
    # Check data sources for updates
    shepherd.check_data_sources()
    
    # Import commodity data
    commodity_files = [
        ('/Users/xavier/sbox/Financial_Data/Commodities/A.CRE-Ai1-UW-v0.87.xlsb', 'agricultural'),
        ('/Users/xavier/sbox/Financial_Data/Commodities/Commodity1 Month Change12 Month ChangeYear to Date.csv', 'general'),
        ('/Users/xavier/sbox/Financial_Data/Commodities/FOSS_landings.csv', 'fisheries'),
        ('/Users/xavier/sbox/Financial_Data/Commodities/HogsCostReturn.xlsx', 'livestock'),
        ('/Users/xavier/sbox/Financial_Data/Commodities/Alaska Salmon Fishery Wholesale Prices, 2000 - 2013.xlsx', 'fisheries')
    ]
    
    for file_path, commodity_type in commodity_files:
        shepherd.import_commodity_file(file_path, commodity_type)
    
    # Example: Process stock data
    stock_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN']
    shepherd.run_daily_shepherd(stock_symbols)
    
    # Example: Process forex data
    forex_pairs = [('USD', 'EUR'), ('USD', 'JPY'), ('GBP', 'USD')]
    for from_curr, to_curr in forex_pairs:
        df = shepherd.fetch_forex_data(from_curr, to_curr)
        if not df.empty:
            shepherd.save_to_database(df, 'forex_data')
    
    # Example: Process crypto data
    crypto_symbols = ['BTC', 'ETH', 'XRP']
    for symbol in crypto_symbols:
        df = shepherd.fetch_crypto_data(symbol)
        if not df.empty:
            shepherd.save_to_database(df, 'crypto_data')

    # Check missing data
    db_path = "data/mstables.sqlite"
    check_missing_data(db_path)

if __name__ == '__main__':
    main() 