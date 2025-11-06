"""
Financial Data Analysis and Visualization

This module provides functionality to analyze and visualize financial data from our SQLite database.
It includes functions for price analysis, financial ratios, sector analysis, and stock screening.

Dependencies:
- pandas
- numpy
- matplotlib
- seaborn
- plotly
- sqlite3
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sqlite3
from pathlib import Path
from typing import List, Optional, Dict, Union
import logging
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('DataOverview')

class DataOverview:
    """A class to handle financial data analysis and visualization."""
    
    def __init__(self, db_path: str = 'data/financial_data.db'):
        """
        Initialize the DataOverview.
        
        Args:
            db_path (str): Path to the SQLite database
        """
        self.db_path = Path(db_path)
        self.charts_path = Path('data/charts')
        self.charts_path.mkdir(exist_ok=True)
        
        # Set style for matplotlib
        plt.style.use('seaborn')
        sns.set_palette("husl")
        
    def get_connection(self) -> sqlite3.Connection:
        """Get a connection to the SQLite database."""
        return sqlite3.connect(self.db_path)
        
    def get_stock_data(self, ticker: str, 
                      start_date: Optional[datetime] = None,
                      end_date: Optional[datetime] = None) -> Optional[pd.DataFrame]:
        """
        Get historical price data for a given ticker from the database.
        
        Args:
            ticker (str): Stock ticker symbol
            start_date (Optional[datetime]): Start date for the data
            end_date (Optional[datetime]): End date for the data
            
        Returns:
            Optional[pd.DataFrame]: DataFrame containing stock data
        """
        try:
            query = """
                SELECT date, open, high, low, close, volume
                FROM daily_data
                WHERE symbol = ?
            """
            params = [ticker]
            
            if start_date:
                query += " AND date >= ?"
                params.append(start_date.strftime('%Y-%m-%d'))
            if end_date:
                query += " AND date <= ?"
                params.append(end_date.strftime('%Y-%m-%d'))
                
            query += " ORDER BY date"
            
            with self.get_connection() as conn:
                df = pd.read_sql_query(query, conn, params=params, parse_dates=['date'])
                df.set_index('date', inplace=True)
                return df
                
        except Exception as e:
            logger.error(f"Error getting data for {ticker}: {str(e)}")
            return None
            
    def get_company_info(self, ticker: str) -> Optional[Dict]:
        """
        Get company information from the database.
        
        Args:
            ticker (str): Stock ticker symbol
            
        Returns:
            Optional[Dict]: Dictionary containing company information
        """
        try:
            query = """
                SELECT *
                FROM company_info
                WHERE symbol = ?
            """
            
            with self.get_connection() as conn:
                df = pd.read_sql_query(query, conn, params=[ticker])
                if not df.empty:
                    return df.iloc[0].to_dict()
                return None
                
        except Exception as e:
            logger.error(f"Error getting company info for {ticker}: {str(e)}")
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
        df = self.get_stock_data(ticker, start_date, end_date)
        if df is None:
            return
            
        # Create figure with secondary y-axis
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # Add candlestick chart
        fig.add_trace(
            go.Candlestick(
                x=df.index,
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                name="Price"
            ),
            secondary_y=False,
        )
        
        # Add volume bars
        fig.add_trace(
            go.Bar(x=df.index, y=df['volume'], name="Volume"),
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
            df = self.get_stock_data(ticker, start_date, end_date)
            if df is not None:
                dfs[ticker] = df['close']
                
        if not dfs:
            logger.error("No valid data found for any tickers")
            return
            
        # Combine all series into a DataFrame
        combined_df = pd.DataFrame(dfs)
        
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
            df = self.get_stock_data(ticker, start_date, end_date)
            if df is not None:
                # Calculate daily returns
                returns = df['close'].pct_change().dropna()
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
            df = self.get_stock_data(ticker, start_date, end_date)
            if df is not None:
                # Calculate daily returns
                returns = df['close'].pct_change().dropna()
                
                # Calculate rolling volatility
                volatility = returns.rolling(window=window).std() * np.sqrt(252)  # Annualized
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
        Plot sector performance based on company information in the database.
        
        Args:
            save (bool): Whether to save the plot to file
        """
        try:
            query = """
                SELECT sector, AVG(market_cap) as avg_market_cap,
                       COUNT(*) as company_count
                FROM company_info
                WHERE sector IS NOT NULL
                GROUP BY sector
                ORDER BY avg_market_cap DESC
            """
            
            with self.get_connection() as conn:
                df = pd.read_sql_query(query, conn)
                
            if df.empty:
                logger.error("No sector data found in database")
                return
                
            # Create bar plot
            plt.figure(figsize=(12, 6))
            sns.barplot(data=df, x='sector', y='avg_market_cap')
            plt.xticks(rotation=45, ha='right')
            plt.title('Average Market Cap by Sector')
            plt.xlabel('Sector')
            plt.ylabel('Average Market Cap (USD)')
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
    overview = DataOverview()
    
    # Example tickers
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN']
    
    # Set date range (last year)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    # Generate various charts
    for ticker in tickers:
        overview.plot_price_history(ticker, start_date, end_date)
        
    overview.plot_correlation_matrix(tickers, start_date, end_date)
    overview.plot_returns_distribution(tickers, start_date, end_date)
    overview.plot_rolling_volatility(tickers, window=30, start_date=start_date, end_date=end_date)
    overview.plot_sector_performance()

if __name__ == '__main__':
    main() 