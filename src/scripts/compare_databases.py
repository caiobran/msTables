import sqlite3
import pandas as pd
from pathlib import Path

# Paths to the databases
INVESTING_DB = Path('/Users/xavier/sbox/Financial_Data/investing.sqlite')
MSTABLES_DB = Path('data/mstables.sqlite')


def get_tables(db_path):
    """Get a list of tables in the database."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        return [row[0] for row in cursor.fetchall()]


def compare_tables(investing_db, mstables_db):
    """Compare tables in investing.sqlite and mstables.sqlite to identify duplicates."""
    investing_tables = get_tables(investing_db)
    mstables_tables = get_tables(mstables_db)
    common_tables = set(investing_tables).intersection(set(mstables_tables))
    print("Common tables in both databases:", common_tables)
    for table in common_tables:
        with sqlite3.connect(investing_db) as conn_inv, sqlite3.connect(mstables_db) as conn_mst:
            df_inv = pd.read_sql(f"SELECT * FROM {table}", conn_inv)
            df_mst = pd.read_sql(f"SELECT * FROM {table}", conn_mst)
            if df_inv.equals(df_mst):
                print(f"Table {table} is identical in both databases.")
            else:
                print(f"Table {table} differs between databases.")


if __name__ == '__main__':
    compare_tables(INVESTING_DB, MSTABLES_DB) 