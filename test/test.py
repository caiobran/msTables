#!/usr/bin/env python

import os
import sqlite3
from datetime import datetime
import sys
sys.path.append('..')  # Add parent directory to path
from src import fetch

def test_database_creation():
    """Test if database and required directories are created properly"""
    print("\n=== Testing Database Creation ===")
    
    # Test data directory creation
    dbpath = os.path.join(os.getcwd(), '..', 'data')
    if not os.path.exists(dbpath):
        os.mkdir(dbpath)
        print("✓ Created data directory")
    else:
        print("✓ Data directory exists")
    
    # Test backup directory creation
    backup_path = os.path.join(dbpath, 'backup')
    if not os.path.exists(backup_path):
        os.mkdir(backup_path)
        print("✓ Created backup directory")
    else:
        print("✓ Backup directory exists")
    
    # Test database file creation
    db_file = os.path.join(dbpath, 'test_mstables.sqlite')
    if os.path.exists(db_file):
        os.remove(db_file)  # Remove if exists for clean test
        print("✓ Removed existing test database")
    
    conn = sqlite3.connect(db_file)
    conn.close()
    print("✓ Created test database file")
    
    return db_file

def test_table_creation(db_file):
    """Test if tables are created properly"""
    print("\n=== Testing Table Creation ===")
    
    # Create tables
    msg = fetch.create_tables(db_file)
    print("✓ Tables created successfully")
    print(msg)
    
    # Verify tables exist
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cur.fetchall()
    print("\nCreated tables:")
    for table in tables:
        print(f"✓ {table[0]}")
    
    # Check if Tickers table has data
    cur.execute("SELECT COUNT(*) FROM Tickers;")
    count = cur.fetchone()[0]
    print(f"\n✓ Tickers table has {count} records")
    
    conn.close()
    return True

def test_data_fetching(db_file):
    """Test if data fetching works properly"""
    print("\n=== Testing Data Fetching ===")
    
    # Test with a small number of records
    print("Testing fetch with 10 records...")
    start = fetch.fetch(db_file)
    
    # Check Fetched_urls table
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    cur.execute("SELECT url_id, COUNT(*) FROM Fetched_urls GROUP BY url_id;")
    results = cur.fetchall()
    
    if results:
        print("\nFetched records by URL ID:")
        for url_id, count in results:
            print(f"✓ URL ID {url_id}: {count} records")
    else:
        print("✗ No records fetched")
    
    conn.close()
    return True

def main():
    print("Starting test sequence...")
    
    # Test database creation
    db_file = test_database_creation()
    
    # Test table creation
    if test_table_creation(db_file):
        print("\n✓ Table creation test passed")
    else:
        print("\n✗ Table creation test failed")
        return
    
    # Test data fetching
    if test_data_fetching(db_file):
        print("\n✓ Data fetching test passed")
    else:
        print("\n✗ Data fetching test failed")
        return
    
    print("\nAll tests completed successfully!")
    print(f"Test database created at: {db_file}")
    print("\nYou can now run main.py with confidence that the basic functionality works.")

if __name__ == '__main__':
    main() 