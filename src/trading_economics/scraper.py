import requests
import bs4 as bs
import pandas as pd
from typing import List, Dict, Optional, Union
import logging
from datetime import datetime
import os
import json
import time
from urllib.parse import urljoin

class TradingEconomicsScraper:
    """Scraper for Trading Economics data with comprehensive market information."""
    
    BASE_URL = "https://tradingeconomics.com"
    ENDPOINTS = {
        'bonds': '/bonds',
        'commodities': '/commodities',
        'indexes': '/indices',
        'shares': '/stocks',
        'currencies': '/currencies',
        'crypto': '/cryptocurrencies',
        'indicators': '/indicators',
        'countries': '/countries'
    }
    
    def __init__(self, cache_dir: str = 'data/cache/trading_economics'):
        """Initialize the scraper with cache directory."""
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self._setup_logging()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def _setup_logging(self):
        """Set up logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('TradingEconomicsScraper')
        
    def _get_cached_data(self, data_type: str, sub_type: str = None) -> Optional[pd.DataFrame]:
        """Get cached data if available and not expired."""
        cache_file = os.path.join(self.cache_dir, f'{data_type}_{sub_type if sub_type else "main"}.json')
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
                if datetime.fromisoformat(cache_data['timestamp']) > datetime.now() - pd.Timedelta(hours=6):
                    return pd.DataFrame(cache_data['data'])
        return None
        
    def _cache_data(self, data_type: str, data: pd.DataFrame, sub_type: str = None):
        """Cache the scraped data."""
        cache_file = os.path.join(self.cache_dir, f'{data_type}_{sub_type if sub_type else "main"}.json')
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'data': data.to_dict(orient='records')
        }
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f)
            
    def _scrape_table(self, url: str, table_class: str = 'table') -> pd.DataFrame:
        """Generic method to scrape a table from Trading Economics."""
        try:
            resp = self.session.get(url)
            if resp.status_code != 200:
                self.logger.error(f"Failed to fetch data from {url}. Status code: {resp.status_code}")
                return pd.DataFrame()
                
            soup = bs.BeautifulSoup(resp.text, 'lxml')
            table = soup.find('table', {'class': table_class})
            
            if not table:
                self.logger.error(f"Could not find table at {url}")
                return pd.DataFrame()
                
            # Extract headers
            headers = []
            for th in table.find_all('th'):
                headers.append(th.text.strip())
                
            # Extract rows
            data = []
            for row in table.find_all('tr')[1:]:  # Skip header row
                cols = row.find_all('td')
                if len(cols) == len(headers):
                    row_data = {}
                    for i, col in enumerate(cols):
                        row_data[headers[i]] = col.text.strip()
                    data.append(row_data)
                    
            return pd.DataFrame(data)
            
        except Exception as e:
            self.logger.error(f"Error scraping table from {url}: {str(e)}")
            return pd.DataFrame()
            
    def get_bonds_data(self, use_cache: bool = True) -> pd.DataFrame:
        """Get global bonds data."""
        if use_cache:
            cached_data = self._get_cached_data('bonds')
            if cached_data is not None:
                return cached_data
                
        url = urljoin(self.BASE_URL, self.ENDPOINTS['bonds'])
        df = self._scrape_table(url)
        if not df.empty and use_cache:
            self._cache_data('bonds', df)
        return df
        
    def get_commodities_data(self, use_cache: bool = True) -> pd.DataFrame:
        """Get commodities data."""
        if use_cache:
            cached_data = self._get_cached_data('commodities')
            if cached_data is not None:
                return cached_data
                
        url = urljoin(self.BASE_URL, self.ENDPOINTS['commodities'])
        df = self._scrape_table(url)
        if not df.empty and use_cache:
            self._cache_data('commodities', df)
        return df
        
    def get_indexes_data(self, use_cache: bool = True) -> pd.DataFrame:
        """Get global indexes data."""
        if use_cache:
            cached_data = self._get_cached_data('indexes')
            if cached_data is not None:
                return cached_data
                
        url = urljoin(self.BASE_URL, self.ENDPOINTS['indexes'])
        df = self._scrape_table(url)
        if not df.empty and use_cache:
            self._cache_data('indexes', df)
        return df
        
    def get_shares_data(self, use_cache: bool = True) -> pd.DataFrame:
        """Get global shares data."""
        if use_cache:
            cached_data = self._get_cached_data('shares')
            if cached_data is not None:
                return cached_data
                
        url = urljoin(self.BASE_URL, self.ENDPOINTS['shares'])
        df = self._scrape_table(url)
        if not df.empty and use_cache:
            self._cache_data('shares', df)
        return df
        
    def get_currencies_data(self, use_cache: bool = True) -> pd.DataFrame:
        """Get currencies data."""
        if use_cache:
            cached_data = self._get_cached_data('currencies')
            if cached_data is not None:
                return cached_data
                
        url = urljoin(self.BASE_URL, self.ENDPOINTS['currencies'])
        df = self._scrape_table(url)
        if not df.empty and use_cache:
            self._cache_data('currencies', df)
        return df
        
    def get_crypto_data(self, use_cache: bool = True) -> pd.DataFrame:
        """Get cryptocurrency data."""
        if use_cache:
            cached_data = self._get_cached_data('crypto')
            if cached_data is not None:
                return cached_data
                
        url = urljoin(self.BASE_URL, self.ENDPOINTS['crypto'])
        df = self._scrape_table(url)
        if not df.empty and use_cache:
            self._cache_data('crypto', df)
        return df
        
    def get_country_indicators(self, country_code: str, use_cache: bool = True) -> pd.DataFrame:
        """Get economic indicators for a specific country."""
        if use_cache:
            cached_data = self._get_cached_data('indicators', country_code)
            if cached_data is not None:
                return cached_data
                
        url = urljoin(self.BASE_URL, f"/country/{country_code}")
        df = self._scrape_table(url)
        if not df.empty and use_cache:
            self._cache_data('indicators', df, country_code)
        return df
        
    def get_countries_list(self, use_cache: bool = True) -> pd.DataFrame:
        """Get list of all available countries."""
        if use_cache:
            cached_data = self._get_cached_data('countries')
            if cached_data is not None:
                return cached_data
                
        url = urljoin(self.BASE_URL, self.ENDPOINTS['countries'])
        df = self._scrape_table(url)
        if not df.empty and use_cache:
            self._cache_data('countries', df)
        return df
        
    def get_all_market_data(self, use_cache: bool = True) -> Dict[str, pd.DataFrame]:
        """Get all available market data."""
        data = {}
        for endpoint in ['bonds', 'commodities', 'indexes', 'shares', 'currencies', 'crypto']:
            method = getattr(self, f'get_{endpoint}_data')
            data[endpoint] = method(use_cache)
            time.sleep(2)  # Be nice to their servers
        return data
        
    def get_all_country_data(self, use_cache: bool = True) -> Dict[str, pd.DataFrame]:
        """Get economic indicators for all countries."""
        countries_df = self.get_countries_list(use_cache)
        if countries_df.empty:
            return {}
            
        data = {}
        for country_code in countries_df['Code']:
            data[country_code] = self.get_country_indicators(country_code, use_cache)
            time.sleep(2)  # Be nice to their servers
        return data 