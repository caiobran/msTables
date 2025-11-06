"""
PostgreSQL Database Tests

Tests for PostgreSQL financial data storage:
- Connection management
- Query execution
- Transaction handling
- Performance
- Concurrent access
- Data integrity
"""

import pytest
import time
from pathlib import Path
import os

from src.utils.database_adapter import FinancialDataDB


class TestPostgreSQLConnection:
    """Test PostgreSQL connection management"""
    
    def test_postgresql_connect(self):
        """Test basic PostgreSQL connection"""
        db = FinancialDataDB()
        assert db.conn is not None
        assert db.db_type == "postgresql"
        db.close()
    
    def test_postgresql_execute_query(self):
        """Test executing SQL queries"""
        db = FinancialDataDB()
        result = db.fetchone("SELECT 1 as test")
        assert result is not None
        assert result['test'] == 1
        db.close()
    
    def test_postgresql_fetchall(self):
        """Test fetching multiple rows"""
        db = FinancialDataDB()
        results = db.fetchall("SELECT generate_series(1, 5) as num")
        assert len(results) == 5
        assert results[0]['num'] == 1
        assert results[4]['num'] == 5
        db.close()
    
    def test_postgresql_transaction(self):
        """Test transaction handling"""
        db = FinancialDataDB()
        
        # Create test table
        db.execute("""
            CREATE TABLE IF NOT EXISTS test_transaction (
                id SERIAL PRIMARY KEY,
                value TEXT
            )
        """)
        db.commit()
        
        # Insert data
        db.execute("INSERT INTO test_transaction (value) VALUES (%s)", ("test",))
        db.commit()
        
        # Verify insert
        result = db.fetchone("SELECT * FROM test_transaction WHERE value = %s", ("test",))
        assert result is not None
        assert result['value'] == "test"
        
        # Rollback test
        db.execute("INSERT INTO test_transaction (value) VALUES (%s)", ("rollback",))
        db.rollback()
        
        # Verify rollback
        result = db.fetchone("SELECT * FROM test_transaction WHERE value = %s", ("rollback",))
        assert result is None
        
        # Cleanup
        db.execute("DROP TABLE IF EXISTS test_transaction")
        db.commit()
        db.close()
    
    def test_postgresql_connection_pooling(self):
        """Test connection pooling (multiple connections)"""
        connections = []
        for i in range(5):
            db = FinancialDataDB()
            connections.append(db)
            result = db.fetchone("SELECT %s as test", (i,))
            assert result['test'] == i
        
        for db in connections:
            db.close()


