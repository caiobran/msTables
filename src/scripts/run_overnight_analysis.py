"""
Overnight Analysis Script

This script runs overnight analysis and prepares trading signals for the next day.
It leverages GPU acceleration and parallel processing for efficient computation.
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
import pandas as pd
import numpy as np
import torch
from src.analysis.market_simulator import MarketSimulator
from src.analysis.ratio_calculator import RatioCalculator
from src.trading.tws_integration import TWSIntegration
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import cupy as cp
import sqlite3

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/logs/overnight_analysis.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('OvernightAnalysis')

def setup_environment():
    """Set up the environment for overnight analysis."""
    # Create necessary directories
    Path('data/logs').mkdir(parents=True, exist_ok=True)
    Path('data/predictions').mkdir(parents=True, exist_ok=True)
    Path('data/simulations').mkdir(parents=True, exist_ok=True)
    Path('data/trading').mkdir(parents=True, exist_ok=True)
    
    # Set up GPU
    if torch.cuda.is_available():
        logger.info(f"Using GPU: {torch.cuda.get_device_name(0)}")
        torch.cuda.set_device(0)
    else:
        logger.warning("No GPU available, using CPU")
    
    # Set up CPU pool
    num_cores = mp.cpu_count()
    logger.info(f"Using {num_cores} CPU cores")

def load_watchlist() -> list:
    """
    Load the watchlist of symbols to analyze.
    
    Returns
    -------
    list
        List of symbols to analyze
    """
    try:
        with open('data/config/watchlist.json', 'r') as f:
            watchlist = json.load(f)
        return watchlist['symbols']
    except Exception as e:
        logger.error(f"Error loading watchlist: {e}")
        return []

def run_market_analysis(symbols: list):
    """
    Run market analysis for the watchlist.
    
    Parameters
    ----------
    symbols : list
        List of symbols to analyze
    """
    try:
        # Initialize market simulator
        simulator = MarketSimulator(
            num_simulations=10000,  # Adjust based on your GPU memory
            prediction_horizon=5
        )
        
        # Run overnight analysis
        simulator.run_overnight_analysis(symbols)
        
    except Exception as e:
        logger.error(f"Error in market analysis: {e}")

def prepare_trading_signals():
    """
    Prepare trading signals for the next day.
    """
    try:
        # Load overnight analysis
        with open('data/predictions/overnight_analysis.json', 'r') as f:
            analysis = json.load(f)
        
        # Initialize TWS integration
        tws = TWSIntegration(paper_trading=True)
        
        if tws.connect():
            try:
                # Execute signals
                tws.execute_trading_signals(analysis['signals'])
                
                # Save results
                tws.save_trading_results()
                
            finally:
                tws.disconnect()
                
    except Exception as e:
        logger.error(f"Error preparing trading signals: {e}")

def visualize_market_analysis(data: pd.DataFrame, predictions: np.ndarray):
    """Create comprehensive visualizations of market analysis."""
    try:
        # Create figure with subplots
        fig = make_subplots(
            rows=4, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            subplot_titles=('Price and Predictions', 'Technical Indicators', 
                          'Volume Analysis', 'Market Regime')
        )
        
        # Price and predictions
        fig.add_trace(
            go.Scatter(x=data.index, y=data['close'], name='Actual Price'),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=data.index, y=predictions, name='Predictions'),
            row=1, col=1
        )
        
        # Technical indicators
        fig.add_trace(
            go.Scatter(x=data.index, y=data['sma_20'], name='SMA 20'),
            row=2, col=1
        )
        fig.add_trace(
            go.Scatter(x=data.index, y=data['sma_50'], name='SMA 50'),
            row=2, col=1
        )
        fig.add_trace(
            go.Scatter(x=data.index, y=data['rsi'], name='RSI'),
            row=2, col=1
        )
        
        # Volume analysis
        fig.add_trace(
            go.Bar(x=data.index, y=data['volume'], name='Volume'),
            row=3, col=1
        )
        fig.add_trace(
            go.Scatter(x=data.index, y=data['volume_sma'], name='Volume SMA'),
            row=3, col=1
        )
        
        # Market regime
        fig.add_trace(
            go.Scatter(x=data.index, y=data['regime'], name='Market Regime'),
            row=4, col=1
        )
        
        # Update layout
        fig.update_layout(
            height=1200,
            title_text="Market Analysis Dashboard",
            showlegend=True,
            template="plotly_dark"
        )
        
        # Save plot
        fig.write_html("market_analysis.html")
        
    except Exception as e:
        logger.error(f"Error creating visualizations: {e}")

def calculate_features_gpu(self, data: pd.DataFrame) -> pd.DataFrame:
    """Calculate features using advanced GPU acceleration."""
    try:
        # Convert to GPU arrays
        close_gpu = cp.array(data['close'].values)
        volume_gpu = cp.array(data['volume'].values)
        high_gpu = cp.array(data['high'].values)
        low_gpu = cp.array(data['low'].values)
        
        # Batch processing for multiple features
        with cp.cuda.Stream():
            # Price features
            returns_gpu = cp.diff(close_gpu) / close_gpu[:-1]
            log_returns_gpu = cp.log(close_gpu / cp.roll(close_gpu, 1))
            
            # Volatility features
            volatility_gpu = cp.std(returns_gpu, axis=0)
            high_low_range_gpu = (high_gpu - low_gpu) / close_gpu
            
            # Trend features
            sma_20_gpu = cp.convolve(close_gpu, cp.ones(20)/20, mode='valid')
            sma_50_gpu = cp.convolve(close_gpu, cp.ones(50)/50, mode='valid')
            sma_200_gpu = cp.convolve(close_gpu, cp.ones(200)/200, mode='valid')
            
            # Momentum features
            rsi_gpu = self.calculate_rsi_gpu(close_gpu)
            macd_gpu = self.calculate_macd_gpu(close_gpu)
            
            # Volume features
            volume_sma_gpu = cp.convolve(volume_gpu, cp.ones(20)/20, mode='valid')
            volume_ratio_gpu = volume_gpu / volume_sma_gpu
            
            # Convert back to CPU
            data['returns'] = cp.asnumpy(returns_gpu)
            data['log_returns'] = cp.asnumpy(log_returns_gpu)
            data['volatility'] = cp.asnumpy(volatility_gpu)
            data['high_low_range'] = cp.asnumpy(high_low_range_gpu)
            data['sma_20'] = cp.asnumpy(sma_20_gpu)
            data['sma_50'] = cp.asnumpy(sma_50_gpu)
            data['sma_200'] = cp.asnumpy(sma_200_gpu)
            data['rsi'] = cp.asnumpy(rsi_gpu)
            data['macd'] = cp.asnumpy(macd_gpu)
            data['volume_ratio'] = cp.asnumpy(volume_ratio_gpu)
            
        return data
        
    except Exception as e:
        self.logger.error(f"Error calculating GPU features: {e}")
        return data

def prepare_market_data(self, symbol: str = '^GSPC', lookback_days: int = 252) -> pd.DataFrame:
    """Fetch and prepare market data with enhanced features."""
    try:
        # Connect to database
        conn = sqlite3.connect(self.db_path)
        
        # Fetch historical data with joins for additional metrics
        query = """
        SELECT 
            p.date, p.open, p.high, p.low, p.close, p.volume,
            c.market_cap, c.pe_ratio, c.dividend_yield,
            f.current_ratio, f.debt_to_equity, f.return_on_equity
        FROM MSpricehistory p
        LEFT JOIN MScompany c ON p.symbol = c.symbol
        LEFT JOIN MSfinancials f ON p.symbol = f.symbol
        WHERE p.symbol = ? 
        ORDER BY p.date DESC 
        LIMIT ?
        """
        data = pd.read_sql_query(query, conn, params=(symbol, lookback_days))
        
        # Add technical indicators
        data = self.add_technical_indicators(data)
        
        # Add fundamental indicators
        data = self.add_fundamental_indicators(data)
        
        # Add market regime indicators
        data = self.add_regime_indicators(data)
        
        return data
        
    except Exception as e:
        self.logger.error(f"Error preparing market data: {e}")
        return pd.DataFrame()

def main():
    """Main function to run overnight analysis."""
    try:
        # Set up environment
        setup_environment()
        
        # Load watchlist
        symbols = load_watchlist()
        if not symbols:
            logger.error("No symbols to analyze")
            return
        
        # Run market analysis
        run_market_analysis(symbols)
        
        # Prepare trading signals
        prepare_trading_signals()
        
        logger.info("Overnight analysis completed successfully")
        
    except Exception as e:
        logger.error(f"Error in overnight analysis: {e}")

if __name__ == '__main__':
    main() 