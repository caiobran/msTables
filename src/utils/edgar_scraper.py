"""
EDGAR (Electronic Data Gathering, Analysis, and Retrieval) Scraper

This module provides functionality to scrape and process SEC EDGAR filings.
It includes utilities for downloading and parsing EDGAR index files and filings.

Source: https://medium.com/@thomasfunk10/pulling-company-filings-from-edgar-using-pandas-eaa662cd3c22
Last Updated: 2024
"""

import pandas as pd
import io
import gzip
import requests
import datetime
from dateutil.relativedelta import relativedelta
import os
from typing import List, Tuple, Dict, Optional
import logging

class EdgarScraper:
    """Scraper for SEC EDGAR filings and index files."""
    
    def __init__(self, cache_dir: str = 'data/cache/edgar'):
        """Initialize the EDGAR scraper with cache directory."""
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self._setup_logging()
        
    def _setup_logging(self):
        """Set up logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('EdgarScraper')
        
    def quarter_tuple(self, date: datetime.datetime) -> Tuple[int, int]:
        """Convert a date to a quarter tuple (quarter, year).
        
        Args:
            date: The date to convert
            
        Returns:
            Tuple of (quarter number, year)
        """
        return (((date.month - 1) // 3 + 1), date.year)
        
    def get_quarters(self, start_date: datetime.datetime, 
                    end_date: datetime.datetime) -> List[Tuple[int, int]]:
        """Get list of quarters between start and end dates.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            List of (quarter, year) tuples
        """
        quarters = []
        next_date = start_date
        while next_date < end_date:
            quarters.append(self.quarter_tuple(next_date))
            next_date += relativedelta(months=3)
            
        end_date_quarter = self.quarter_tuple(end_date)
        if end_date_quarter not in quarters:
            quarters.append(end_date_quarter)
        return quarters
        
    def get_quarters_urls(self, start_date: datetime.datetime, 
                         end_date: datetime.datetime) -> List[str]:
        """Get list of EDGAR index file URLs for the given date range.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            List of URLs to EDGAR index files
        """
        quarters = self.get_quarters(start_date, end_date)
        return [f'https://www.sec.gov/Archives/edgar/full-index/{y}/QTR{q}/master.gz' 
                for (q, y) in quarters]
                
    def strip_header(self, data: io.StringIO) -> Tuple[io.StringIO, str]:
        """Remove the unstructured header from EDGAR index file.
        
        Args:
            data: StringIO object containing the index file data
            
        Returns:
            Tuple of (cleaned data, header)
        """
        header = ''
        line = ''
        while set(line) != set(['-']):
            header = line
            line = data.readline().strip()
        return data, header
        
    def read_url(self, url: str, delimiter: str = '|') -> pd.DataFrame:
        """Read and parse an EDGAR index file from URL.
        
        Args:
            url: URL to the index file
            delimiter: Delimiter used in the index file
            
        Returns:
            DataFrame containing the index data
        """
        try:
            # Get the master index gzip
            r = requests.get(url)
            # Unzip
            data_stream = gzip.decompress(r.content)
            # Decode bytes
            data = io.StringIO(data_stream.decode('utf-8'))
            # Remove the unstructured header
            data, columns = self.strip_header(data)
            # Create dataframe
            df = pd.read_csv(data, sep=delimiter)
            df.columns = columns.split(delimiter)
            df['Date Filed'] = pd.to_datetime(df['Date Filed'], format='%Y-%m-%d')
            return df
        except Exception as e:
            self.logger.error(f"Error reading URL {url}: {str(e)}")
            return pd.DataFrame()
            
    def filter_df(self, df: pd.DataFrame, start_date: datetime.datetime,
                 end_date: datetime.datetime, form_type: str,
                 cik_mapping: Dict[int, str] = None) -> pd.DataFrame:
        """Filter the index DataFrame by date range and form type.
        
        Args:
            df: Index DataFrame to filter
            start_date: Start date
            end_date: End date
            form_type: Type of form to filter for
            cik_mapping: Optional mapping of CIK numbers to ticker symbols
            
        Returns:
            Filtered DataFrame
        """
        try:
            in_date_range = (df['Date Filed'] >= start_date) & (df['Date Filed'] <= end_date)
            is_form_type = (df['Form Type'] == form_type)
            df = df.loc[in_date_range & is_form_type]
            
            if cik_mapping:
                df = df[df['CIK'].isin(cik_mapping.keys())]
                df['Ticker'] = df['CIK'].map(cik_mapping)
                
            return df.reset_index()
        except Exception as e:
            self.logger.error(f"Error filtering DataFrame: {str(e)}")
            return pd.DataFrame()
            
    def get_filings(self, start_date: datetime.datetime, end_date: datetime.datetime,
                   form_type: str, cik_mapping: Dict[int, str], dir_path: str) -> None:
        """Download SEC filings for the given parameters.
        
        Args:
            start_date: Start date
            end_date: End date
            form_type: Type of form to download
            cik_mapping: Mapping of CIK numbers to ticker symbols
            dir_path: Directory to save filings
        """
        urls = self.get_quarters_urls(start_date, end_date)
        
        for i, url in enumerate(urls):
            try:
                # Loop through the quarter urls
                df = self.read_url(url)
                df = self.filter_df(df, start_date, end_date, form_type, cik_mapping)
                
                for j, row in df.iterrows():
                    try:
                        # Loop through the filings
                        ticker = row['Ticker']
                        form = row['Form Type'].replace(' ', '-')
                        date = row['Date Filed'].date()
                        filename = row['Filename']
                        # More human-readable filename
                        outname = f"{ticker}_{form}_{date}.html"
                        
                        full_path = os.path.join(dir_path, outname)
                        file_url = f"https://www.sec.gov/Archives/{filename}"
                        
                        # Download
                        r = requests.get(file_url)
                        content = r.content.decode('utf-8')
                        
                        with open(full_path, 'w+') as f:
                            f.write(content)
                            
                    except Exception as e:
                        self.logger.error(f"Error processing filing {j}: {str(e)}")
                        continue
                        
            except Exception as e:
                self.logger.error(f"Error processing quarter {i}: {str(e)}")
                continue 