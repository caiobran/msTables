import os
import time
from datetime import datetime, timedelta
import pandas as pd
import sqlite3
from dotenv import load_dotenv
import logging
from typing import List, Dict, Optional, Union
from enum import Enum

# Import IEX modules
from .daily import IEXDailyReader
from .deep import Deep
from .stats import DailySummaryReader, MonthlySummaryReader, RecordsReader, RecentReader
from .market import MarketReader
from .ref import ReferenceReader
from .tops import TopsReader

class IEXEndpointGroup(Enum):
    """Enum for IEX endpoint groups."""
    STOCKS = 'stocks'
    MARKET = 'market'
    CRYPTO = 'crypto'
    OPTIONS = 'options'
    REFERENCE = 'reference'
    INVESTORS_EXCHANGE = 'investors_exchange'
    ALTERNATIVE = 'alternative'
    ACCOUNT = 'account'

class IEXFeedType(Enum):
    """Enum for IEX feed types and their associated fees."""
    DEEP_REALTIME = {
        'name': 'DEEP Feed (Real-Time)',
        'fee': 2500,  # $2,500 per month
        'delay': 0,   # Real-time
        'features': ['full order book', 'real-time']
    }
    TOPS_REALTIME = {
        'name': 'TOPS Feed (Real-Time)',
        'fee': 500,   # $500 per month
        'delay': 0,   # Real-time
        'features': ['top of book', 'real-time']
    }
    DEEP_PLUS_REALTIME = {
        'name': 'DEEP+ Feed (Real-Time)',
        'fee': 0,     # Free when launched
        'delay': 0,   # Real-time
        'features': ['full order book', 'real-time', 'plus features']
    }
    DEEP_DELAYED = {
        'name': 'DEEP Feed (Delayed)',
        'fee': 0,     # Free
        'delay': 15,  # 15-minute delay
        'features': ['full order book', 'delayed']
    }
    TOPS_DELAYED = {
        'name': 'TOPS Feed (Delayed)',
        'fee': 0,     # Free
        'delay': 15,  # 15-minute delay
        'features': ['top of book', 'delayed']
    }
    DEEP_PLUS_DELAYED = {
        'name': 'DEEP+ Feed (Delayed)',
        'fee': 0,     # Free when launched
        'delay': 15,  # 15-minute delay
        'features': ['full order book', 'delayed', 'plus features']
    }

