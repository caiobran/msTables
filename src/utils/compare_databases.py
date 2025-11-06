import sqlite3
import pandas as pd
from typing import Dict, List, Tuple
import logging
from pathlib import Path
import sys
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('database_comparison.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

class DatabaseComparer:
    def __init__(self, db1_path: str, db2_path: str):
        self.db1_path = db1_path
        self.db2_path = db2_path
        self.conn1 = None
        self.conn2 = None
        
    def __enter__(self):
        self.conn1 = sqlite3.connect(self.db1_path)
        self.conn2 = sqlite3.connect(self.db2_path)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn1:
            self.conn1.close()
        if self.conn2:
            self.conn2.close()
            
    def get_tables(self, conn: sqlite3.Connection) -> List[str]:
        """Get list of tables in the database"""
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        return [table[0] for table in cursor.fetchall()]
    
    def get_table_schema(self, conn: sqlite3.Connection, table: str) -> str:
        """Get the schema for a specific table"""
        cursor = conn.cursor()
        cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}';")
        return cursor.fetchone()[0]
    
    def get_row_count(self, conn: sqlite3.Connection, table: str) -> int:
        """Get the number of rows in a table"""
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table};")
        return cursor.fetchone()[0]
    
    def get_sample_data(self, conn: sqlite3.Connection, table: str, limit: int = 5) -> pd.DataFrame:
        """Get a sample of data from a table"""
        return pd.read_sql_query(f"SELECT * FROM {table} LIMIT {limit}", conn)
    
    def compare_table_structures(self) -> Dict[str, Dict]:
        """Compare the structure of tables between the two databases"""
        tables1 = set(self.get_tables(self.conn1))
        tables2 = set(self.get_tables(self.conn2))
        
        all_tables = tables1.union(tables2)
        comparison = {}
        
        for table in all_tables:
            comparison[table] = {
                'in_db1': table in tables1,
                'in_db2': table in tables2,
                'schema_match': False,
                'row_count_db1': 0,
                'row_count_db2': 0
            }
            
            if table in tables1 and table in tables2:
                schema1 = self.get_table_schema(self.conn1, table)
                schema2 = self.get_table_schema(self.conn2, table)
                comparison[table]['schema_match'] = schema1 == schema2
                comparison[table]['row_count_db1'] = self.get_row_count(self.conn1, table)
                comparison[table]['row_count_db2'] = self.get_row_count(self.conn2, table)
            elif table in tables1:
                comparison[table]['row_count_db1'] = self.get_row_count(self.conn1, table)
            elif table in tables2:
                comparison[table]['row_count_db2'] = self.get_row_count(self.conn2, table)
                
        return comparison
    
    def print_comparison(self, comparison: Dict[str, Dict]) -> None:
        """Print the comparison results"""
        logging.info(f"\nComparing databases:")
        logging.info(f"DB1: {self.db1_path}")
        logging.info(f"DB2: {self.db2_path}\n")
        
        # Print table comparison
        logging.info("Table Comparison:")
        logging.info("-" * 80)
        logging.info(f"{'Table Name':<30} {'In DB1':<10} {'In DB2':<10} {'Schema Match':<15} {'Rows DB1':<10} {'Rows DB2':<10}")
        logging.info("-" * 80)
        
        for table, stats in comparison.items():
            logging.info(f"{table:<30} {str(stats['in_db1']):<10} {str(stats['in_db2']):<10} "
                        f"{str(stats['schema_match']):<15} {stats['row_count_db1']:<10} {stats['row_count_db2']:<10}")
        
        # Print summary
        logging.info("\nSummary:")
        logging.info("-" * 80)
        tables_only_in_db1 = sum(1 for stats in comparison.values() if stats['in_db1'] and not stats['in_db2'])
        tables_only_in_db2 = sum(1 for stats in comparison.values() if stats['in_db2'] and not stats['in_db1'])
        tables_in_both = sum(1 for stats in comparison.values() if stats['in_db1'] and stats['in_db2'])
        schema_mismatches = sum(1 for stats in comparison.values() 
                              if stats['in_db1'] and stats['in_db2'] and not stats['schema_match'])
        
        logging.info(f"Total tables in DB1: {sum(1 for stats in comparison.values() if stats['in_db1'])}")
        logging.info(f"Total tables in DB2: {sum(1 for stats in comparison.values() if stats['in_db2'])}")
        logging.info(f"Tables only in DB1: {tables_only_in_db1}")
        logging.info(f"Tables only in DB2: {tables_only_in_db2}")
        logging.info(f"Tables in both: {tables_in_both}")
        logging.info(f"Schema mismatches: {schema_mismatches}")
        
    def compare_sample_data(self, table: str, limit: int = 5) -> None:
        """Compare sample data from a specific table"""
        if table not in self.get_tables(self.conn1) or table not in self.get_tables(self.conn2):
            logging.warning(f"Table {table} not present in both databases")
            return
            
        sample1 = self.get_sample_data(self.conn1, table, limit)
        sample2 = self.get_sample_data(self.conn2, table, limit)
        
        logging.info(f"\nSample data comparison for table: {table}")
        logging.info("-" * 80)
        logging.info(f"DB1 sample ({len(sample1)} rows):")
        logging.info(sample1)
        logging.info(f"\nDB2 sample ({len(sample2)} rows):")
        logging.info(sample2)
        
    def run(self, sample_table: str = None) -> None:
        """Run the comparison"""
        try:
            comparison = self.compare_table_structures()
            self.print_comparison(comparison)
            
            if sample_table:
                self.compare_sample_data(sample_table)
                
        except Exception as e:
            logging.error(f"Error during comparison: {str(e)}")

if __name__ == "__main__":
    # Example usage
    db1_path = "data/mstables.sqlite"
    db2_path = "/Users/xavier/sbox/Financial_Data/mstables_2019_2022/db/mstables.sqlite"
    
    with DatabaseComparer(db1_path, db2_path) as comparer:
        comparer.run(sample_table="tiingo_prices")  # Compare sample data from tiingo_prices table 