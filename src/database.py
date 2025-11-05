import os
import sqlite3
from datetime import datetime
from shutil import copyfile
import logging

logger = logging.getLogger(__name__)

def get_db_path(db_name='mstables'):
    """Get the path to the database file."""
    return f'data/{db_name}.sqlite'

def create_tables(db_path):
    """Create necessary database tables if they don't exist."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Create Master table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Master (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT UNIQUE,
                name TEXT,
                exchange TEXT,
                country TEXT,
                type TEXT,
                source TEXT,
                last_updated TEXT,
                is_active BOOLEAN DEFAULT 1
            )
        """)
        
        # Create error_log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS error_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                source TEXT,
                symbol TEXT,
                error_type TEXT,
                error_message TEXT,
                stack_trace TEXT,
                context TEXT
            )
        """)
        
        # Create table_updates table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS table_updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                table_name TEXT,
                operation TEXT,
                symbol TEXT,
                rows_affected INTEGER,
                status TEXT,
                details TEXT
            )
        """)
        
        conn.commit()
        logger.info("Database tables created successfully")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error creating tables: {str(e)}")
        raise
    finally:
        conn.close()

def backup_db(db_path):
    """Create a backup of the database."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f'data/backup/mstables_backup_{timestamp}.sqlite'
    
    if os.path.exists(db_path):
        copyfile(db_path, backup_path)
        logger.info(f"Database backed up to {backup_path}")
        return f"Database backed up to {backup_path}"
    else:
        logger.warning("No database found to backup.")
        return "No database found to backup." 