class TestPostgreSQLFinancialData:
    """Test PostgreSQL financial data operations"""
    
    def test_create_stock_prices_table(self):
        """Test creating stock_prices table"""
        db = FinancialDataDB()
        
        db.execute("""
            CREATE TABLE IF NOT EXISTS stock_prices (
                symbol TEXT,
                date DATE,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume BIGINT,
                adj_close REAL,
                PRIMARY KEY (symbol, date)
            )
        """)
        db.commit()
        
        # Verify table exists
        result = db.fetchone("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'stock_prices'
            )
        """)
        assert result['exists'] is True
        
        # Cleanup
        db.execute("DROP TABLE IF EXISTS stock_prices")
        db.commit()
        db.close()
    
    def test_insert_stock_price(self):
        """Test inserting stock price data"""
        db = FinancialDataDB()
        
        # Create table
        db.execute("""
            CREATE TABLE IF NOT EXISTS stock_prices (
                symbol TEXT,
                date DATE,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume BIGINT,
                adj_close REAL,
                PRIMARY KEY (symbol, date)
            )
        """)
        db.commit()
        
        # Insert data
        db.execute("""
            INSERT INTO stock_prices (symbol, date, open, high, low, close, volume, adj_close)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, ("AAPL", "2024-01-01", 100.0, 105.0, 95.0, 102.0, 1000000, 102.0))
        db.commit()
        
        # Verify insert
        result = db.fetchone(
            "SELECT * FROM stock_prices WHERE symbol = %s AND date = %s",
            ("AAPL", "2024-01-01")
        )
        assert result is not None
        assert result['symbol'] == "AAPL"
        assert result['close'] == 102.0
        
        # Cleanup
        db.execute("DROP TABLE IF EXISTS stock_prices")
        db.commit()
        db.close()
    
    def test_bulk_insert_performance(self):
        """Test bulk insert performance"""
        db = FinancialDataDB()
        
        # Create table
        db.execute("""
            CREATE TABLE IF NOT EXISTS stock_prices_test (
                symbol TEXT,
                date DATE,
                close REAL,
                PRIMARY KEY (symbol, date)
            )
        """)
        db.commit()
        
        # Bulk insert
        start_time = time.time()
        for i in range(1000):
            db.execute("""
                INSERT INTO stock_prices_test (symbol, date, close)
                VALUES (%s, %s, %s)
                ON CONFLICT (symbol, date) DO UPDATE SET close = EXCLUDED.close
            """, (f"SYM{i%100}", f"2024-01-{(i%30)+1:02d}", 100.0 + i))
        
        db.commit()
        duration = time.time() - start_time
        
        # Verify insert
        result = db.fetchone("SELECT COUNT(*) as count FROM stock_prices_test")
        assert result['count'] == 1000
        
        # Cleanup
        db.execute("DROP TABLE IF EXISTS stock_prices_test")
        db.commit()
        db.close()
        
        # Performance assertion (should be < 5 seconds for 1000 inserts)
        assert duration < 5.0


class TestPostgreSQLPerformance:
    """Test PostgreSQL performance"""
    
    def test_query_performance(self):
        """Test query performance"""
        db = FinancialDataDB()
        
        # Create test data
        db.execute("""
            CREATE TABLE IF NOT EXISTS performance_test (
                id SERIAL PRIMARY KEY,
                value REAL
            )
        """)
        db.commit()
        
        # Insert test data
        for i in range(10000):
            db.execute("INSERT INTO performance_test (value) VALUES (%s)", (i * 1.5,))
        db.commit()
        
        # Test query performance
        start_time = time.time()
        results = db.fetchall("SELECT * FROM performance_test WHERE value > %s", (5000,))
        duration = time.time() - start_time
        
        assert len(results) > 0
        assert duration < 1.0  # Should complete in < 1 second
        
        # Cleanup
        db.execute("DROP TABLE IF EXISTS performance_test")
        db.commit()
        db.close()
    
    def test_index_performance(self):
        """Test index performance impact"""
        db = FinancialDataDB()
        
        # Create table without index
        db.execute("""
            CREATE TABLE IF NOT EXISTS index_test (
                symbol TEXT,
                date DATE,
                value REAL
            )
        """)
        db.commit()
        
        # Insert data
        for i in range(1000):
            db.execute(
                "INSERT INTO index_test (symbol, date, value) VALUES (%s, %s, %s)",
                (f"SYM{i%100}", f"2024-01-{(i%30)+1:02d}", i * 1.5)
            )
        db.commit()
        
        # Query without index
        start_time = time.time()
        results = db.fetchall("SELECT * FROM index_test WHERE symbol = %s", ("SYM50",))
        duration_no_index = time.time() - start_time
        
        # Create index
        db.execute("CREATE INDEX idx_symbol ON index_test(symbol)")
        db.commit()
        
        # Query with index
        start_time = time.time()
        results = db.fetchall("SELECT * FROM index_test WHERE symbol = %s", ("SYM50",))
        duration_with_index = time.time() - start_time
        
        # Index should improve performance (or at least not hurt)
        assert duration_with_index <= duration_no_index * 1.5
        
        # Cleanup
        db.execute("DROP TABLE IF EXISTS index_test")
        db.commit()
        db.close()

