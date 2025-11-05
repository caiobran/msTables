import os
import time
from datetime import datetime, timedelta
import pandas as pd
import sqlite3
from dotenv import load_dotenv
import logging
from typing import List, Dict, Optional, Union
import yfinance as yf
from yfinance import Ticker
import requests
import bs4 as bs
import getpass
from ..utils.yahoo_finance_reference import get_exchange_suffix, get_data_provider, get_exchange_info

class YahooFetcher:
    """Comprehensive Yahoo Finance data fetcher that handles multiple data types."""
    
    def __init__(self, db_path: str = None):
        """Initialize the Yahoo Finance fetcher with database path."""
        self.db_path = db_path or 'data/mstables.sqlite'
        
        # Setup paths
        self.user_name = getpass.getuser()
        self.base_path = os.path.expanduser(f'~/Data/Global_Finance_Webscrape')
        self.csv_path = os.path.join(self.base_path, 'csv')
        self.log_path = os.path.join(self.base_path, 'logs')
        
        # Create necessary directories
        os.makedirs(self.csv_path, exist_ok=True)
        os.makedirs(self.log_path, exist_ok=True)
        
        # Setup logging after paths are created
        self._setup_logging()
        
        # Create database tables
        self._create_tables()
        
        # Rate limiting parameters
        self.requests_per_second = 2  # Yahoo Finance rate limit
        self.last_request_time = 0
        
        # Load exchange information
        self.exchange_info = {market: (suffix, delay) for _, market, suffix, delay, _ in get_exchange_info()}
        
    def _setup_logging(self):
        """Set up logging configuration."""
        log_file = os.path.join(self.log_path, f'yahoo_fetcher_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('YahooFetcher')
        
    def _create_tables(self):
        """Create necessary database tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables for different data types
        cursor.executescript('''
            -- Historical price data
            CREATE TABLE IF NOT EXISTS yahoo_daily (
                id INTEGER PRIMARY KEY,
                symbol TEXT,
                exchange TEXT,
                date TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                adj_close REAL,
                fetch_date TEXT,
                data_provider TEXT,
                UNIQUE(symbol, date)
            );
            
            -- Company info
            CREATE TABLE IF NOT EXISTS yahoo_info (
                id INTEGER PRIMARY KEY,
                symbol TEXT,
                short_name TEXT,
                long_name TEXT,
                sector TEXT,
                industry TEXT,
                market_cap REAL,
                currency TEXT,
                exchange TEXT,
                quote_type TEXT,
                fetch_date TEXT,
                UNIQUE(symbol)
            );
            
            -- Financial statements
            CREATE TABLE IF NOT EXISTS yahoo_financials (
                id INTEGER PRIMARY KEY,
                symbol TEXT,
                statement_type TEXT,
                date TEXT,
                data TEXT,  -- Store as JSON string
                fetch_date TEXT,
                UNIQUE(symbol, statement_type, date)
            );
            
            -- Balance sheet
            CREATE TABLE IF NOT EXISTS yahoo_balance_sheet (
                id INTEGER PRIMARY KEY,
                symbol TEXT,
                date TEXT,
                total_assets REAL,
                total_current_assets REAL,
                cash REAL,
                short_term_investments REAL,
                net_receivables REAL,
                inventory REAL,
                other_current_assets REAL,
                total_liabilities REAL,
                total_current_liabilities REAL,
                accounts_payable REAL,
                short_term_debt REAL,
                other_current_liabilities REAL,
                total_stockholder_equity REAL,
                treasury_stock REAL,
                retained_earnings REAL,
                common_stock REAL,
                fetch_date TEXT,
                UNIQUE(symbol, date)
            );
            
            -- Income statement
            CREATE TABLE IF NOT EXISTS yahoo_income_stmt (
                id INTEGER PRIMARY KEY,
                symbol TEXT,
                date TEXT,
                total_revenue REAL,
                cost_of_revenue REAL,
                gross_profit REAL,
                research_development REAL,
                operating_expense REAL,
                operating_income REAL,
                net_income REAL,
                eps REAL,
                eps_diluted REAL,
                fetch_date TEXT,
                UNIQUE(symbol, date)
            );
            
            -- Cash flow statement
            CREATE TABLE IF NOT EXISTS yahoo_cash_flow (
                id INTEGER PRIMARY KEY,
                symbol TEXT,
                date TEXT,
                operating_cash_flow REAL,
                investing_cash_flow REAL,
                financing_cash_flow REAL,
                free_cash_flow REAL,
                capital_expenditure REAL,
                dividend_payout REAL,
                stock_repurchase REAL,
                fetch_date TEXT,
                UNIQUE(symbol, date)
            );
            
            -- Major holders
            CREATE TABLE IF NOT EXISTS yahoo_major_holders (
                id INTEGER PRIMARY KEY,
                symbol TEXT,
                holder_name TEXT,
                shares_held INTEGER,
                value REAL,
                percent_held REAL,
                fetch_date TEXT,
                UNIQUE(symbol, holder_name, fetch_date)
            );
            
            -- Institutional holders
            CREATE TABLE IF NOT EXISTS yahoo_institutional_holders (
                id INTEGER PRIMARY KEY,
                symbol TEXT,
                holder_name TEXT,
                shares_held INTEGER,
                value REAL,
                percent_held REAL,
                fetch_date TEXT,
                UNIQUE(symbol, holder_name, fetch_date)
            );
            
            -- Options data
            CREATE TABLE IF NOT EXISTS yahoo_options (
                id INTEGER PRIMARY KEY,
                symbol TEXT,
                expiration_date TEXT,
                strike_price REAL,
                option_type TEXT,
                last_price REAL,
                bid REAL,
                ask REAL,
                volume INTEGER,
                open_interest INTEGER,
                implied_volatility REAL,
                contract_symbol TEXT,
                fetch_date TEXT,
                UNIQUE(symbol, expiration_date, strike_price, option_type)
            );
            
            -- Create indices
            CREATE INDEX IF NOT EXISTS idx_yahoo_daily_symbol ON yahoo_daily(symbol);
            CREATE INDEX IF NOT EXISTS idx_yahoo_daily_date ON yahoo_daily(date);
            CREATE INDEX IF NOT EXISTS idx_yahoo_info_symbol ON yahoo_info(symbol);
            CREATE INDEX IF NOT EXISTS idx_yahoo_financials_symbol ON yahoo_financials(symbol);
            CREATE INDEX IF NOT EXISTS idx_yahoo_balance_sheet_symbol ON yahoo_balance_sheet(symbol);
            CREATE INDEX IF NOT EXISTS idx_yahoo_income_stmt_symbol ON yahoo_income_stmt(symbol);
            CREATE INDEX IF NOT EXISTS idx_yahoo_cash_flow_symbol ON yahoo_cash_flow(symbol);
            CREATE INDEX IF NOT EXISTS idx_yahoo_major_holders_symbol ON yahoo_major_holders(symbol);
            CREATE INDEX IF NOT EXISTS idx_yahoo_institutional_holders_symbol ON yahoo_institutional_holders(symbol);
            CREATE INDEX IF NOT EXISTS idx_yahoo_options_symbol ON yahoo_options(symbol);
        ''')
        
        conn.commit()
        conn.close()
        
    def _get_exchange_delay(self, exchange: str) -> float:
        """Get the appropriate delay for an exchange based on its data delay."""
        if exchange in self.exchange_info:
            delay_str = self.exchange_info[exchange][1]
            if delay_str == 'Real-time':
                return 0.5  # 500ms minimum delay
            elif 'min' in delay_str:
                return float(delay_str.split()[0]) * 60  # Convert minutes to seconds
        return 1.0  # Default 1 second delay
        
    def _rate_limit(self, exchange: str = None):
        """Implement rate limiting to respect Yahoo Finance limits and exchange delays."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        # Get appropriate delay based on exchange
        delay = self._get_exchange_delay(exchange) if exchange else (1.0 / self.requests_per_second)
        
        if time_since_last < delay:
            time.sleep(delay - time_since_last)
        self.last_request_time = time.time()
        
    def _get_full_symbol(self, symbol: str, exchange: str = None) -> str:
        """Get the full symbol with exchange suffix if needed."""
        if exchange and exchange in self.exchange_info:
            suffix = self.exchange_info[exchange][0]
            if suffix != 'N/A':
                return f"{symbol}{suffix}"
        return symbol
        
    def fetch_all_data(self, symbols: List[str], batch_size: int = 25, 
                      delay_between_batches: int = 1, test_mode: bool = False) -> int:
        """Fetch all available data types for the given symbols."""
        if test_mode:
            symbols = symbols[:25]
            
        success_count = 0
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            try:
                # Fetch historical price data
                self._fetch_daily_data(batch)
                
                # Fetch company info
                self._fetch_info(batch)
                
                # Fetch financial statements
                self._fetch_financials(batch)
                
                # Fetch balance sheet
                self._fetch_balance_sheet(batch)
                
                # Fetch income statement
                self._fetch_income_stmt(batch)
                
                # Fetch cash flow statement
                self._fetch_cash_flow(batch)
                
                # Fetch major holders
                self._fetch_major_holders(batch)
                
                # Fetch institutional holders
                self._fetch_institutional_holders(batch)
                
                # Fetch options data
                self._fetch_options(batch)
                
                success_count += len(batch)
                self.logger.info(f"Successfully processed batch of {len(batch)} symbols")
                
            except Exception as e:
                self.logger.error(f"Error processing batch: {str(e)}")
                continue
                
            if i + batch_size < len(symbols):
                time.sleep(delay_between_batches)
                
        return success_count
        
    def _fetch_daily_data(self, symbols: List[str], exchange: str = None):
        """Fetch daily price data for symbols."""
        for symbol in symbols:
            try:
                full_symbol = self._get_full_symbol(symbol, exchange)
                self._rate_limit(exchange)
                
                ticker = yf.Ticker(full_symbol)
                df = ticker.history(period="1y")  # Last year of data
                
                if not df.empty:
                    df = df.reset_index()
                    df['symbol'] = symbol
                    df['exchange'] = exchange
                    df['fetch_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    df['data_provider'] = get_data_provider('us_equities' if not exchange else 'international_charts')
                    
                    # Ensure column names match the database schema
                    df = df.rename(columns={
                        'Date': 'date',
                        'Open': 'open',
                        'High': 'high',
                        'Low': 'low',
                        'Close': 'close',
                        'Volume': 'volume',
                        'Adj Close': 'adj_close'
                    })
                    
                    # Select only the columns we need
                    columns = ['symbol', 'exchange', 'date', 'open', 'high', 'low', 'close', 
                             'volume', 'adj_close', 'fetch_date', 'data_provider']
                    df = df[columns]
                    
                    conn = sqlite3.connect(self.db_path)
                    df.to_sql('yahoo_daily', conn, if_exists='append', index=False)
                    conn.close()
                    
            except Exception as e:
                self.logger.error(f"Error fetching daily data for {symbol}: {str(e)}")
                
    def _fetch_info(self, symbols: List[str]):
        """Fetch company info for symbols."""
        self._rate_limit()
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                
                if info:
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO yahoo_info 
                        (symbol, short_name, long_name, sector, industry,
                         market_cap, currency, exchange, quote_type, fetch_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        symbol,
                        info.get('shortName'),
                        info.get('longName'),
                        info.get('sector'),
                        info.get('industry'),
                        info.get('marketCap'),
                        info.get('currency'),
                        info.get('exchange'),
                        info.get('quoteType'),
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    ))
                    conn.commit()
                    conn.close()
                    
            except Exception as e:
                self.logger.error(f"Error fetching info for {symbol}: {str(e)}")
                
    def _fetch_financials(self, symbols: List[str]):
        """Fetch financial statements for symbols."""
        self._rate_limit()
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                
                # Fetch quarterly financials
                quarterly = ticker.quarterly_financials
                if not quarterly.empty:
                    self._store_financials(symbol, 'quarterly', quarterly)
                
                # Fetch annual financials
                annual = ticker.financials
                if not annual.empty:
                    self._store_financials(symbol, 'annual', annual)
                    
            except Exception as e:
                self.logger.error(f"Error fetching financials for {symbol}: {str(e)}")
                
    def _store_financials(self, symbol: str, statement_type: str, data: pd.DataFrame):
        """Store financial statement data in the database."""
        if not data.empty:
            data = data.reset_index()
            data['symbol'] = symbol
            data['statement_type'] = statement_type
            data['fetch_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Convert the DataFrame to JSON string
            data_json = data.to_json(orient='records')
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO yahoo_financials 
                (symbol, statement_type, date, data, fetch_date)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                symbol,
                statement_type,
                datetime.now().strftime('%Y-%m-%d'),
                data_json,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            conn.commit()
            conn.close()
            
    def _fetch_balance_sheet(self, symbols: List[str]):
        """Fetch balance sheet data for symbols."""
        self._rate_limit()
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                balance_sheet = ticker.balance_sheet
                
                if not balance_sheet.empty:
                    balance_sheet = balance_sheet.reset_index()
                    balance_sheet['symbol'] = symbol
                    balance_sheet['fetch_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    conn = sqlite3.connect(self.db_path)
                    balance_sheet.to_sql('yahoo_balance_sheet', conn, if_exists='append', index=False)
                    conn.close()
                    
            except Exception as e:
                self.logger.error(f"Error fetching balance sheet for {symbol}: {str(e)}")
                
    def _fetch_income_stmt(self, symbols: List[str]):
        """Fetch income statement data for symbols."""
        self._rate_limit()
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                income_stmt = ticker.income_stmt
                
                if not income_stmt.empty:
                    income_stmt = income_stmt.reset_index()
                    income_stmt['symbol'] = symbol
                    income_stmt['fetch_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    conn = sqlite3.connect(self.db_path)
                    income_stmt.to_sql('yahoo_income_stmt', conn, if_exists='append', index=False)
                    conn.close()
                    
            except Exception as e:
                self.logger.error(f"Error fetching income statement for {symbol}: {str(e)}")
                
    def _fetch_cash_flow(self, symbols: List[str]):
        """Fetch cash flow statement data for symbols."""
        self._rate_limit()
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                cash_flow = ticker.cashflow
                
                if not cash_flow.empty:
                    cash_flow = cash_flow.reset_index()
                    cash_flow['symbol'] = symbol
                    cash_flow['fetch_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    conn = sqlite3.connect(self.db_path)
                    cash_flow.to_sql('yahoo_cash_flow', conn, if_exists='append', index=False)
                    conn.close()
                    
            except Exception as e:
                self.logger.error(f"Error fetching cash flow for {symbol}: {str(e)}")
                
    def _fetch_major_holders(self, symbols: List[str]):
        """Fetch major holders data for symbols."""
        self._rate_limit()
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                major_holders = ticker.major_holders
                
                if not major_holders.empty:
                    major_holders = major_holders.reset_index()
                    major_holders['symbol'] = symbol
                    major_holders['fetch_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    conn = sqlite3.connect(self.db_path)
                    major_holders.to_sql('yahoo_major_holders', conn, if_exists='append', index=False)
                    conn.close()
                    
            except Exception as e:
                self.logger.error(f"Error fetching major holders for {symbol}: {str(e)}")
                
    def _fetch_institutional_holders(self, symbols: List[str]):
        """Fetch institutional holders data for symbols."""
        self._rate_limit()
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                institutional_holders = ticker.institutional_holders
                
                if not institutional_holders.empty:
                    institutional_holders = institutional_holders.reset_index()
                    institutional_holders['symbol'] = symbol
                    institutional_holders['fetch_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    conn = sqlite3.connect(self.db_path)
                    institutional_holders.to_sql('yahoo_institutional_holders', conn, if_exists='append', index=False)
                    conn.close()
                    
            except Exception as e:
                self.logger.error(f"Error fetching institutional holders for {symbol}: {str(e)}")
                
    def _fetch_options(self, symbols: List[str]):
        """Fetch options data for symbols."""
        self._rate_limit()
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                options = ticker.options
                
                if options:
                    for expiration in options:
                        try:
                            opt = ticker.option_chain(expiration)
                            
                            # Process calls
                            if not opt.calls.empty:
                                calls = opt.calls.copy()
                                calls['symbol'] = symbol
                                calls['expiration_date'] = expiration
                                calls['option_type'] = 'call'
                                calls['fetch_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                calls['contract_symbol'] = calls.index  # Store the contract symbol
                                
                                # Select and rename columns to match schema
                                columns = ['symbol', 'expiration_date', 'strike_price', 'option_type',
                                         'last_price', 'bid', 'ask', 'volume', 'open_interest',
                                         'implied_volatility', 'contract_symbol', 'fetch_date']
                                calls = calls.rename(columns={
                                    'strike': 'strike_price',
                                    'lastPrice': 'last_price',
                                    'impliedVolatility': 'implied_volatility',
                                    'openInterest': 'open_interest'
                                })
                                calls = calls[columns]
                                
                                conn = sqlite3.connect(self.db_path)
                                calls.to_sql('yahoo_options', conn, if_exists='append', index=False)
                                conn.close()
                            
                            # Process puts
                            if not opt.puts.empty:
                                puts = opt.puts.copy()
                                puts['symbol'] = symbol
                                puts['expiration_date'] = expiration
                                puts['option_type'] = 'put'
                                puts['fetch_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                puts['contract_symbol'] = puts.index  # Store the contract symbol
                                
                                # Select and rename columns to match schema
                                puts = puts.rename(columns={
                                    'strike': 'strike_price',
                                    'lastPrice': 'last_price',
                                    'impliedVolatility': 'implied_volatility',
                                    'openInterest': 'open_interest'
                                })
                                puts = puts[columns]
                                
                                conn = sqlite3.connect(self.db_path)
                                puts.to_sql('yahoo_options', conn, if_exists='append', index=False)
                                conn.close()
                                
                        except Exception as e:
                            self.logger.error(f"Error fetching options for {symbol} expiration {expiration}: {str(e)}")
                            continue
                            
            except Exception as e:
                self.logger.error(f"Error fetching options for {symbol}: {str(e)}")

    def get_sp500_tickers(self) -> List[str]:
        """Fetch S&P 500 tickers from Wikipedia."""
        try:
            resp = requests.get('http://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
            if resp.status_code != 200:
                self.logger.error(f"Failed to fetch S&P 500 data. Status code: {resp.status_code}")
                return []
                
            soup = bs.BeautifulSoup(resp.text, 'lxml')
            table = soup.find('table', {'class': 'wikitable sortable'})
            
            if not table:
                self.logger.error("Could not find S&P 500 table on Wikipedia")
                return []
                
            tickers = []
            for row in table.findAll('tr')[1:]:
                ticker = row.findAll('td')[0].text.strip()
                tickers.append(ticker)
                
            self.logger.info(f"Successfully fetched {len(tickers)} S&P 500 tickers")
            return tickers
            
        except Exception as e:
            self.logger.error(f"Error fetching S&P 500 tickers: {str(e)}")
            return []
            
    def export_to_csv(self, symbol: str, data_type: str, df: pd.DataFrame):
        """Export data to CSV file."""
        try:
            csv_file = os.path.join(self.csv_path, f'{symbol}_{data_type}.csv')
            df.to_csv(csv_file, index=False)
            self.logger.info(f"Exported {data_type} data for {symbol} to {csv_file}")
        except Exception as e:
            self.logger.error(f"Error exporting {data_type} data for {symbol} to CSV: {str(e)}")
            
    def fetch_sp500_data(self, batch_size: int = 25, delay_between_batches: int = 1, 
                        test_mode: bool = False) -> int:
        """Fetch data for all S&P 500 stocks."""
        tickers = self.get_sp500_tickers()
        if not tickers:
            return 0
            
        return self.fetch_all_data(tickers, batch_size, delay_between_batches, test_mode) 