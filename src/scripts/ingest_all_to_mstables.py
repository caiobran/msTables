import os
import sqlite3
import pandas as pd
from pathlib import Path

# Directory containing the data files
DATA_DIR = Path('/Users/xavier/sbox/Financial_Data')
DB_PATH = Path('data/mstables.sqlite')

# Supported file extensions
CSV_EXTENSIONS = ['.csv']
EXCEL_EXTENSIONS = ['.xlsx', '.xlsm']
TXT_EXTENSIONS = ['.txt']


def sanitize_table_name(filename):
    """Sanitize filename to be a valid SQLite table name."""
    name = filename.lower().replace('.', '_').replace('-', '_')
    if name[0].isdigit():
        name = '_' + name
    return name


def ingest_file_to_sqlite(file_path, db_path):
    ext = file_path.suffix.lower()
    table_name = sanitize_table_name(file_path.stem)
    try:
        if ext in CSV_EXTENSIONS:
            df = pd.read_csv(file_path)
        elif ext in EXCEL_EXTENSIONS:
            df = pd.read_excel(file_path)
        elif ext in TXT_EXTENSIONS:
            df = pd.read_csv(file_path, sep='|')
        else:
            print(f"Skipping unsupported file: {file_path}")
            return
        if df.empty:
            print(f"Skipping empty file: {file_path}")
            return
        with sqlite3.connect(db_path) as conn:
            df.to_sql(table_name, conn, if_exists='replace', index=False)
        print(f"Ingested {file_path} into table {table_name}")
    except Exception as e:
        print(f"Failed to ingest {file_path}: {e}")


def main():
    for file in DATA_DIR.iterdir():
        if file.is_file():
            if file.suffix.lower() in CSV_EXTENSIONS + EXCEL_EXTENSIONS + TXT_EXTENSIONS:
                ingest_file_to_sqlite(file, DB_PATH)

if __name__ == '__main__':
    main() 