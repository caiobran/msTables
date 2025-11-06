#!/usr/bin/env python3
"""
Data Path Manager

Utility to view, manage, and consolidate financial data paths in the database.
Helps prevent duplicate imports and track data sources across machines.

Author: Data Consolidation System
Version: 1.0.0
"""

import sqlite3
import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class DataPathManager:
    """Manage financial data paths in the database."""
    
    def __init__(self, db_path: str = 'data/mstables.sqlite'):
        self.db_path = db_path
    
    def get_all_paths(self) -> pd.DataFrame:
        """Get all financial data paths as a DataFrame."""
        try:
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query("SELECT * FROM financial_data_paths ORDER BY created_at DESC", conn)
            conn.close()
            return df
        except Exception as e:
            logger.error(f"Error getting paths: {e}")
            return pd.DataFrame()
    
    def get_paths_by_machine(self, machine_id: str) -> pd.DataFrame:
        """Get paths for a specific machine."""
        try:
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query(
                "SELECT * FROM financial_data_paths WHERE machine_id = ? ORDER BY created_at DESC",
                conn, params=[machine_id]
            )
            conn.close()
            return df
        except Exception as e:
            logger.error(f"Error getting paths for machine {machine_id}: {e}")
            return pd.DataFrame()
    
    def get_paths_by_status(self, status: str) -> pd.DataFrame:
        """Get paths by import status."""
        try:
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query(
                "SELECT * FROM financial_data_paths WHERE import_status = ? ORDER BY created_at DESC",
                conn, params=[status]
            )
            conn.close()
            return df
        except Exception as e:
            logger.error(f"Error getting paths by status {status}: {e}")
            return pd.DataFrame()
    
    def get_duplicate_paths(self) -> pd.DataFrame:
        """Find potential duplicate paths across machines."""
        try:
            conn = sqlite3.connect(self.db_path)
            query = """
                SELECT p1.*, p2.path as duplicate_path, p2.machine_name as duplicate_machine
                FROM financial_data_paths p1
                JOIN financial_data_paths p2 ON p1.id != p2.id
                WHERE (
                    p1.path LIKE '%' || REPLACE(p2.path, '/', '%') || '%'
                    OR p2.path LIKE '%' || REPLACE(p1.path, '/', '%') || '%'
                )
                AND p1.machine_id != p2.machine_id
                ORDER BY p1.path, p2.path
            """
            df = pd.read_sql_query(query, conn)
            conn.close()
            return df
        except Exception as e:
            logger.error(f"Error finding duplicate paths: {e}")
            return pd.DataFrame()
    
    def get_summary_stats(self) -> Dict:
        """Get summary statistics of the data paths."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Overall summary
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_paths,
                    COUNT(DISTINCT machine_id) as total_machines,
                    COUNT(DISTINCT data_source) as total_sources,
                    COUNT(CASE WHEN import_status = 'not_imported' THEN 1 END) as not_imported,
                    COUNT(CASE WHEN import_status = 'imported' THEN 1 END) as imported,
                    COUNT(CASE WHEN import_status = 'failed' THEN 1 END) as failed
                FROM financial_data_paths
            """)
            
            summary = dict(zip([desc[0] for desc in cursor.description], cursor.fetchone()))
            
            # By machine
            cursor.execute("""
                SELECT machine_name, COUNT(*) as count
                FROM financial_data_paths
                GROUP BY machine_name
                ORDER BY count DESC
            """)
            
            by_machine = {row[0]: row[1] for row in cursor.fetchall()}
            
            # By data source
            cursor.execute("""
                SELECT data_source, COUNT(*) as count
                FROM financial_data_paths
                GROUP BY data_source
                ORDER BY count DESC
            """)
            
            by_source = {row[0]: row[1] for row in cursor.fetchall()}
            
            conn.close()
            
            return {
                'summary': summary,
                'by_machine': by_machine,
                'by_source': by_source
            }
            
        except Exception as e:
            logger.error(f"Error getting summary stats: {e}")
            return {}
    
    def update_import_status(self, path_id: int, status: str, errors: str = None):
        """Update the import status of a path."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE financial_data_paths 
                SET import_status = ?, import_date = ?, import_errors = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, datetime.now(), errors, path_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Updated path {path_id} status to {status}")
            
        except Exception as e:
            logger.error(f"Error updating import status: {e}")
    
    def mark_paths_for_import(self, machine_id: str = None, data_source: str = None):
        """Mark paths as ready for import."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if machine_id and data_source:
                cursor.execute("""
                    UPDATE financial_data_paths 
                    SET import_status = 'ready_for_import', updated_at = CURRENT_TIMESTAMP
                    WHERE machine_id = ? AND data_source = ? AND import_status = 'not_imported'
                """, (machine_id, data_source))
            elif machine_id:
                cursor.execute("""
                    UPDATE financial_data_paths 
                    SET import_status = 'ready_for_import', updated_at = CURRENT_TIMESTAMP
                    WHERE machine_id = ? AND import_status = 'not_imported'
                """, (machine_id,))
            elif data_source:
                cursor.execute("""
                    UPDATE financial_data_paths 
                    SET import_status = 'ready_for_import', updated_at = CURRENT_TIMESTAMP
                    WHERE data_source = ? AND import_status = 'not_imported'
                """, (data_source,))
            else:
                cursor.execute("""
                    UPDATE financial_data_paths 
                    SET import_status = 'ready_for_import', updated_at = CURRENT_TIMESTAMP
                    WHERE import_status = 'not_imported'
                """)
            
            updated_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            logger.info(f"Marked {updated_count} paths for import")
            return updated_count
            
        except Exception as e:
            logger.error(f"Error marking paths for import: {e}")
            return 0
    
    def export_to_csv(self, filename: str = 'financial_data_paths.csv'):
        """Export all paths to a CSV file."""
        try:
            df = self.get_all_paths()
            df.to_csv(filename, index=False)
            logger.info(f"Exported {len(df)} paths to {filename}")
            return filename
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")
            return None
    
    def print_summary(self):
        """Print a formatted summary of the data paths."""
        stats = self.get_summary_stats()
        
        if not stats:
            print("No data available")
            return
        
        print("=" * 60)
        print("FINANCIAL DATA PATHS SUMMARY")
        print("=" * 60)
        
        summary = stats['summary']
        print(f"Total paths: {summary['total_paths']}")
        print(f"Total machines: {summary['total_machines']}")
        print(f"Total data sources: {summary['total_sources']}")
        print(f"Not imported: {summary['not_imported']}")
        print(f"Imported: {summary['imported']}")
        print(f"Failed: {summary['failed']}")
        
        print("\nBy Machine:")
        print("-" * 30)
        for machine, count in stats['by_machine'].items():
            print(f"{machine}: {count} paths")
        
        print("\nBy Data Source:")
        print("-" * 30)
        for source, count in stats['by_source'].items():
            print(f"{source}: {count} paths")
    
    def print_duplicates(self):
        """Print potential duplicate paths."""
        df = self.get_duplicate_paths()
        
        if df.empty:
            print("No duplicate paths found")
            return
        
        print("=" * 60)
        print("POTENTIAL DUPLICATE PATHS")
        print("=" * 60)
        
        for _, row in df.iterrows():
            print(f"Path: {row['path']}")
            print(f"Machine: {row['machine_name']}")
            print(f"Duplicate: {row['duplicate_path']}")
            print(f"Duplicate Machine: {row['duplicate_machine']}")
            print("-" * 40)

def main():
    """Main function to demonstrate usage."""
    manager = DataPathManager()
    
    # Print summary
    manager.print_summary()
    
    # Print duplicates
    manager.print_duplicates()
    
    # Export to CSV
    filename = manager.export_to_csv()
    if filename:
        print(f"\nExported to: {filename}")

if __name__ == "__main__":
    main() 