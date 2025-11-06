#!/usr/bin/env python

import os
import sys
import logging
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.parent.parent)
sys.path.append(project_root)

from src.cboe.fetcher import CBOEFetcher

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main function to ingest CBOE data."""
    try:
        # Initialize fetcher
        fetcher = CBOEFetcher()
        
        # Get CBOE data directory
        cboe_dir = Path('CBOE_data')
        if not cboe_dir.exists():
            raise FileNotFoundError(f"CBOE data directory not found at {cboe_dir}")
        
        # Ingest VIX futures data
        vix_futures_dir = cboe_dir / 'VIX_futures'
        if vix_futures_dir.exists():
            for file in vix_futures_dir.glob('*.csv'):
                logger.info(f"Ingesting VIX futures data from {file}")
                fetcher.ingest_vix_futures(str(file))
        
        # Ingest circuit breaker data
        circuit_breaker_dir = cboe_dir / 'circuit_breakers'
        if circuit_breaker_dir.exists():
            for file in circuit_breaker_dir.glob('*.csv'):
                logger.info(f"Ingesting circuit breaker data from {file}")
                fetcher.ingest_circuit_breakers(str(file))
        
        # Ingest market statistics
        market_stats_dir = cboe_dir / 'market_statistics'
        if market_stats_dir.exists():
            for file in market_stats_dir.glob('*.csv'):
                logger.info(f"Ingesting market statistics from {file}")
                fetcher.ingest_market_stats(str(file))
        
        logger.info("Successfully completed CBOE data ingestion")
        
    except Exception as e:
        logger.error(f"Error ingesting CBOE data: {str(e)}")
        raise

if __name__ == '__main__':
    main() 