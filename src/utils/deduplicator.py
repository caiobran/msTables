import pandas as pd
import sqlite3
import logging
import sys
from pathlib import Path
import hashlib
from datetime import datetime
import os
from typing import List, Dict

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/deduplication.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

class Deduplicator:
    def __init__(self, 
                 db_path: str = 'data/mstables.sqlite',
                 file_paths: List[str] = None):
        self.db_path = db_path
        self.file_paths = file_paths or []
        self._init_db()
        
    def _init_db(self) -> None:
        """Initialize the deleted_files table if it doesn't exist"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Drop existing table if it exists
                conn.execute("DROP TABLE IF EXISTS deleted_files")
                
                # Create new table with all columns
                conn.execute("""
                    CREATE TABLE deleted_files (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_path TEXT NOT NULL,
                        file_hash TEXT NOT NULL,
                        file_size INTEGER NOT NULL,
                        deleted_at TIMESTAMP NOT NULL,
                        reason TEXT,
                        sequence_number INTEGER,
                        original_location TEXT,
                        file_type TEXT,
                        UNIQUE(file_hash)
                    )
                """)
                conn.commit()
            logging.info("Initialized deleted_files table")
        except Exception as e:
            logging.error(f"Error initializing database: {str(e)}")
            raise
            
    def compute_blake2_hash(self, file_path: Path) -> str:
        """Compute BLAKE2 hash of a file"""
        try:
            blake2 = hashlib.blake2b()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    blake2.update(chunk)
            return blake2.hexdigest()
        except Exception as e:
            logging.error(f"Error computing hash: {str(e)}")
            raise
            
    def is_file_deleted(self, file_hash: str) -> bool:
        """Check if a file hash exists in deleted_files table"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT 1 FROM deleted_files WHERE file_hash = ?",
                    (file_hash,)
                )
                return cursor.fetchone() is not None
        except Exception as e:
            logging.error(f"Error checking deleted files: {str(e)}")
            raise
            
    def get_next_sequence(self) -> int:
        """Get the next sequence number"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT MAX(sequence_number) FROM deleted_files"
                )
                max_seq = cursor.fetchone()[0]
                return (max_seq or 0) + 1
        except Exception as e:
            logging.error(f"Error getting sequence number: {str(e)}")
            raise
            
    def log_deleted_file(self, file_path: Path, file_hash: str, reason: str) -> None:
        """Log a deleted file to the database"""
        try:
            sequence = self.get_next_sequence()
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO deleted_files 
                    (file_path, file_hash, file_size, deleted_at, reason, 
                     sequence_number, original_location, file_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(file_path),
                        file_hash,
                        file_path.stat().st_size,
                        datetime.now().isoformat(),
                        reason,
                        sequence,
                        str(file_path.parent),
                        file_path.suffix.lower()
                    )
                )
                conn.commit()
            logging.info(f"Logged deleted file: {file_path} (sequence: {sequence})")
        except Exception as e:
            logging.error(f"Error logging deleted file: {str(e)}")
            raise
            
    def verify_data_in_db(self, file_path: Path) -> bool:
        """Verify if the data from the file is already in the database"""
        try:
            # Read the CSV file
            df_csv = pd.read_csv(file_path)
            
            # Get the first column (should be DATE)
            date_col = df_csv.columns[0]
            
            # Get unique dates from CSV
            csv_dates = set(pd.to_datetime(df_csv[date_col]).dt.date)
            
            # Tables to check for data
            tables_to_check = [
                'tiingo_prices',
                'pot_stocks',
                'sample_rules',
                'metal_prices'
            ]
            
            # Get unique dates from all relevant tables
            with sqlite3.connect(self.db_path) as conn:
                db_dates = set()
                for table in tables_to_check:
                    try:
                        table_dates = pd.read_sql_query(
                            f"SELECT DISTINCT date FROM {table}",
                            conn
                        )['date'].apply(lambda x: pd.to_datetime(x).date())
                        db_dates.update(table_dates)
                    except sqlite3.OperationalError:
                        logging.warning(f"Table {table} does not exist or has no date column")
                        continue
            
            # Check if all CSV dates are in the database
            missing_dates = csv_dates - db_dates
            if missing_dates:
                logging.info(f"Found {len(missing_dates)} dates not in database")
                return False
                
            logging.info("All data from file is present in database")
            return True
            
        except Exception as e:
            logging.error(f"Error verifying data: {str(e)}")
            return False
            
    def process_file(self, file_path: Path) -> None:
        """Process a file for deduplication"""
        try:
            if not file_path.exists():
                logging.error(f"File not found: {file_path}")
                return
                
            # Compute file hash
            file_hash = self.compute_blake2_hash(file_path)
            logging.info(f"Computed BLAKE2 hash: {file_hash}")
            
            # Check if file was previously deleted
            if self.is_file_deleted(file_hash):
                logging.info(f"File was previously deleted: {file_path}")
                return
                
            # Verify data is in database
            if self.verify_data_in_db(file_path):
                # Log and delete the file
                self.log_deleted_file(
                    file_path,
                    file_hash,
                    "Data already present in database"
                )
                os.remove(file_path)
                logging.info(f"Deleted file: {file_path}")
            else:
                logging.info(f"File contains new data, keeping: {file_path}")
                
        except Exception as e:
            logging.error(f"Error processing file: {str(e)}")
            raise
            
    def run(self) -> None:
        """Run the deduplication process"""
        try:
            # Process all files in sequence
            for file_path in self.file_paths:
                self.process_file(Path(file_path))
            logging.info("Deduplication process completed")
        except Exception as e:
            logging.error(f"Process failed: {str(e)}")
            raise

if __name__ == "__main__":
    # List of files we've processed today
    files_to_process = [
        'data/data_stocks.csv',  # Main stock data file
        'data/mstables.sqlite',  # Main database
        'data/financial_DB_2925.sqlite',  # Financial database
        'input/pot_stocks.json',  # Pot stocks data
        'input/api00.json',  # API configuration
        'input/ms_sal-quote-*.xml',  # Sitemaps
        'input/sql_cmd/select_notupdated*.txt',  # SQL queries
        'doc/pot_stocks.ods'  # Pot stocks documentation
    ]
    
    deduplicator = Deduplicator(file_paths=files_to_process)
    deduplicator.run() 