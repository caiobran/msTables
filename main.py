"""
Main script for the financial data management system.

This script coordinates the data collection, processing, and visualization
components of the system.
"""
# TODO 1.0.0: Add proper error handling and logging configuration
# TODO 1.0.0: Add command line argument parsing
# TODO 1.1.0: Add configuration file support
# TODO 1.1.0: Implement health checks

import pytest
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
from collections import defaultdict
import sqlite3
import sys
import pandas as pd

from src.utils.data_shepherd import ExtendedDataShepherd
from src.model.data_overview import DataVisualizer

# TODO 1.0.0: Set up proper logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/logs/main.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# TODO 1.0.0: Add configuration management
def load_config():
    """Load configuration from environment variables or config file."""
    # TODO 1.1.0: Implement configuration file loading
    config = {
        'db_path': os.getenv('DB_PATH', 'data/mstables.sqlite'),
        'log_level': os.getenv('LOG_LEVEL', 'INFO'),
        'batch_size': int(os.getenv('BATCH_SIZE', '100')),
    }
    return config

def check_database_health():
    """Check database connectivity and basic health."""
    # TODO 1.1.0: Implement comprehensive health checks
    try:
        config = load_config()
        conn = sqlite3.connect(config['db_path'])
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        table_count = cursor.fetchone()[0]
        conn.close()
        logger.info(f"Database health check passed. Found {table_count} tables.")
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False

def setup_environment():
    """Set up the environment and create necessary directories."""
    # Load environment variables
    load_dotenv()
    
    # Create necessary directories
    directories = [
        'data',
        'data/logs',
        'data/csv',
        'data/charts',
        'data/csv/stock_dfs'
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensured directory exists: {directory}")

def analyze_data_gaps(shepherd, symbols, table_name='stock_data', lookback_days=365):
    """
    Analyze missing data gaps for given symbols.
    
    Returns:
    - Dictionary of symbols with their missing date ranges
    - Dictionary of symbols with their data completeness percentage
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days)
    
    gap_analysis = defaultdict(list)
    completeness = {}
    
    for symbol in symbols:
        logger.info(f"Analyzing data gaps for {symbol}")
        missing_dates = shepherd.find_missing_dates(symbol, table_name, start_date, end_date)
        
        if missing_dates:
            # Group consecutive dates
            date_groups = shepherd._group_consecutive_dates(missing_dates)
            gap_analysis[symbol] = date_groups
            
            # Calculate completeness
            total_days = (end_date - start_date).days
            missing_days = len(missing_dates)
            completeness[symbol] = ((total_days - missing_days) / total_days) * 100
            
            logger.info(f"{symbol}: {len(date_groups)} gaps found, {completeness[symbol]:.1f}% complete")
        else:
            completeness[symbol] = 100.0
            logger.info(f"{symbol}: No gaps found, 100% complete")
    
    return gap_analysis, completeness

def prioritize_gaps(gap_analysis, completeness):
    """
    Prioritize data gaps based on size and completeness.
    Returns a sorted list of (symbol, start_date, end_date) tuples.
    """
    prioritized_gaps = []
    
    for symbol, gaps in gap_analysis.items():
        for start, end in gaps:
            gap_size = (end - start).days
            # Prioritize larger gaps and symbols with lower completeness
            priority_score = gap_size * (100 - completeness[symbol])
            prioritized_gaps.append((priority_score, symbol, start, end))
    
    # Sort by priority score (descending)
    return sorted(prioritized_gaps, reverse=True)

def main():
    """Main entry point for the application."""
    # TODO 1.0.0: Add proper command line argument parsing
    # TODO 1.0.0: Add help text and usage information
    
    logger.info("Starting MSTables application")
    
    # Check system health
    if not check_database_health():
        logger.error("System health check failed. Exiting.")
        sys.exit(1)
    
    # TODO 1.0.0: Add main application logic here
    # TODO 1.0.0: Implement data processing pipeline
    # TODO 1.0.0: Add graceful shutdown handling
    
    try:
        # Set up environment
        setup_environment()
        logger.info("Starting data management system")
        
        # Initialize the data shepherd
        shepherd = ExtendedDataShepherd()
        shepherd.initialize_database()
        
        # Define symbols to process
        stock_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN']
        forex_pairs = [('USD', 'EUR'), ('USD', 'JPY'), ('GBP', 'USD')]
        crypto_symbols = ['BTC', 'ETH', 'XRP']
        
        # Analyze data gaps for stocks
        logger.info("Analyzing data gaps...")
        gap_analysis, completeness = analyze_data_gaps(shepherd, stock_symbols)
        
        # Prioritize and fetch missing data
        logger.info("Prioritizing and fetching missing data...")
        prioritized_gaps = prioritize_gaps(gap_analysis, completeness)
        
        for _, symbol, start_date, end_date in prioritized_gaps:
            logger.info(f"Fetching data for {symbol} from {start_date} to {end_date}")
            df = shepherd.fetch_missing_data(symbol, start_date, end_date)
            if not df.empty:
                shepherd.save_to_database(df, 'stock_data')
        
        # Process forex data
        logger.info("Processing forex data...")
        for from_curr, to_curr in forex_pairs:
            df = shepherd.fetch_forex_data(from_curr, to_curr)
            if not df.empty:
                shepherd.save_to_database(df, 'forex_data')
        
        # Process crypto data
        logger.info("Processing crypto data...")
        for symbol in crypto_symbols:
            df = shepherd.fetch_crypto_data(symbol)
            if not df.empty:
                shepherd.save_to_database(df, 'crypto_data')
        
        # Create visualizations
        logger.info("Creating visualizations...")
        visualizer = DataVisualizer()
        
        # Set date range based on available data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        
        # Generate various charts
        for ticker in stock_symbols:
            visualizer.plot_price_history(ticker, start_date, end_date)
        
        visualizer.plot_correlation_matrix(stock_symbols, start_date, end_date)
        visualizer.plot_returns_distribution(stock_symbols, start_date, end_date)
        visualizer.plot_rolling_volatility(stock_symbols, window=30, start_date=start_date, end_date=end_date)
        visualizer.plot_sector_performance()
        
        # Log data completeness report
        logger.info("\nData Completeness Report:")
        for symbol, complete in completeness.items():
            logger.info(f"{symbol}: {complete:.1f}% complete")
        
        logger.info("Data management system completed successfully")
        
    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")
        raise

if __name__ == '__main__':
    main()