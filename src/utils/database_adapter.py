"""
Database Adapter

Supports both PostgreSQL (financial data) and SQLite (DandE.db)
Provides unified interface for database operations
"""

import sqlite3
import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
from typing import Optional, Dict, Any, List
import logging
from pathlib import Path
import os

logging.basicConfig(level=logging.INFO)


class DatabaseAdapter:
    """Unified database adapter for PostgreSQL and SQLite"""
    
    def __init__(self, db_type: str = "auto", **kwargs):
        """
        Initialize database adapter
        
        Args:
            db_type: "postgresql", "sqlite", or "auto" (auto-detect)
            **kwargs: Database connection parameters
        """
        self.db_type = db_type
        self.conn = None
        
        if db_type == "auto":
            self.db_type = self._detect_db_type(**kwargs)
        
        self._connect(**kwargs)
    
    def _detect_db_type(self, **kwargs) -> str:
        """Auto-detect database type from environment or kwargs"""
        # Check environment variables
        if os.getenv("FINANCIAL_DB_TYPE") == "postgresql":
            return "postgresql"
        if os.getenv("POSTGRES_HOST"):
            return "postgresql"
        
        # Check kwargs
        if "host" in kwargs or "postgres_host" in kwargs:
            return "postgresql"
        
        # Default to SQLite
        return "sqlite"
    
    def _connect(self, **kwargs):
        """Establish database connection"""
        if self.db_type == "postgresql":
            self._connect_postgresql(**kwargs)
        else:
            self._connect_sqlite(**kwargs)
    
    def _connect_postgresql(self, **kwargs):
        """Connect to PostgreSQL"""
        host = kwargs.get("host") or os.getenv("POSTGRES_HOST", "localhost")
        port = kwargs.get("port") or int(os.getenv("POSTGRES_PORT", "5432"))
        user = kwargs.get("user") or os.getenv("POSTGRES_USER", "mstables_user")
        password = kwargs.get("password") or os.getenv("POSTGRES_PASSWORD", "mstables_password")
        database = kwargs.get("database") or os.getenv("POSTGRES_DB", "mstables")
        
        self.conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database
        )
        self.conn.autocommit = False
        logging.info(f"Connected to PostgreSQL: {host}:{port}/{database}")
    
    def _connect_sqlite(self, **kwargs):
        """Connect to SQLite"""
        db_path = kwargs.get("db_path") or kwargs.get("database") or os.getenv("SQLITE_DB_PATH", "data/mstables.sqlite")
        
        # Create directory if needed
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        logging.info(f"Connected to SQLite: {db_path}")
    
    def execute(self, query: str, params: Optional[tuple] = None) -> Any:
        """Execute SQL query (works for both PostgreSQL and SQLite)"""
        if self.db_type == "postgresql":
            # PostgreSQL uses %s placeholders
            if params:
                # Convert SQLite-style ? placeholders to PostgreSQL %s
                query = query.replace("?", "%s")
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            return cursor
        else:
            # SQLite uses ? placeholders
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            return cursor
    
    def fetchone(self, query: str, params: Optional[tuple] = None) -> Optional[Dict[str, Any]]:
        """Fetch one row"""
        cursor = self.execute(query, params)
        row = cursor.fetchone()
        
        if row is None:
            return None
        
        if self.db_type == "postgresql":
            # Convert to dict
            if isinstance(row, tuple):
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            return dict(row)
        else:
            # SQLite Row already acts like dict
            return dict(row)
    
    def fetchall(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Fetch all rows"""
        cursor = self.execute(query, params)
        rows = cursor.fetchall()
        
        if self.db_type == "postgresql":
            # Convert to list of dicts
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            return [dict(zip(columns, row)) if isinstance(row, tuple) else dict(row) for row in rows]
        else:
            # SQLite Row already acts like dict
            return [dict(row) for row in rows]
    
    def commit(self):
        """Commit transaction"""
        self.conn.commit()
    
    def rollback(self):
        """Rollback transaction"""
        self.conn.rollback()
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logging.info(f"Closed {self.db_type} connection")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()


class FinancialDataDB(DatabaseAdapter):
    """Adapter for financial data (PostgreSQL)"""
    
    def __init__(self, **kwargs):
        super().__init__(db_type="postgresql", **kwargs)


class DandEDB(DatabaseAdapter):
    """Adapter for DandE.db (SQLite)"""
    
    def __init__(self, db_path: Optional[str] = None):
        db_path = db_path or os.getenv("DANDE_DB_PATH", "data/DandE.db")
        super().__init__(db_type="sqlite", db_path=db_path)

