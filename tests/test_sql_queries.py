import pytest
import sqlite3
import pandas as pd
from pathlib import Path

class TestSQLQueries:
    def test_create_tables(self, temp_db):
        """Test table creation"""
        # Create tables
        with sqlite3.connect(temp_db) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sample_rules (
                    date TEXT,
                    avevol INTEGER,
                    yield REAL,
                    Dividend_Y10 REAL,
                    Rev_Growth_Y9 REAL,
                    OpeInc_Growth_Y9 REAL,
                    NetInc_Growth_Y9 REAL,
                    PE_TTM REAL,
                    PB_TTM REAL,
                    PS_TTM REAL,
                    PC_TTM REAL
                )
            """)
            
            # Verify table exists
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sample_rules'")
            assert cursor.fetchone() is not None
            
            # Verify columns
            cursor = conn.execute("PRAGMA table_info(sample_rules)")
            columns = [row[1] for row in cursor.fetchall()]
            assert all(col in columns for col in [
                'date', 'avevol', 'yield', 'Dividend_Y10', 'Rev_Growth_Y9',
                'OpeInc_Growth_Y9', 'NetInc_Growth_Y9', 'PE_TTM',
                'PB_TTM', 'PS_TTM', 'PC_TTM'
            ])

    def test_insert_data(self, temp_db):
        """Test data insertion"""
        # Create table
        with sqlite3.connect(temp_db) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sample_rules (
                    date TEXT,
                    avevol INTEGER,
                    yield REAL,
                    Dividend_Y10 REAL,
                    Rev_Growth_Y9 REAL,
                    OpeInc_Growth_Y9 REAL,
                    NetInc_Growth_Y9 REAL,
                    PE_TTM REAL,
                    PB_TTM REAL,
                    PS_TTM REAL,
                    PC_TTM REAL
                )
            """)
            
            # Insert test data
            conn.execute("""
                INSERT INTO sample_rules (
                    date, avevol, yield, Dividend_Y10, Rev_Growth_Y9,
                    OpeInc_Growth_Y9, NetInc_Growth_Y9, PE_TTM,
                    PB_TTM, PS_TTM, PC_TTM
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                '2024-01-01', 1000, 0.05, 1.0, 0.1,
                0.15, 0.12, 20.0, 2.0, 3.0, 4.0
            ))
            
            # Verify data was inserted
            cursor = conn.execute("SELECT * FROM sample_rules")
            row = cursor.fetchone()
            assert row is not None
            assert row[0] == '2024-01-01'  # date
            assert row[1] == 1000  # avevol
            assert row[2] == 0.05  # yield

    def test_select_data(self, temp_db):
        """Test data selection"""
        # Create and populate table
        with sqlite3.connect(temp_db) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sample_rules (
                    date TEXT,
                    avevol INTEGER,
                    yield REAL,
                    Dividend_Y10 REAL,
                    Rev_Growth_Y9 REAL,
                    OpeInc_Growth_Y9 REAL,
                    NetInc_Growth_Y9 REAL,
                    PE_TTM REAL,
                    PB_TTM REAL,
                    PS_TTM REAL,
                    PC_TTM REAL
                )
            """)
            
            # Insert test data
            conn.execute("""
                INSERT INTO sample_rules (
                    date, avevol, yield, Dividend_Y10, Rev_Growth_Y9,
                    OpeInc_Growth_Y9, NetInc_Growth_Y9, PE_TTM,
                    PB_TTM, PS_TTM, PC_TTM
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                '2024-01-01', 1000, 0.05, 1.0, 0.1,
                0.15, 0.12, 20.0, 2.0, 3.0, 4.0
            ))
            
            # Test basic select
            cursor = conn.execute("SELECT date, avevol, yield FROM sample_rules")
            row = cursor.fetchone()
            assert row is not None
            assert row[0] == '2024-01-01'
            assert row[1] == 1000
            assert row[2] == 0.05
            
            # Test where clause
            cursor = conn.execute("SELECT * FROM sample_rules WHERE yield > 0.04")
            row = cursor.fetchone()
            assert row is not None
            
            # Test order by
            cursor = conn.execute("SELECT * FROM sample_rules ORDER BY avevol DESC")
            row = cursor.fetchone()
            assert row is not None

    def test_update_data(self, temp_db):
        """Test data updates"""
        # Create and populate table
        with sqlite3.connect(temp_db) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sample_rules (
                    date TEXT,
                    avevol INTEGER,
                    yield REAL,
                    Dividend_Y10 REAL,
                    Rev_Growth_Y9 REAL,
                    OpeInc_Growth_Y9 REAL,
                    NetInc_Growth_Y9 REAL,
                    PE_TTM REAL,
                    PB_TTM REAL,
                    PS_TTM REAL,
                    PC_TTM REAL
                )
            """)
            
            # Insert test data
            conn.execute("""
                INSERT INTO sample_rules (
                    date, avevol, yield, Dividend_Y10, Rev_Growth_Y9,
                    OpeInc_Growth_Y9, NetInc_Growth_Y9, PE_TTM,
                    PB_TTM, PS_TTM, PC_TTM
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                '2024-01-01', 1000, 0.05, 1.0, 0.1,
                0.15, 0.12, 20.0, 2.0, 3.0, 4.0
            ))
            
            # Update data
            conn.execute("""
                UPDATE sample_rules
                SET yield = 0.06
                WHERE date = '2024-01-01'
            """)
            
            # Verify update
            cursor = conn.execute("SELECT yield FROM sample_rules WHERE date = '2024-01-01'")
            row = cursor.fetchone()
            assert row is not None
            assert row[0] == 0.06

    def test_delete_data(self, temp_db):
        """Test data deletion"""
        # Create and populate table
        with sqlite3.connect(temp_db) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sample_rules (
                    date TEXT,
                    avevol INTEGER,
                    yield REAL,
                    Dividend_Y10 REAL,
                    Rev_Growth_Y9 REAL,
                    OpeInc_Growth_Y9 REAL,
                    NetInc_Growth_Y9 REAL,
                    PE_TTM REAL,
                    PB_TTM REAL,
                    PS_TTM REAL,
                    PC_TTM REAL
                )
            """)
            
            # Insert test data
            conn.execute("""
                INSERT INTO sample_rules (
                    date, avevol, yield, Dividend_Y10, Rev_Growth_Y9,
                    OpeInc_Growth_Y9, NetInc_Growth_Y9, PE_TTM,
                    PB_TTM, PS_TTM, PC_TTM
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                '2024-01-01', 1000, 0.05, 1.0, 0.1,
                0.15, 0.12, 20.0, 2.0, 3.0, 4.0
            ))
            
            # Delete data
            conn.execute("DELETE FROM sample_rules WHERE date = '2024-01-01'")
            
            # Verify deletion
            cursor = conn.execute("SELECT COUNT(*) FROM sample_rules")
            count = cursor.fetchone()[0]
            assert count == 0 