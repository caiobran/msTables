import sqlite3
import pandas as pd
import logging
from pathlib import Path
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

class CBOEFetcher:
    """Fetcher for CBOE market data including VIX futures, circuit breakers, and market statistics."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize the CBOE fetcher.
        
        Args:
            db_path: Path to SQLite database. If None, uses default path.
        """
        self.db_path = db_path or 'data/market_data.db'
        self._create_tables()
    
    def _create_tables(self):
        """Create necessary database tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # VIX futures data table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cboe_vix_futures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume INTEGER,
                    open_interest INTEGER,
                    settlement_price REAL,
                    last_updated TEXT,
                    UNIQUE(date, symbol)
                )
            """)
            
            # Circuit breaker data table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cboe_circuit_breakers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    level INTEGER,
                    trigger_price REAL,
                    trigger_time TEXT,
                    recovery_time TEXT,
                    market TEXT,
                    last_updated TEXT,
                    UNIQUE(date, level, market)
                )
            """)
            
            # Market statistics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cboe_market_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    market TEXT NOT NULL,
                    total_volume INTEGER,
                    advancers INTEGER,
                    decliners INTEGER,
                    unchanged INTEGER,
                    new_highs INTEGER,
                    new_lows INTEGER,
                    put_call_ratio REAL,
                    vix REAL,
                    last_updated TEXT,
                    UNIQUE(date, market)
                )
            """)
            
            # Create indices for common queries
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_vix_futures_date ON cboe_vix_futures(date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_vix_futures_symbol ON cboe_vix_futures(symbol)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_circuit_breakers_date ON cboe_circuit_breakers(date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_market_stats_date ON cboe_market_stats(date)')
            
            conn.commit()
            logger.info("CBOE database tables created successfully")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error creating CBOE tables: {str(e)}")
            raise
        finally:
            conn.close()
    
    def ingest_vix_futures(self, data_path: str):
        """Ingest VIX futures data from CSV file.
        
        Args:
            data_path: Path to VIX futures CSV file
        """
        try:
            df = pd.read_csv(data_path)
            conn = sqlite3.connect(self.db_path)
            
            # Ensure required columns exist
            required_cols = ['date', 'symbol', 'open', 'high', 'low', 'close', 'volume', 'open_interest']
            if not all(col in df.columns for col in required_cols):
                raise ValueError(f"CSV must contain columns: {required_cols}")
            
            # Add last_updated timestamp
            df['last_updated'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Write to database
            df.to_sql('cboe_vix_futures', conn, if_exists='append', index=False)
            logger.info(f"Successfully ingested VIX futures data from {data_path}")
            
        except Exception as e:
            logger.error(f"Error ingesting VIX futures data: {str(e)}")
            raise
        finally:
            conn.close()
    
    def ingest_circuit_breakers(self, data_path: str):
        """Ingest circuit breaker data from CSV file.
        
        Args:
            data_path: Path to circuit breaker CSV file
        """
        try:
            df = pd.read_csv(data_path)
            conn = sqlite3.connect(self.db_path)
            
            # Ensure required columns exist
            required_cols = ['date', 'level', 'trigger_price', 'trigger_time', 'market']
            if not all(col in df.columns for col in required_cols):
                raise ValueError(f"CSV must contain columns: {required_cols}")
            
            # Add last_updated timestamp
            df['last_updated'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Write to database
            df.to_sql('cboe_circuit_breakers', conn, if_exists='append', index=False)
            logger.info(f"Successfully ingested circuit breaker data from {data_path}")
            
        except Exception as e:
            logger.error(f"Error ingesting circuit breaker data: {str(e)}")
            raise
        finally:
            conn.close()
    
    def ingest_market_stats(self, data_path: str):
        """Ingest market statistics data from CSV file.
        
        Args:
            data_path: Path to market statistics CSV file
        """
        try:
            df = pd.read_csv(data_path)
            conn = sqlite3.connect(self.db_path)
            
            # Ensure required columns exist
            required_cols = ['date', 'market', 'total_volume', 'advancers', 'decliners', 'put_call_ratio']
            if not all(col in df.columns for col in required_cols):
                raise ValueError(f"CSV must contain columns: {required_cols}")
            
            # Add last_updated timestamp
            df['last_updated'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Write to database
            df.to_sql('cboe_market_stats', conn, if_exists='append', index=False)
            logger.info(f"Successfully ingested market statistics data from {data_path}")
            
        except Exception as e:
            logger.error(f"Error ingesting market statistics data: {str(e)}")
            raise
        finally:
            conn.close() 