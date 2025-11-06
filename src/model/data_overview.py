"""
Financial Data Visualization

This module provides functionality to generate various financial charts and visualizations
from the data collected by the FinancialScraper.

Dependencies:
- pandas
- numpy
- matplotlib
- seaborn
- plotly
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
from typing import List, Optional, Dict, Union
import logging
from datetime import datetime, timedelta
from src.yahoo.fetcher import YahooFetcher
import sqlite3

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('DataVisualizer')

class DataVisualizer:
    """A class to handle financial data visualization."""
    
    def __init__(self, save_path: str = 'data'):
        """
        Initialize the DataVisualizer.
        
        Args:
            save_path (str): Base path where data and charts will be saved
        """
        # Create base directories
        self.base_path = Path(save_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        self.stock_dfs_path = self.base_path / 'csv' / 'stock_dfs'
        self.stock_dfs_path.mkdir(parents=True, exist_ok=True)
        
        self.charts_path = self.base_path / 'charts'
        self.charts_path.mkdir(parents=True, exist_ok=True)
        
        # Set style for matplotlib
        plt.style.use('seaborn-v0_8')  # Use the correct seaborn style name
        sns.set_theme()  # Set seaborn theme
        sns.set_palette("husl")
        
        logger.info(f"Initialized DataVisualizer with paths:")
        logger.info(f"Base path: {self.base_path}")
        logger.info(f"Stock data path: {self.stock_dfs_path}")
        logger.info(f"Charts path: {self.charts_path}")
        
    def load_stock_data(self, ticker: str) -> Optional[pd.DataFrame]:
        """
        Load stock data for a given ticker.
        
        Args:
            ticker (str): Stock ticker symbol
            
        Returns:
            Optional[pd.DataFrame]: DataFrame containing stock data
        """
        try:
            file_path = self.stock_dfs_path / f"{ticker}.csv"
            if not file_path.exists():
                logger.error(f"No data found for {ticker}")
                return None
                
            df = pd.read_csv(file_path, index_col='Date', parse_dates=True)
            return df
        except Exception as e:
            logger.error(f"Error loading data for {ticker}: {str(e)}")
            return None
            
    def plot_price_history(self, ticker: str, 
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None,
                          save: bool = True) -> None:
        """
        Plot historical price data for a given ticker.
        
        Args:
            ticker (str): Stock ticker symbol
            start_date (Optional[datetime]): Start date for the plot
            end_date (Optional[datetime]): End date for the plot
            save (bool): Whether to save the plot to file
        """
        df = self.load_stock_data(ticker)
        if df is None:
            return
            
        # Filter date range if specified
        if start_date:
            df = df[df.index >= start_date]
        if end_date:
            df = df[df.index <= end_date]
            
        # Create figure with secondary y-axis
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # Add price line
        fig.add_trace(
            go.Scatter(x=df.index, y=df['Close'], name="Price"),
            secondary_y=False,
        )
        
        # Add volume bars
        fig.add_trace(
            go.Bar(x=df.index, y=df['Volume'], name="Volume"),
            secondary_y=True,
        )
        
        # Update layout
        fig.update_layout(
            title=f"{ticker} Price History",
            xaxis_title="Date",
            yaxis_title="Price (USD)",
            yaxis2_title="Volume",
            template="plotly_white"
        )
        
        if save:
            fig.write_html(self.charts_path / f"{ticker}_price_history.html")
            logger.info(f"Saved price history chart for {ticker}")
        else:
            fig.show()
            
    def plot_correlation_matrix(self, tickers: List[str], 
                              start_date: Optional[datetime] = None,
                              end_date: Optional[datetime] = None,
                              save: bool = True) -> None:
        """
        Plot correlation matrix for multiple tickers.
        
        Args:
            tickers (List[str]): List of stock ticker symbols
            start_date (Optional[datetime]): Start date for the correlation
            end_date (Optional[datetime]): End date for the correlation
            save (bool): Whether to save the plot to file
        """
        # Load and prepare data
        dfs = {}
        for ticker in tickers:
            df = self.load_stock_data(ticker)
            if df is not None:
                dfs[ticker] = df['Close']
                
        if not dfs:
            logger.error("No valid data found for any tickers")
            return
            
        # Combine all series into a DataFrame
        combined_df = pd.DataFrame(dfs)
        
        # Filter date range if specified
        if start_date:
            combined_df = combined_df[combined_df.index >= start_date]
        if end_date:
            combined_df = combined_df[combined_df.index <= end_date]
            
        # Calculate correlation matrix
        corr_matrix = combined_df.corr()
        
        # Create heatmap
        plt.figure(figsize=(12, 8))
        sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', center=0)
        plt.title('Stock Price Correlation Matrix')
        
        if save:
            plt.savefig(self.charts_path / 'correlation_matrix.png', 
                       bbox_inches='tight', dpi=300)
            logger.info("Saved correlation matrix chart")
        else:
            plt.show()
        plt.close()
        
    def plot_returns_distribution(self, tickers: List[str],
                                start_date: Optional[datetime] = None,
                                end_date: Optional[datetime] = None,
                                save: bool = True) -> None:
        """
        Plot returns distribution for multiple tickers.
        
        Args:
            tickers (List[str]): List of stock ticker symbols
            start_date (Optional[datetime]): Start date for the analysis
            end_date (Optional[datetime]): End date for the analysis
            save (bool): Whether to save the plot to file
        """
        # Load and prepare data
        returns_data = {}
        for ticker in tickers:
            df = self.load_stock_data(ticker)
            if df is not None:
                # Calculate daily returns
                returns = df['Close'].pct_change().dropna()
                
                # Filter date range if specified
                if start_date:
                    returns = returns[returns.index >= start_date]
                if end_date:
                    returns = returns[returns.index <= end_date]
                    
                returns_data[ticker] = returns
                
        if not returns_data:
            logger.error("No valid data found for any tickers")
            return
            
        # Create subplots
        n_tickers = len(returns_data)
        fig, axes = plt.subplots(n_tickers, 1, figsize=(12, 4*n_tickers))
        if n_tickers == 1:
            axes = [axes]
            
        for (ticker, returns), ax in zip(returns_data.items(), axes):
            # Plot histogram with KDE
            sns.histplot(returns, kde=True, ax=ax)
            ax.set_title(f'{ticker} Returns Distribution')
            ax.set_xlabel('Daily Returns')
            ax.set_ylabel('Frequency')
            
        plt.tight_layout()
        
        if save:
            plt.savefig(self.charts_path / 'returns_distribution.png',
                       bbox_inches='tight', dpi=300)
            logger.info("Saved returns distribution chart")
        else:
            plt.show()
        plt.close()
        
    def plot_rolling_volatility(self, tickers: List[str],
                              window: int = 30,
                              start_date: Optional[datetime] = None,
                              end_date: Optional[datetime] = None,
                              save: bool = True) -> None:
        """
        Plot rolling volatility for multiple tickers.
        
        Args:
            tickers (List[str]): List of stock ticker symbols
            window (int): Rolling window size in days
            start_date (Optional[datetime]): Start date for the analysis
            end_date (Optional[datetime]): End date for the analysis
            save (bool): Whether to save the plot to file
        """
        # Load and prepare data
        volatility_data = {}
        for ticker in tickers:
            df = self.load_stock_data(ticker)
            if df is not None:
                # Calculate daily returns
                returns = df['Close'].pct_change().dropna()
                
                # Calculate rolling volatility
                volatility = returns.rolling(window=window).std() * np.sqrt(252)  # Annualized
                
                # Filter date range if specified
                if start_date:
                    volatility = volatility[volatility.index >= start_date]
                if end_date:
                    volatility = volatility[volatility.index <= end_date]
                    
                volatility_data[ticker] = volatility
                
        if not volatility_data:
            logger.error("No valid data found for any tickers")
            return
            
        # Create plot
        plt.figure(figsize=(12, 6))
        for ticker, volatility in volatility_data.items():
            plt.plot(volatility.index, volatility, label=ticker)
            
        plt.title(f'{window}-Day Rolling Volatility (Annualized)')
        plt.xlabel('Date')
        plt.ylabel('Volatility')
        plt.legend()
        plt.grid(True)
        
        if save:
            plt.savefig(self.charts_path / 'rolling_volatility.png',
                       bbox_inches='tight', dpi=300)
            logger.info("Saved rolling volatility chart")
        else:
            plt.show()
        plt.close()

    def plot_sector_performance(self, save: bool = True) -> None:
        """
        Plot sector performance based on company data.
        
        Args:
            save (bool): Whether to save the plot to file
        """
        try:
            # Get sector data from the database
            conn = sqlite3.connect('data/mstables.sqlite')
            sector_data = pd.read_sql_query('''
                SELECT symbol, sector, market_cap 
                FROM yahoo_info 
                WHERE sector IS NOT NULL
            ''', conn)
            conn.close()
            
            if sector_data.empty:
                logger.error("No sector data found in database")
                return
                
            # Calculate sector performance metrics
            sector_metrics = sector_data.groupby('sector').agg({
                'symbol': 'count',
                'market_cap': 'sum'
            }).rename(columns={
                'symbol': 'company_count',
                'market_cap': 'total_market_cap'
            })
            
            # Create subplots
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
            
            # Plot company count by sector
            sector_metrics['company_count'].sort_values().plot(
                kind='barh', ax=ax1, title='Number of Companies by Sector'
            )
            ax1.set_xlabel('Number of Companies')
            
            # Plot market cap by sector
            (sector_metrics['total_market_cap'] / 1e12).sort_values().plot(
                kind='barh', ax=ax2, title='Total Market Cap by Sector (Trillions USD)'
            )
            ax2.set_xlabel('Market Cap (Trillions USD)')
            
            plt.tight_layout()
            
            if save:
                plt.savefig(self.charts_path / 'sector_performance.png',
                           bbox_inches='tight', dpi=300)
                logger.info("Saved sector performance chart")
            else:
                plt.show()
            plt.close()
            
        except Exception as e:
            logger.error(f"Error plotting sector performance: {str(e)}")

def main():
    """Main function to demonstrate usage."""
    logger.info("Loading data from local files...")
    
    # Example tickers
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN']
    
    # Set date range (last year)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    # Create visualizer
    visualizer = DataVisualizer()
    
    try:
        # Try to load from data_stocks.csv first
        if Path('data/data_stocks.csv').exists():
            logger.info("Loading data from data_stocks.csv...")
            df = pd.read_csv('data/data_stocks.csv')
            
            # Filter for our tickers
            df = df[df['Symbol'].isin(tickers)]
            
            # Save individual ticker files
            for ticker in tickers:
                ticker_df = df[df['Symbol'] == ticker].copy()
                if not ticker_df.empty:
                    # Rename columns to match expected format
                    ticker_df = ticker_df.rename(columns={
                        'Date': 'date',
                        'Open': 'open',
                        'High': 'high',
                        'Low': 'low',
                        'Close': 'close',
                        'Volume': 'volume',
                        'Adj Close': 'adj_close'
                    })
                    
                    # Save to CSV
                    csv_path = visualizer.stock_dfs_path / f"{ticker}.csv"
                    ticker_df.to_csv(csv_path, index=False)
                    logger.info(f"Saved data for {ticker} to CSV")
        
        # If data_stocks.csv doesn't exist or is empty, try SQLite database
        elif Path('data/mstables.sqlite').exists():
            logger.info("Loading data from mstables.sqlite...")
            conn = sqlite3.connect('data/mstables.sqlite')
            
            for ticker in tickers:
                # Try different tables for price data
                tables_to_try = [
                    ('MSpricehistory', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume'),
                    ('tiingo_prices', 'date', 'open', 'high', 'low', 'close', 'volume'),
                    ('YahooQuote', 'date', 'open', 'high', 'low', 'close', 'volume')
                ]
                
                df = None
                for table, date_col, open_col, high_col, low_col, close_col, vol_col in tables_to_try:
                    try:
                        query = f'''
                            SELECT {date_col} as date, 
                                   {open_col} as open, 
                                   {high_col} as high, 
                                   {low_col} as low, 
                                   {close_col} as close, 
                                   {vol_col} as volume
                            FROM {table}
                            WHERE symbol = '{ticker}'
                            ORDER BY {date_col}
                        '''
                        df = pd.read_sql_query(query, conn)
                        if not df.empty:
                            logger.info(f"Found data for {ticker} in {table}")
                            break
                    except Exception as e:
                        logger.debug(f"No data in {table} for {ticker}: {str(e)}")
                        continue
                
                if df is not None and not df.empty:
                    # Add adj_close column (using close as a fallback)
                    df['adj_close'] = df['close']
                    
                    # Save to CSV
                    csv_path = visualizer.stock_dfs_path / f"{ticker}.csv"
                    df.to_csv(csv_path, index=False)
                    logger.info(f"Saved data for {ticker} to CSV")
                else:
                    logger.error(f"No price data found for {ticker} in any table")
            
            conn.close()
        else:
            logger.error("No data files found in data directory")
            return
            
    except Exception as e:
        logger.error(f"Error loading data: {str(e)}")
        return
    
    # Generate visualizations
    logger.info("Creating visualizations...")
    
    # Generate various charts
    for ticker in tickers:
        visualizer.plot_price_history(ticker, start_date, end_date)
        
    visualizer.plot_correlation_matrix(tickers, start_date, end_date)
    visualizer.plot_returns_distribution(tickers, start_date, end_date)
    visualizer.plot_rolling_volatility(tickers, window=30, start_date=start_date, end_date=end_date)
    visualizer.plot_sector_performance()
    
    logger.info("Visualization complete. Check the charts in data/charts directory.")

if __name__ == '__main__':
    main() 