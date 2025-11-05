import sqlite3
import pandas as pd
import logging
from pathlib import Path
import sys
import shutil
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('alphavantage_merge.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

class AlphavantageMerger:
    def __init__(self, 
                 source_db: str = 'mstables/data/mstables.sqlite',
                 target_db: str = 'data/mstables.sqlite',
                 backup_dir: str = 'data/backup'):
        self.source_db = source_db
        self.target_db = target_db
        self.backup_dir = backup_dir
        self.alphavantage_tables = [
            'alphavantage_intraday',
            'alphavantage_fundamentals',
            'alphavantage_daily'
        ]
        
    def backup_target_db(self) -> None:
        """Create a backup of the target database"""
        backup_path = Path(self.backup_dir) / f"mstables_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sqlite"
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.target_db, backup_path)
        logging.info(f"Created backup at: {backup_path}")
        
    def get_table_schema(self, conn: sqlite3.Connection, table: str) -> str:
        """Get the schema for a specific table"""
        cursor = conn.cursor()
        cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}';")
        return cursor.fetchone()[0]
        
    def create_table_if_not_exists(self, target_conn: sqlite3.Connection, source_conn: sqlite3.Connection, table: str) -> None:
        """Create table in target database if it doesn't exist"""
        schema = self.get_table_schema(source_conn, table)
        target_conn.execute(schema)
        target_conn.commit()
        logging.info(f"Created table {table} in target database")
        
    def merge_table_data(self, source_conn: sqlite3.Connection, target_conn: sqlite3.Connection, table: str) -> None:
        """Merge data from source table to target table"""
        # Get row count from source
        cursor = source_conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        row_count = cursor.fetchone()[0]
        
        if row_count == 0:
            logging.info(f"No data to merge for table {table}")
            return
            
        # Read data from source
        df = pd.read_sql_query(f"SELECT * FROM {table}", source_conn)
        
        # Insert into target
        df.to_sql(table, target_conn, if_exists='append', index=False)
        logging.info(f"Merged {len(df)} rows from {table}")
        
    def merge_alphavantage_data(self) -> None:
        """Merge Alphavantage tables from source to target database"""
        try:
            # Create backup
            self.backup_target_db()
            
            # Connect to both databases
            with sqlite3.connect(self.source_db) as source_conn, \
                 sqlite3.connect(self.target_db) as target_conn:
                
                for table in self.alphavantage_tables:
                    # Check if table exists in source
                    cursor = source_conn.cursor()
                    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}';")
                    if not cursor.fetchone():
                        logging.warning(f"Table {table} not found in source database")
                        continue
                        
                    # Create table in target if it doesn't exist
                    self.create_table_if_not_exists(target_conn, source_conn, table)
                    
                    # Merge data
                    self.merge_table_data(source_conn, target_conn, table)
                    
            logging.info("Successfully merged Alphavantage data")
            
        except Exception as e:
            logging.error(f"Error during merge: {str(e)}")
            raise
            
    def cleanup_source_db(self) -> None:
        """Remove the source database after successful merge"""
        try:
            Path(self.source_db).unlink()
            logging.info(f"Removed source database: {self.source_db}")
        except Exception as e:
            logging.error(f"Error removing source database: {str(e)}")
            
    def run(self) -> None:
        """Run the merge process"""
        try:
            self.merge_alphavantage_data()
            self.cleanup_source_db()
            logging.info("Process completed successfully")
        except Exception as e:
            logging.error(f"Process failed: {str(e)}")

if __name__ == "__main__":
    merger = AlphavantageMerger()
    merger.run() 