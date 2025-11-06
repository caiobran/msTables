import requests
import bs4 as bs
import pandas as pd
from typing import List, Dict, Optional, Union
import logging
from datetime import datetime
import os
import json
from ..utils.yahoo_finance_reference import get_exchange_suffix, get_data_provider, get_exchange_info

class MarketDataScraper:
    """Scraper for market data from various reliable sources."""
    
    def __init__(self, cache_dir: str = 'data/cache'):
        """Initialize the scraper with cache directory."""
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self._setup_logging()
        
        # Load exchange information
        self.exchange_info = {market: (suffix, delay) for _, market, suffix, delay, _ in get_exchange_info()}
        
    def _setup_logging(self):
        """Set up logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('MarketDataScraper')
        
    def _get_cached_data(self, source: str, data_type: str) -> Optional[pd.DataFrame]:
        """Get cached data if available and not expired."""
        cache_file = os.path.join(self.cache_dir, f'{source}_{data_type}.json')
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
                if datetime.fromisoformat(cache_data['timestamp']) > datetime.now() - pd.Timedelta(days=1):
                    return pd.DataFrame(cache_data['data'])
        return None
        
    def _cache_data(self, source: str, data_type: str, data: pd.DataFrame):
        """Cache the scraped data."""
        cache_file = os.path.join(self.cache_dir, f'{source}_{data_type}.json')
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'data': data.to_dict(orient='records')
        }
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f)
            
    def _validate_exchange(self, exchange: str) -> bool:
        """Validate if the exchange exists in our reference data."""
        return exchange in self.exchange_info
        
    def _get_exchange_suffix(self, exchange: str) -> str:
        """Get the exchange suffix for a given exchange."""
        if exchange in self.exchange_info:
            return self.exchange_info[exchange][0]
        return ''
        
    def _get_data_provider(self, exchange: str) -> str:
        """Get the data provider for a given exchange."""
        if exchange in self.exchange_info:
            return get_data_provider('us_equities' if exchange in ['Nasdaq Stock Exchange', 'New York Stock Exchange'] else 'international_charts')
        return get_data_provider('us_equities')  # Default to US equities provider
        
    def get_sp500_tickers(self, use_cache: bool = True) -> pd.DataFrame:
        """Get S&P 500 tickers with additional company information."""
        if use_cache:
            cached_data = self._get_cached_data('wikipedia', 'sp500')
            if cached_data is not None:
                return cached_data
                
        try:
            resp = requests.get('http://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
            if resp.status_code != 200:
                self.logger.error(f"Failed to fetch S&P 500 data. Status code: {resp.status_code}")
                return pd.DataFrame()
                
            soup = bs.BeautifulSoup(resp.text, 'lxml')
            table = soup.find('table', {'class': 'wikitable sortable'})
            
            if not table:
                self.logger.error("Could not find S&P 500 table on Wikipedia")
                return pd.DataFrame()
                
            data = []
            for row in table.findAll('tr')[1:]:
                cols = row.findAll('td')
                if len(cols) >= 8:
                    data.append({
                        'ticker': cols[0].text.strip(),
                        'security': cols[1].text.strip(),
                        'gics_sector': cols[3].text.strip(),
                        'gics_sub_industry': cols[4].text.strip(),
                        'hq_location': cols[5].text.strip(),
                        'date_added': cols[6].text.strip(),
                        'cik': cols[7].text.strip(),
                        'founded': cols[8].text.strip() if len(cols) > 8 else None
                    })
                    
            df = pd.DataFrame(data)
            if use_cache:
                self._cache_data('wikipedia', 'sp500', df)
            return df
            
        except Exception as e:
            self.logger.error(f"Error fetching S&P 500 data: {str(e)}")
            return pd.DataFrame()
            
    def get_nasdaq100_tickers(self, use_cache: bool = True) -> pd.DataFrame:
        """Get NASDAQ-100 tickers with additional company information."""
        if use_cache:
            cached_data = self._get_cached_data('wikipedia', 'nasdaq100')
            if cached_data is not None:
                return cached_data
                
        try:
            resp = requests.get('http://en.wikipedia.org/wiki/Nasdaq-100')
            if resp.status_code != 200:
                self.logger.error(f"Failed to fetch NASDAQ-100 data. Status code: {resp.status_code}")
                return pd.DataFrame()
                
            soup = bs.BeautifulSoup(resp.text, 'lxml')
            table = soup.find('table', {'class': 'wikitable sortable'})
            
            if not table:
                self.logger.error("Could not find NASDAQ-100 table on Wikipedia")
                return pd.DataFrame()
                
            data = []
            for row in table.findAll('tr')[1:]:
                cols = row.findAll('td')
                if len(cols) >= 3:
                    data.append({
                        'ticker': cols[0].text.strip(),
                        'company': cols[1].text.strip(),
                        'sector': cols[2].text.strip(),
                        'weight': cols[3].text.strip() if len(cols) > 3 else None
                    })
                    
            df = pd.DataFrame(data)
            if use_cache:
                self._cache_data('wikipedia', 'nasdaq100', df)
            return df
            
        except Exception as e:
            self.logger.error(f"Error fetching NASDAQ-100 data: {str(e)}")
            return pd.DataFrame()
            
    def get_dow30_tickers(self, use_cache: bool = True) -> pd.DataFrame:
        """Get Dow Jones Industrial Average (DJIA) tickers with additional company information."""
        if use_cache:
            cached_data = self._get_cached_data('wikipedia', 'dow30')
            if cached_data is not None:
                return cached_data
                
        try:
            resp = requests.get('http://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average')
            if resp.status_code != 200:
                self.logger.error(f"Failed to fetch DJIA data. Status code: {resp.status_code}")
                return pd.DataFrame()
                
            soup = bs.BeautifulSoup(resp.text, 'lxml')
            table = soup.find('table', {'class': 'wikitable sortable'})
            
            if not table:
                self.logger.error("Could not find DJIA table on Wikipedia")
                return pd.DataFrame()
                
            data = []
            for row in table.findAll('tr')[1:]:
                cols = row.findAll('td')
                if len(cols) >= 4:
                    ticker = cols[0].text.strip()
                    exchange = 'New York Stock Exchange'  # DJIA stocks are all NYSE
                    data.append({
                        'ticker': ticker,
                        'full_symbol': f"{ticker}{self._get_exchange_suffix(exchange)}",
                        'company': cols[1].text.strip(),
                        'industry': cols[2].text.strip(),
                        'date_added': cols[3].text.strip(),
                        'notes': cols[4].text.strip() if len(cols) > 4 else None,
                        'exchange': exchange,
                        'data_provider': self._get_data_provider(exchange)
                    })
                    
            df = pd.DataFrame(data)
            if use_cache:
                self._cache_data('wikipedia', 'dow30', df)
            return df
            
        except Exception as e:
            self.logger.error(f"Error fetching DJIA data: {str(e)}")
            return pd.DataFrame()
            
    def get_market_cap_data(self, use_cache: bool = True) -> pd.DataFrame:
        """Get market cap data for major companies."""
        if use_cache:
            cached_data = self._get_cached_data('wikipedia', 'market_cap')
            if cached_data is not None:
                return cached_data
                
        try:
            resp = requests.get('http://en.wikipedia.org/wiki/List_of_largest_companies_by_revenue')
            if resp.status_code != 200:
                self.logger.error(f"Failed to fetch market cap data. Status code: {resp.status_code}")
                return pd.DataFrame()
                
            soup = bs.BeautifulSoup(resp.text, 'lxml')
            table = soup.find('table', {'class': 'wikitable sortable'})
            
            if not table:
                self.logger.error("Could not find market cap table on Wikipedia")
                return pd.DataFrame()
                
            data = []
            for row in table.findAll('tr')[1:]:
                cols = row.findAll('td')
                if len(cols) >= 6:
                    data.append({
                        'rank': cols[0].text.strip(),
                        'company': cols[1].text.strip(),
                        'revenue': cols[2].text.strip(),
                        'profit': cols[3].text.strip(),
                        'employees': cols[4].text.strip(),
                        'country': cols[5].text.strip()
                    })
                    
            df = pd.DataFrame(data)
            if use_cache:
                self._cache_data('wikipedia', 'market_cap', df)
            return df
            
        except Exception as e:
            self.logger.error(f"Error fetching market cap data: {str(e)}")
            return pd.DataFrame()
            
    def get_all_major_indices(self, use_cache: bool = True) -> Dict[str, pd.DataFrame]:
        """Get data for all major market indices."""
        return {
            'sp500': self.get_sp500_tickers(use_cache),
            'nasdaq100': self.get_nasdaq100_tickers(use_cache),
            'dow30': self.get_dow30_tickers(use_cache),
            'market_cap': self.get_market_cap_data(use_cache)
        } 