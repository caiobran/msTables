"""
Database Merge Script

This script compares and merges data from mstables_050622.sqlite into mstables.sqlite,
keeping only unique and newer data.
"""

import sqlite3
import pandas as pd
from datetime import datetime
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/logs/db_merge.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('DBMerge')

class DatabaseMerger:
    def __init__(self, source_db: str, target_db: str):
        self.source_db = source_db
        self.target_db = target_db
        self.source_conn = None
        self.target_conn = None
    
    def connect(self):
        """Connect to both databases."""
        try:
            self.source_conn = sqlite3.connect(self.source_db)
            self.target_conn = sqlite3.connect(self.target_db)
            logger.info("Successfully connected to both databases")
        except sqlite3.Error as e:
            logger.error(f"Database connection error: {e}")
            raise
    
    def close(self):
        """Close database connections."""
        if self.source_conn:
            self.source_conn.close()
        if self.target_conn:
            self.target_conn.close()
    
    def get_tables(self, conn) -> list:
        """Get list of tables in a database."""
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        return [row[0] for row in cursor.fetchall()]
    
    def get_table_schema(self, conn, table: str) -> str:
        """Get schema for a table."""
        cursor = conn.cursor()
        cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}';")
        return cursor.fetchone()[0]
    
    def compare_tables(self) -> dict:
        """Compare tables between source and target databases."""
        source_tables = set(self.get_tables(self.source_conn))
        target_tables = set(self.get_tables(self.target_conn))
        
        return {
            'common': source_tables.intersection(target_tables),
            'source_only': source_tables - target_tables,
            'target_only': target_tables - source_tables
        }
    
    def get_row_count(self, conn, table: str) -> int:
        """Get number of rows in a table."""
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table};")
        return cursor.fetchone()[0]
    
    def merge_table(self, table: str):
        """Merge data from source table to target table."""
        try:
            # Get schema for both tables
            source_schema = self.get_table_schema(self.source_conn, table)
            target_schema = self.get_table_schema(self.target_conn, table)
            
            if source_schema != target_schema:
                logger.warning(f"Schema mismatch for table {table}")
                return
            
            # Get data from source
            source_df = pd.read_sql(f"SELECT * FROM {table}", self.source_conn)
            
            if source_df.empty:
                logger.info(f"No data in source table {table}")
                return
            
            # Get existing data from target
            target_df = pd.read_sql(f"SELECT * FROM {table}", self.target_conn)
            
            # Merge data
            if target_df.empty:
                # If target is empty, just insert all source data
                source_df.to_sql(table, self.target_conn, if_exists='append', index=False)
                logger.info(f"Inserted {len(source_df)} rows into {table}")
            else:
                # For tables with date columns, keep newer data
                date_columns = [col for col in source_df.columns if 'date' in col.lower()]
                
                if date_columns:
                    # Merge based on date columns
                    merged_df = pd.concat([target_df, source_df])
                    merged_df = merged_df.sort_values(by=date_columns, ascending=False)
                    merged_df = merged_df.drop_duplicates(subset=[col for col in source_df.columns if col not in date_columns])
                    
                    # Clear target table and insert merged data
                    self.target_conn.execute(f"DELETE FROM {table}")
                    merged_df.to_sql(table, self.target_conn, if_exists='append', index=False)
                    logger.info(f"Merged {len(merged_df)} rows into {table}")
                else:
                    # For tables without date columns, keep unique rows
                    merged_df = pd.concat([target_df, source_df])
                    merged_df = merged_df.drop_duplicates()
                    
                    # Clear target table and insert merged data
                    self.target_conn.execute(f"DELETE FROM {table}")
                    merged_df.to_sql(table, self.target_conn, if_exists='append', index=False)
                    logger.info(f"Merged {len(merged_df)} rows into {table}")
            
            self.target_conn.commit()
            
        except Exception as e:
            logger.error(f"Error merging table {table}: {e}")
            self.target_conn.rollback()
    
    def merge_all_tables(self):
        """Merge all common tables."""
        table_comparison = self.compare_tables()
        
        logger.info("Starting database merge...")
        logger.info(f"Common tables: {len(table_comparison['common'])}")
        logger.info(f"Tables only in source: {len(table_comparison['source_only'])}")
        logger.info(f"Tables only in target: {len(table_comparison['target_only'])}")
        
        # Merge common tables
        for table in table_comparison['common']:
            logger.info(f"Processing table: {table}")
            self.merge_table(table)
        
        # Create tables that only exist in source
        for table in table_comparison['source_only']:
            logger.info(f"Creating table from source: {table}")
            try:
                # Get schema and data from source
                schema = self.get_table_schema(self.source_conn, table)
                self.target_conn.execute(schema)
                
                # Copy data
                source_df = pd.read_sql(f"SELECT * FROM {table}", self.source_conn)
                source_df.to_sql(table, self.target_conn, if_exists='append', index=False)
                
                self.target_conn.commit()
                logger.info(f"Created and populated table {table}")
            except Exception as e:
                logger.error(f"Error creating table {table}: {e}")
                self.target_conn.rollback()

def main():
    # Create necessary directories
    Path('data/logs').mkdir(parents=True, exist_ok=True)
    
    # Initialize merger
    merger = DatabaseMerger(
        source_db='/Users/xavier/sbox/data_bases/mstables_050622.sqlite',
        target_db='data/mstables.sqlite'
    )
    
    try:
        # Connect to databases
        merger.connect()
        
        # Merge tables
        merger.merge_all_tables()
        
        logger.info("Database merge completed successfully")
    
    except Exception as e:
        logger.error(f"Error during database merge: {e}")
    
    finally:
        merger.close()

if __name__ == "__main__":
    main() 