class IEXFetcher:
    """Comprehensive IEX data fetcher that handles multiple data types and respects rate limits."""
    
    def __init__(self, db_path: str = None, feed_type: IEXFeedType = IEXFeedType.DEEP_DELAYED):
        """Initialize the IEX fetcher with database path and API key."""
        load_dotenv()
        self.api_key = os.getenv('IEX_API_KEY')
        if not self.api_key:
            raise ValueError("IEX_API_KEY not found in environment variables")
            
        self.db_path = db_path or 'data/mstables.sqlite'
        self.feed_type = feed_type
        self._setup_logging()
        self._create_tables()
        self._validate_feed_type()
        
        # Rate limiting parameters
        self.requests_per_second = 100  # IEX Cloud tier 1 limit
        self.last_request_time = 0
        
    def _validate_feed_type(self):
        """Validate the feed type and log subscription information."""
        feed_info = self.feed_type.value
        self.logger.info(f"Using IEX feed: {feed_info['name']}")
        self.logger.info(f"Monthly fee: ${feed_info['fee']}")
        self.logger.info(f"Data delay: {feed_info['delay']} minutes")
        self.logger.info(f"Features: {', '.join(feed_info['features'])}")
        
        # Check if using a real-time feed
        if self.feed_type in [IEXFeedType.DEEP_REALTIME, IEXFeedType.TOPS_REALTIME, IEXFeedType.DEEP_PLUS_REALTIME]:
            self.logger.warning("Using real-time feed - ensure you have the appropriate subscription")
            
        # Check if using DEEP+ feed (not yet launched)
        if self.feed_type in [IEXFeedType.DEEP_PLUS_REALTIME, IEXFeedType.DEEP_PLUS_DELAYED]:
            self.logger.warning("DEEP+ feed is not yet launched - check IEX Trader Alerts for launch date")
            
    def _should_use_delayed_data(self) -> bool:
        """Determine if we should use delayed data based on feed type."""
        return self.feed_type in [
            IEXFeedType.DEEP_DELAYED,
            IEXFeedType.TOPS_DELAYED,
            IEXFeedType.DEEP_PLUS_DELAYED
        ]
        
    def _get_delay_minutes(self) -> int:
        """Get the delay in minutes for the current feed type."""
        return self.feed_type.value['delay']
        
    def _adjust_timestamp(self, timestamp: datetime) -> datetime:
        """Adjust timestamp based on feed delay."""
        if self._should_use_delayed_data():
            return timestamp - timedelta(minutes=self._get_delay_minutes())
        return timestamp
        
    def _setup_logging(self):
        """Set up logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('IEXFetcher')
        
    def _create_tables(self):
        """Create necessary database tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables for different data types
        cursor.executescript('''
            -- Stocks/Equities Tables
            CREATE TABLE IF NOT EXISTS iex_advanced_stats (
                id INTEGER PRIMARY KEY,
                symbol TEXT,
                total_cash REAL,
                current_debt REAL,
                revenue REAL,
                gross_profit REAL,
                total_revenue REAL,
                ebitda REAL,
                revenue_per_share REAL,
                revenue_per_employee REAL,
                debt_to_equity REAL,
                profit_margin REAL,
                enterprise_value REAL,
                enterprise_value_to_revenue REAL,
                price_to_sales REAL,
                price_to_book REAL,
                forward_pe_ratio REAL,
                peg_ratio REAL,
                pe_high REAL,
                pe_low REAL,
                fetch_date TEXT,
                UNIQUE(symbol, fetch_date)
            );

            CREATE TABLE IF NOT EXISTS iex_insider_roster (
                id INTEGER PRIMARY KEY,
                symbol TEXT,
                name TEXT,
                title TEXT,
                fetch_date TEXT,
                UNIQUE(symbol, name, fetch_date)
            );

            CREATE TABLE IF NOT EXISTS iex_insider_transactions (
                id INTEGER PRIMARY KEY,
                symbol TEXT,
                name TEXT,
                transaction_date TEXT,
                transaction_type TEXT,
                shares INTEGER,
                price REAL,
                value REAL,
                fetch_date TEXT,
                UNIQUE(symbol, name, transaction_date, transaction_type)
            );

            CREATE TABLE IF NOT EXISTS iex_largest_trades (
                id INTEGER PRIMARY KEY,
                symbol TEXT,
                price REAL,
                size INTEGER,
                time TEXT,
                time_label TEXT,
                venue TEXT,
                venue_name TEXT,
                fetch_date TEXT,
                UNIQUE(symbol, time, venue)
            );

            CREATE TABLE IF NOT EXISTS iex_volume_by_venue (
                id INTEGER PRIMARY KEY,
                symbol TEXT,
                venue TEXT,
                venue_name TEXT,
                volume INTEGER,
                market_percent REAL,
                avg_trade_size INTEGER,
                fetch_date TEXT,
                UNIQUE(symbol, venue, fetch_date)
            );

            -- Market Info Tables
            CREATE TABLE IF NOT EXISTS iex_collections (
                id INTEGER PRIMARY KEY,
                collection_name TEXT,
                symbol TEXT,
                fetch_date TEXT,
                UNIQUE(collection_name, symbol, fetch_date)
            );

            CREATE TABLE IF NOT EXISTS iex_earnings_today (
                id INTEGER PRIMARY KEY,
                symbol TEXT,
                consensus_eps REAL,
                estimated_eps REAL,
                actual_eps REAL,
                report_time TEXT,
                fetch_date TEXT,
                UNIQUE(symbol, report_time)
            );

            CREATE TABLE IF NOT EXISTS iex_ipo_calendar (
                id INTEGER PRIMARY KEY,
                symbol TEXT,
                company_name TEXT,
                expected_date TEXT,
                shares INTEGER,
                price_low REAL,
                price_high REAL,
                currency TEXT,
                exchange TEXT,
                fetch_date TEXT,
                UNIQUE(symbol, expected_date)
            );

            CREATE TABLE IF NOT EXISTS iex_sector_performance (
                id INTEGER PRIMARY KEY,
                sector TEXT,
                name TEXT,
                performance REAL,
                last_updated TEXT,
                fetch_date TEXT,
                UNIQUE(sector, last_updated)
            );

            -- News Tables
            CREATE TABLE IF NOT EXISTS iex_news (
                id INTEGER PRIMARY KEY,
                symbol TEXT,
                datetime TEXT,
                headline TEXT,
                source TEXT,
                url TEXT,
                summary TEXT,
                related TEXT,
                image TEXT,
                lang TEXT,
                has_paywall BOOLEAN,
                fetch_date TEXT,
                UNIQUE(symbol, datetime, headline)
            );

            -- Cryptocurrency Tables
            CREATE TABLE IF NOT EXISTS iex_crypto_quote (
                id INTEGER PRIMARY KEY,
                symbol TEXT,
                price REAL,
                volume INTEGER,
                market_cap REAL,
                timestamp TEXT,
                fetch_date TEXT,
                UNIQUE(symbol, timestamp)
            );

            -- Options Tables
            CREATE TABLE IF NOT EXISTS iex_options (
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
                fetch_date TEXT,
                UNIQUE(symbol, expiration_date, strike_price, option_type)
            );

            -- Reference Data Tables
            CREATE TABLE IF NOT EXISTS iex_international_symbols (
                id INTEGER PRIMARY KEY,
                symbol TEXT,
                exchange TEXT,
                name TEXT,
                date TEXT,
                type TEXT,
                iex_id TEXT,
                region TEXT,
                currency TEXT,
                is_enabled BOOLEAN,
                fetch_date TEXT,
                UNIQUE(symbol, exchange)
            );

            CREATE TABLE IF NOT EXISTS iex_holidays (
                id INTEGER PRIMARY KEY,
                date TEXT,
                exchange TEXT,
                name TEXT,
                status TEXT,
                fetch_date TEXT,
                UNIQUE(date, exchange)
            );

            -- Alternative Data Tables
            CREATE TABLE IF NOT EXISTS iex_social_sentiment (
                id INTEGER PRIMARY KEY,
                symbol TEXT,
                date TEXT,
                sentiment REAL,
                total_sentiment_score REAL,
                positive_score REAL,
                negative_score REAL,
                fetch_date TEXT,
                UNIQUE(symbol, date)
            );

            -- Account Tables
            CREATE TABLE IF NOT EXISTS iex_usage (
                id INTEGER PRIMARY KEY,
                date TEXT,
                messages_used INTEGER,
                messages_remaining INTEGER,
                fetch_date TEXT,
                UNIQUE(date)
            );

            -- Create indices for all tables
            CREATE INDEX IF NOT EXISTS idx_iex_advanced_stats_symbol ON iex_advanced_stats(symbol);
            CREATE INDEX IF NOT EXISTS idx_iex_insider_roster_symbol ON iex_insider_roster(symbol);
            CREATE INDEX IF NOT EXISTS idx_iex_insider_transactions_symbol ON iex_insider_transactions(symbol);
            CREATE INDEX IF NOT EXISTS idx_iex_largest_trades_symbol ON iex_largest_trades(symbol);
            CREATE INDEX IF NOT EXISTS idx_iex_volume_by_venue_symbol ON iex_volume_by_venue(symbol);
            CREATE INDEX IF NOT EXISTS idx_iex_collections_name ON iex_collections(collection_name);
            CREATE INDEX IF NOT EXISTS idx_iex_earnings_today_symbol ON iex_earnings_today(symbol);
            CREATE INDEX IF NOT EXISTS idx_iex_ipo_calendar_symbol ON iex_ipo_calendar(symbol);
            CREATE INDEX IF NOT EXISTS idx_iex_sector_performance_sector ON iex_sector_performance(sector);
            CREATE INDEX IF NOT EXISTS idx_iex_news_symbol ON iex_news(symbol);
            CREATE INDEX IF NOT EXISTS idx_iex_crypto_quote_symbol ON iex_crypto_quote(symbol);
            CREATE INDEX IF NOT EXISTS idx_iex_options_symbol ON iex_options(symbol);
            CREATE INDEX IF NOT EXISTS idx_iex_international_symbols_symbol ON iex_international_symbols(symbol);
            CREATE INDEX IF NOT EXISTS idx_iex_holidays_date ON iex_holidays(date);
            CREATE INDEX IF NOT EXISTS idx_iex_social_sentiment_symbol ON iex_social_sentiment(symbol);
            CREATE INDEX IF NOT EXISTS idx_iex_usage_date ON iex_usage(date);
        ''')
        
        conn.commit()
        conn.close()
        
    def _rate_limit(self):
        """Implement rate limiting to respect IEX API limits."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < (1.0 / self.requests_per_second):
            time.sleep((1.0 / self.requests_per_second) - time_since_last)
        self.last_request_time = time.time()
        
    def _get_last_update(self, table: str, symbol: str = None) -> Optional[datetime]:
        """Get the last update time for a symbol in a specific table."""
        conn = sqlite3.connect(self.db_path)
        try:
            query = f"SELECT MAX(fetch_date) FROM {table}"
            if symbol:
                query += f" WHERE symbol = ?"
                last_update = pd.read_sql(query, conn, params=[symbol])['MAX(fetch_date)'].iloc[0]
            else:
                last_update = pd.read_sql(query, conn)['MAX(fetch_date)'].iloc[0]
            return pd.to_datetime(last_update) if last_update else None
        finally:
            conn.close()
            
    def fetch_all_data(self, symbols: List[str], batch_size: int = 25, 
                      delay_between_batches: int = 1, test_mode: bool = False) -> int:
        """Fetch all available data types for the given symbols."""
        if test_mode:
            symbols = symbols[:25]
            
        success_count = 0
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            try:
                # Stocks/Equities data
                self._fetch_advanced_stats(batch)
                self._fetch_insider_roster(batch)
                self._fetch_insider_transactions(batch)
                self._fetch_largest_trades(batch)
                self._fetch_volume_by_venue(batch)
                
                # Market data
                self._fetch_collections(batch)
                self._fetch_earnings_today(batch)
                self._fetch_ipo_calendar()
                self._fetch_sector_performance()
                
                # News
                self._fetch_news(batch)
                
                # Cryptocurrency
                self._fetch_crypto_quote(batch)
                
                # Options
                self._fetch_options(batch)
                
                # Reference data
                self._fetch_international_symbols()
                self._fetch_holidays()
                
                # Alternative data
                self._fetch_social_sentiment(batch)
                
                # Account usage
                self._fetch_usage()
                
                success_count += len(batch)
                self.logger.info(f"Successfully processed batch of {len(batch)} symbols")
                
            except Exception as e:
                self.logger.error(f"Error processing batch: {str(e)}")
                continue
                
            if i + batch_size < len(symbols):
                time.sleep(delay_between_batches)
                
        return success_count

    def _fetch_advanced_stats(self, symbols: List[str]):
        """Fetch advanced statistics for symbols."""
        self._rate_limit()
        for symbol in symbols:
            try:
                stats = self._get_advanced_stats(symbol)
                if stats:
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO iex_advanced_stats 
                        (symbol, total_cash, current_debt, revenue, gross_profit,
                         total_revenue, ebitda, revenue_per_share, revenue_per_employee,
                         debt_to_equity, profit_margin, enterprise_value,
                         enterprise_value_to_revenue, price_to_sales, price_to_book,
                         forward_pe_ratio, peg_ratio, pe_high, pe_low, fetch_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        symbol,
                        stats.get('totalCash'),
                        stats.get('currentDebt'),
                        stats.get('revenue'),
                        stats.get('grossProfit'),
                        stats.get('totalRevenue'),
                        stats.get('EBITDA'),
                        stats.get('revenuePerShare'),
                        stats.get('revenuePerEmployee'),
                        stats.get('debtToEquity'),
                        stats.get('profitMargin'),
                        stats.get('enterpriseValue'),
                        stats.get('enterpriseValueToRevenue'),
                        stats.get('priceToSales'),
                        stats.get('priceToBook'),
                        stats.get('forwardPERatio'),
                        stats.get('pegRatio'),
                        stats.get('peHigh'),
                        stats.get('peLow'),
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    ))
                    conn.commit()
                    conn.close()
                    
            except Exception as e:
                self.logger.error(f"Error fetching advanced stats for {symbol}: {str(e)}")

    def _fetch_insider_roster(self, symbols: List[str]):
        """Fetch insider roster for symbols."""
        self._rate_limit()
        for symbol in symbols:
            try:
                roster = self._get_insider_roster(symbol)
                if roster:
                    records = []
                    for insider in roster:
                        records.append({
                            'symbol': symbol,
                            'name': insider.get('name'),
                            'title': insider.get('title'),
                            'fetch_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        })
                    
                    if records:
                        df = pd.DataFrame(records)
                        conn = sqlite3.connect(self.db_path)
                        df.to_sql('iex_insider_roster', conn, if_exists='append', index=False)
                        conn.close()
                        
            except Exception as e:
                self.logger.error(f"Error fetching insider roster for {symbol}: {str(e)}")

    def _fetch_insider_transactions(self, symbols: List[str]):
        """Fetch insider transactions for symbols."""
        self._rate_limit()
        for symbol in symbols:
            try:
                transactions = self._get_insider_transactions(symbol)
                if transactions:
                    records = []
                    for trans in transactions:
                        records.append({
                            'symbol': symbol,
                            'name': trans.get('name'),
                            'transaction_date': trans.get('transactionDate'),
                            'transaction_type': trans.get('transactionType'),
                            'shares': trans.get('shares'),
                            'price': trans.get('price'),
                            'value': trans.get('value'),
                            'fetch_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        })
                    
                    if records:
                        df = pd.DataFrame(records)
                        conn = sqlite3.connect(self.db_path)
                        df.to_sql('iex_insider_transactions', conn, if_exists='append', index=False)
                        conn.close()
                        
            except Exception as e:
                self.logger.error(f"Error fetching insider transactions for {symbol}: {str(e)}")

    def _fetch_largest_trades(self, symbols: List[str]):
        """Fetch largest trades for symbols."""
        self._rate_limit()
        for symbol in symbols:
            try:
                trades = self._get_largest_trades(symbol)
                if trades:
                    records = []
                    for trade in trades:
                        records.append({
                            'symbol': symbol,
                            'price': trade.get('price'),
                            'size': trade.get('size'),
                            'time': trade.get('time'),
                            'time_label': trade.get('timeLabel'),
                            'venue': trade.get('venue'),
                            'venue_name': trade.get('venueName'),
                            'fetch_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        })
                    
                    if records:
                        df = pd.DataFrame(records)
                        conn = sqlite3.connect(self.db_path)
                        df.to_sql('iex_largest_trades', conn, if_exists='append', index=False)
                        conn.close()
                        
            except Exception as e:
                self.logger.error(f"Error fetching largest trades for {symbol}: {str(e)}")

    def _fetch_volume_by_venue(self, symbols: List[str]):
        """Fetch volume by venue for symbols."""
        self._rate_limit()
        for symbol in symbols:
            try:
                venues = self._get_volume_by_venue(symbol)
                if venues:
                    records = []
                    for venue in venues:
                        records.append({
                            'symbol': symbol,
                            'venue': venue.get('venue'),
                            'venue_name': venue.get('venueName'),
                            'volume': venue.get('volume'),
                            'market_percent': venue.get('marketPercent'),
                            'avg_trade_size': venue.get('avgTradeSize'),
                            'fetch_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        })
                    
                    if records:
                        df = pd.DataFrame(records)
                        conn = sqlite3.connect(self.db_path)
                        df.to_sql('iex_volume_by_venue', conn, if_exists='append', index=False)
                        conn.close()
                        
            except Exception as e:
                self.logger.error(f"Error fetching volume by venue for {symbol}: {str(e)}")

    def _fetch_collections(self, symbols: List[str]):
        """Fetch collections for symbols."""
        self._rate_limit()
        collections = ['mostactive', 'gainers', 'losers', 'iexvolume', 'iexpercent']
        for collection in collections:
            try:
                data = self._get_collection(collection)
                if data:
                    records = []
                    for symbol in data:
                        records.append({
                            'collection_name': collection,
                            'symbol': symbol,
                            'fetch_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        })
                    
                    if records:
                        df = pd.DataFrame(records)
                        conn = sqlite3.connect(self.db_path)
                        df.to_sql('iex_collections', conn, if_exists='append', index=False)
                        conn.close()
                        
            except Exception as e:
                self.logger.error(f"Error fetching collection {collection}: {str(e)}")

    def _fetch_earnings_today(self, symbols: List[str]):
        """Fetch earnings calendar for today."""
        self._rate_limit()
        try:
            earnings = self._get_earnings_today()
            if earnings:
                records = []
                for earning in earnings:
                    records.append({
                        'symbol': earning.get('symbol'),
                        'consensus_eps': earning.get('consensusEPS'),
                        'estimated_eps': earning.get('estimatedEPS'),
                        'actual_eps': earning.get('actualEPS'),
                        'report_time': earning.get('reportTime'),
                        'fetch_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                
                if records:
                    df = pd.DataFrame(records)
                    conn = sqlite3.connect(self.db_path)
                    df.to_sql('iex_earnings_today', conn, if_exists='append', index=False)
                    conn.close()
                    
        except Exception as e:
            self.logger.error(f"Error fetching earnings today: {str(e)}")

    def _fetch_ipo_calendar(self):
        """Fetch IPO calendar."""
        self._rate_limit()
        try:
            ipos = self._get_ipo_calendar()
            if ipos:
                records = []
                for ipo in ipos:
                    records.append({
                        'symbol': ipo.get('symbol'),
                        'company_name': ipo.get('companyName'),
                        'expected_date': ipo.get('expectedDate'),
                        'shares': ipo.get('shares'),
                        'price_low': ipo.get('priceLow'),
                        'price_high': ipo.get('priceHigh'),
                        'currency': ipo.get('currency'),
                        'exchange': ipo.get('exchange'),
                        'fetch_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                
                if records:
                    df = pd.DataFrame(records)
                    conn = sqlite3.connect(self.db_path)
                    df.to_sql('iex_ipo_calendar', conn, if_exists='append', index=False)
                    conn.close()
                    
        except Exception as e:
            self.logger.error(f"Error fetching IPO calendar: {str(e)}")

    def _fetch_sector_performance(self):
        """Fetch sector performance."""
        self._rate_limit()
        try:
            sectors = self._get_sector_performance()
            if sectors:
                records = []
                for sector in sectors:
                    records.append({
                        'sector': sector.get('sector'),
                        'name': sector.get('name'),
                        'performance': sector.get('performance'),
                        'last_updated': sector.get('lastUpdated'),
                        'fetch_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                
                if records:
                    df = pd.DataFrame(records)
                    conn = sqlite3.connect(self.db_path)
                    df.to_sql('iex_sector_performance', conn, if_exists='append', index=False)
                    conn.close()
                    
        except Exception as e:
            self.logger.error(f"Error fetching sector performance: {str(e)}")

    def _fetch_news(self, symbols: List[str]):
        """Fetch news for symbols."""
        self._rate_limit()
        for symbol in symbols:
            try:
                news = self._get_news(symbol)
                if news:
                    records = []
                    for article in news:
                        records.append({
                            'symbol': symbol,
                            'datetime': article.get('datetime'),
                            'headline': article.get('headline'),
                            'source': article.get('source'),
                            'url': article.get('url'),
                            'summary': article.get('summary'),
                            'related': article.get('related'),
                            'image': article.get('image'),
                            'lang': article.get('lang'),
                            'has_paywall': article.get('hasPaywall'),
                            'fetch_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        })
                    
                    if records:
                        df = pd.DataFrame(records)
                        conn = sqlite3.connect(self.db_path)
                        df.to_sql('iex_news', conn, if_exists='append', index=False)
                        conn.close()
                        
            except Exception as e:
                self.logger.error(f"Error fetching news for {symbol}: {str(e)}")

    def _fetch_crypto_quote(self, symbols: List[str]):
        """Fetch cryptocurrency quotes."""
        self._rate_limit()
        for symbol in symbols:
            try:
                quote = self._get_crypto_quote(symbol)
                if quote:
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO iex_crypto_quote 
                        (symbol, price, volume, market_cap, timestamp, fetch_date)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        symbol,
                        quote.get('price'),
                        quote.get('volume'),
                        quote.get('marketCap'),
                        quote.get('timestamp'),
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    ))
                    conn.commit()
                    conn.close()
                    
            except Exception as e:
                self.logger.error(f"Error fetching crypto quote for {symbol}: {str(e)}")

    def _fetch_options(self, symbols: List[str]):
        """Fetch options data for symbols."""
        self._rate_limit()
        for symbol in symbols:
            try:
                options = self._get_options(symbol)
                if options:
                    records = []
                    for option in options:
                        records.append({
                            'symbol': symbol,
                            'expiration_date': option.get('expirationDate'),
                            'strike_price': option.get('strikePrice'),
                            'option_type': option.get('optionType'),
                            'last_price': option.get('lastPrice'),
                            'bid': option.get('bid'),
                            'ask': option.get('ask'),
                            'volume': option.get('volume'),
                            'open_interest': option.get('openInterest'),
                            'fetch_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        })
                    
                    if records:
                        df = pd.DataFrame(records)
                        conn = sqlite3.connect(self.db_path)
                        df.to_sql('iex_options', conn, if_exists='append', index=False)
                        conn.close()
                        
            except Exception as e:
                self.logger.error(f"Error fetching options for {symbol}: {str(e)}")

    def _fetch_international_symbols(self):
        """Fetch international symbols."""
        self._rate_limit()
        try:
            symbols = self._get_international_symbols()
            if symbols:
                records = []
                for symbol in symbols:
                    records.append({
                        'symbol': symbol.get('symbol'),
                        'exchange': symbol.get('exchange'),
                        'name': symbol.get('name'),
                        'date': symbol.get('date'),
                        'type': symbol.get('type'),
                        'iex_id': symbol.get('iexId'),
                        'region': symbol.get('region'),
                        'currency': symbol.get('currency'),
                        'is_enabled': symbol.get('isEnabled'),
                        'fetch_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                
                if records:
                    df = pd.DataFrame(records)
                    conn = sqlite3.connect(self.db_path)
                    df.to_sql('iex_international_symbols', conn, if_exists='append', index=False)
                    conn.close()
                    
        except Exception as e:
            self.logger.error(f"Error fetching international symbols: {str(e)}")

    def _fetch_holidays(self):
        """Fetch U.S. holidays and trading dates."""
        self._rate_limit()
        try:
            holidays = self._get_holidays()
            if holidays:
                records = []
                for holiday in holidays:
                    records.append({
                        'date': holiday.get('date'),
                        'exchange': holiday.get('exchange'),
                        'name': holiday.get('name'),
                        'status': holiday.get('status'),
                        'fetch_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                
                if records:
                    df = pd.DataFrame(records)
                    conn = sqlite3.connect(self.db_path)
                    df.to_sql('iex_holidays', conn, if_exists='append', index=False)
                    conn.close()
                    
        except Exception as e:
            self.logger.error(f"Error fetching holidays: {str(e)}")

    def _fetch_social_sentiment(self, symbols: List[str]):
        """Fetch social sentiment for symbols."""
        self._rate_limit()
        for symbol in symbols:
            try:
                sentiment = self._get_social_sentiment(symbol)
                if sentiment:
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO iex_social_sentiment 
                        (symbol, date, sentiment, total_sentiment_score,
                         positive_score, negative_score, fetch_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        symbol,
                        sentiment.get('date'),
                        sentiment.get('sentiment'),
                        sentiment.get('totalSentimentScore'),
                        sentiment.get('positiveScore'),
                        sentiment.get('negativeScore'),
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    ))
                    conn.commit()
                    conn.close()
                    
            except Exception as e:
                self.logger.error(f"Error fetching social sentiment for {symbol}: {str(e)}")

    def _fetch_usage(self):
        """Fetch account usage information."""
        self._rate_limit()
        try:
            usage = self._get_usage()
            if usage:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO iex_usage 
                    (date, messages_used, messages_remaining, fetch_date)
                    VALUES (?, ?, ?, ?)
                ''', (
                    usage.get('date'),
                    usage.get('messagesUsed'),
                    usage.get('messagesRemaining'),
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ))
                conn.commit()
                conn.close()
                
        except Exception as e:
            self.logger.error(f"Error fetching usage: {str(e)}") 