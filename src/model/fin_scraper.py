"""
Financial Data Scraper

This module provides functionality to scrape financial data from various sources,
including S&P 500 constituents from Wikipedia and historical price data from Yahoo Finance.

Sources:
- https://algotrading101.com/learn/yahoo-finance-api-guide/
- https://github.com/ranaroussi/yfinance
- https://github.com/GregBland/yahoo_fin_article
"""

import os
import datetime as dt
import pandas as pd
import requests
import bs4 as bs
import yfinance as yf
from typing import List, Optional
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('FinancialScraper')

class FinancialScraper:
    """A class to handle financial data scraping operations."""
    
    def __init__(self, save_path: str = 'data/csv'):
        """
        Initialize the FinancialScraper.
        
        Args:
            save_path (str): Path where CSV files will be saved
        """
        self.save_path = Path(save_path)
        self.save_path.mkdir(parents=True, exist_ok=True)
        self.stock_dfs_path = self.save_path / 'stock_dfs'
        self.stock_dfs_path.mkdir(exist_ok=True)
        
    def get_sp500_tickers(self) -> List[str]:
        """
        Scrape S&P 500 tickers from Wikipedia.
        
        Returns:
            List[str]: List of S&P 500 ticker symbols
        """
        try:
            resp = requests.get('http://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
            if resp.status_code != 200:
                logger.error(f"Failed to fetch S&P 500 data. Status code: {resp.status_code}")
                return []
                
            soup = bs.BeautifulSoup(resp.text, 'lxml')
            table = soup.find('table', {'class': 'wikitable sortable'})
            
            if not table:
                logger.error("Could not find S&P 500 table on Wikipedia")
                return []
                
            tickers = []
            for row in table.findAll('tr')[1:]:
                ticker = row.findAll('td')[0].text.strip()
                tickers.append(ticker)
                
            logger.info(f"Successfully scraped {len(tickers)} S&P 500 tickers")
            return tickers
            
        except Exception as e:
            logger.error(f"Error scraping S&P 500 tickers: {str(e)}")
            return []
            
    def save_tickers_to_csv(self, tickers: List[str], filename: str = 'sp500_tickers.csv'):
        """
        Save ticker symbols to a CSV file.
        
        Args:
            tickers (List[str]): List of ticker symbols
            filename (str): Name of the CSV file
        """
        try:
            df = pd.DataFrame(tickers, columns=['Symbol'])
            df.to_csv(self.save_path / filename, index=False)
            logger.info(f"Saved {len(tickers)} tickers to {filename}")
        except Exception as e:
            logger.error(f"Error saving tickers to CSV: {str(e)}")
            
    def load_tickers_from_csv(self, filename: str = 'sp500_tickers.csv') -> List[str]:
        """
        Load ticker symbols from a CSV file.
        
        Args:
            filename (str): Name of the CSV file
            
        Returns:
            List[str]: List of ticker symbols
        """
        try:
            df = pd.read_csv(self.save_path / filename)
            return df['Symbol'].tolist()
        except Exception as e:
            logger.error(f"Error loading tickers from CSV: {str(e)}")
            return []
            
    def get_data_from_yahoo(self, tickers: Optional[List[str]] = None, 
                           reload_sp500: bool = False,
                           start_date: dt.datetime = None,
                           end_date: dt.datetime = None) -> None:
        """
        Download historical price data from Yahoo Finance.
        
        Args:
            tickers (Optional[List[str]]): List of ticker symbols to download
            reload_sp500 (bool): Whether to reload S&P 500 tickers
            start_date (dt.datetime): Start date for historical data
            end_date (dt.datetime): End date for historical data
        """
        if reload_sp500 or tickers is None:
            tickers = self.get_sp500_tickers()
            self.save_tickers_to_csv(tickers)
            
        if not tickers:
            logger.error("No tickers provided")
            return
            
        start_date = start_date or dt.datetime(1900, 1, 1)
        end_date = end_date or dt.datetime.now()
        
        for ticker in tickers:
            csv_path = self.stock_dfs_path / f"{ticker}.csv"
            
            if not csv_path.exists():
                try:
                    # Replace dots with hyphens for Yahoo Finance compatibility
                    yahoo_ticker = ticker.replace('.', '-')
                    df = yf.download(yahoo_ticker, start_date, end_date, interval='1d')
                    
                    if not df.empty:
                        df.reset_index(inplace=True)
                        df.set_index("Date", inplace=True)
                        df.to_csv(csv_path)
                        logger.info(f"Downloaded and saved data for {ticker}")
                    else:
                        logger.warning(f"No data found for {ticker}")
                        
                except Exception as e:
                    logger.error(f"Error downloading data for {ticker}: {str(e)}")
            else:
                logger.info(f"Data already exists for {ticker}")

def main():
    """Main function to demonstrate usage."""
    scraper = FinancialScraper()
    
    # Get S&P 500 tickers
    tickers = scraper.get_sp500_tickers()
    
    if tickers:
        # Save tickers to CSV
        scraper.save_tickers_to_csv(tickers)
        
        # Download historical data
        scraper.get_data_from_yahoo(tickers)

if __name__ == '__main__':
    main() 