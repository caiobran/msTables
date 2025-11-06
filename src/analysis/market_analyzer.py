"""
Market Analyzer with GPU Acceleration and Advanced Features

This module provides comprehensive market analysis capabilities with GPU acceleration,
regime detection, visualization, and robust error handling.
"""

import os
import sys
import logging
import time
import psutil
import numpy as np
import pandas as pd
import torch
import cupy as cp
from typing import List, Dict, Tuple, Optional
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from functools import wraps
import sqlite3
from datetime import datetime, timedelta

class MarketAnalyzer:
    def __init__(self, db_path: str, use_gpu: bool = True):
        """Initialize the Market Analyzer."""
        self.db_path = db_path
        self.use_gpu = use_gpu and torch.cuda.is_available()
        self.device = torch.device('cuda' if self.use_gpu else 'cpu')
        self.logger = self._setup_logging()
        
        if self.use_gpu:
            self.logger.info(f"Using GPU: {torch.cuda.get_device_name(0)}")
            torch.cuda.set_device(0)
        else:
            self.logger.warning("No GPU available, using CPU")
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging configuration."""
        logger = logging.getLogger('MarketAnalyzer')
        logger.setLevel(logging.INFO)
        
        # Create handlers
        c_handler = logging.StreamHandler()
        f_handler = logging.FileHandler('data/logs/market_analyzer.log')
        
        # Create formatters
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        c_handler.setFormatter(formatter)
        f_handler.setFormatter(formatter)
        
        # Add handlers
        logger.addHandler(c_handler)
        logger.addHandler(f_handler)
        
        return logger

    def calculate_rsi_gpu(self, prices_gpu: cp.ndarray, period: int = 14) -> cp.ndarray:
        """Calculate RSI using GPU acceleration."""
        try:
            # Calculate price changes
            delta = cp.diff(prices_gpu)
            
            # Separate gains and losses
            gains = cp.where(delta > 0, delta, 0)
            losses = cp.where(delta < 0, -delta, 0)
            
            # Calculate average gains and losses
            avg_gains = cp.convolve(gains, cp.ones(period)/period, mode='valid')
            avg_losses = cp.convolve(losses, cp.ones(period)/period, mode='valid')
            
            # Calculate RS and RSI
            rs = avg_gains / avg_losses
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
            
        except Exception as e:
            self.logger.error(f"Error calculating RSI on GPU: {e}")
            return cp.array([])

    def calculate_macd_gpu(self, prices_gpu: cp.ndarray, 
                          fast_period: int = 12, 
                          slow_period: int = 26, 
                          signal_period: int = 9) -> Tuple[cp.ndarray, cp.ndarray, cp.ndarray]:
        """Calculate MACD using GPU acceleration."""
        try:
            # Calculate EMAs
            fast_ema = cp.convolve(prices_gpu, cp.ones(fast_period)/fast_period, mode='valid')
            slow_ema = cp.convolve(prices_gpu, cp.ones(slow_period)/slow_period, mode='valid')
            
            # Calculate MACD line
            macd_line = fast_ema - slow_ema
            
            # Calculate signal line
            signal_line = cp.convolve(macd_line, cp.ones(signal_period)/signal_period, mode='valid')
            
            # Calculate histogram
            histogram = macd_line - signal_line
            
            return macd_line, signal_line, histogram
            
        except Exception as e:
            self.logger.error(f"Error calculating MACD on GPU: {e}")
            return cp.array([]), cp.array([]), cp.array([])

    def process_batch_gpu(self, data_batch: pd.DataFrame) -> pd.DataFrame:
        """Process a batch of data using GPU acceleration."""
        try:
            # Convert to GPU arrays
            close_gpu = cp.array(data_batch['close'].values)
            volume_gpu = cp.array(data_batch['volume'].values)
            high_gpu = cp.array(data_batch['high'].values)
            low_gpu = cp.array(data_batch['low'].values)
            
            # Process in parallel using CUDA streams
            with cp.cuda.Stream():
                # Calculate technical indicators
                rsi = self.calculate_rsi_gpu(close_gpu)
                macd_line, signal_line, histogram = self.calculate_macd_gpu(close_gpu)
                
                # Calculate additional features
                returns = cp.diff(close_gpu) / close_gpu[:-1]
                volatility = cp.std(returns, axis=0)
                high_low_range = (high_gpu - low_gpu) / close_gpu
                
                # Convert back to CPU
                data_batch['rsi'] = cp.asnumpy(rsi)
                data_batch['macd'] = cp.asnumpy(macd_line)
                data_batch['macd_signal'] = cp.asnumpy(signal_line)
                data_batch['macd_hist'] = cp.asnumpy(histogram)
                data_batch['volatility'] = cp.asnumpy(volatility)
                data_batch['high_low_range'] = cp.asnumpy(high_low_range)
            
            return data_batch
            
        except Exception as e:
            self.logger.error(f"Error processing batch on GPU: {e}")
            return data_batch

    def add_regime_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add market regime indicators."""
        try:
            # Calculate volatility regime
            data['volatility_regime'] = self.calculate_volatility_regime(data)
            
            # Calculate trend regime
            data['trend_regime'] = self.calculate_trend_regime(data)
            
            # Calculate commodity correlation
            data['commodity_correlation'] = self.calculate_commodity_correlation(data)
            
            # Calculate regime change probability
            data['regime_change_prob'] = self.calculate_regime_change_probability(data)
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error adding regime indicators: {e}")
            return data

    def calculate_volatility_regime(self, data: pd.DataFrame) -> pd.Series:
        """Calculate volatility regime using GPU acceleration."""
        try:
            returns_gpu = cp.array(data['returns'].values)
            volatility_gpu = cp.std(returns_gpu, axis=0)
            
            # Define regime thresholds
            low_vol = cp.percentile(volatility_gpu, 33)
            high_vol = cp.percentile(volatility_gpu, 66)
            
            # Classify regimes
            regime = cp.where(volatility_gpu < low_vol, 0,  # Low volatility
                     cp.where(volatility_gpu > high_vol, 2,  # High volatility
                     1))  # Medium volatility
            
            return pd.Series(cp.asnumpy(regime), index=data.index)
            
        except Exception as e:
            self.logger.error(f"Error calculating volatility regime: {e}")
            return pd.Series()

    def calculate_commodity_correlation(self, data: pd.DataFrame) -> pd.Series:
        """Calculate correlation with commodity prices."""
        try:
            # Fetch commodity data
            conn = sqlite3.connect(self.db_path)
            commodity_query = """
            SELECT date, close 
            FROM MSpricehistory 
            WHERE symbol IN ('GC=F', 'CL=F', 'SI=F')
            ORDER BY date
            """
            commodity_data = pd.read_sql_query(commodity_query, conn)
            
            # Calculate rolling correlations
            correlations = []
            for commodity in ['GC=F', 'CL=F', 'SI=F']:
                commodity_returns = commodity_data[commodity_data['symbol'] == commodity]['close'].pct_change()
                market_returns = data['close'].pct_change()
                correlation = commodity_returns.rolling(window=20).corr(market_returns)
                correlations.append(correlation)
            
            # Combine correlations
            combined_correlation = pd.concat(correlations, axis=1).mean(axis=1)
            
            return combined_correlation
            
        except Exception as e:
            self.logger.error(f"Error calculating commodity correlation: {e}")
            return pd.Series()

    def create_interactive_dashboard(self, data: pd.DataFrame, predictions: np.ndarray):
        """Create interactive dashboard for real-time monitoring."""
        try:
            # Create figure with subplots
            fig = make_subplots(
                rows=5, cols=2,
                shared_xaxes=True,
                vertical_spacing=0.05,
                subplot_titles=(
                    'Price and Predictions', 'Technical Indicators',
                    'Volume Analysis', 'Market Regime',
                    'Performance Metrics', 'Commodity Correlations',
                    'Risk Metrics', 'Trading Signals',
                    'System Health', 'Error Logs'
                )
            )
            
            # Add traces
            self._add_price_traces(fig, data, predictions)
            self._add_technical_traces(fig, data)
            self._add_volume_traces(fig, data)
            self._add_regime_traces(fig, data)
            self._add_performance_traces(fig, data)
            self._add_commodity_traces(fig, data)
            self._add_risk_traces(fig, data)
            self._add_signal_traces(fig, data)
            self._add_health_traces(fig)
            self._add_error_traces(fig)
            
            # Update layout
            fig.update_layout(
                height=2000,
                title_text="Real-time Market Analysis Dashboard",
                showlegend=True,
                template="plotly_dark"
            )
            
            # Save plot
            os.makedirs('data/dashboards', exist_ok=True)
            fig.write_html("data/dashboards/market_analysis.html")
            
        except Exception as e:
            self.logger.error(f"Error creating interactive dashboard: {e}")

    def _add_price_traces(self, fig: go.Figure, data: pd.DataFrame, predictions: np.ndarray):
        """Add price and prediction traces to the figure."""
        fig.add_trace(
            go.Scatter(x=data.index, y=data['close'], name='Actual Price'),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=data.index, y=predictions, name='Predictions'),
            row=1, col=1
        )

    def _add_technical_traces(self, fig: go.Figure, data: pd.DataFrame):
        """Add technical indicator traces to the figure."""
        fig.add_trace(
            go.Scatter(x=data.index, y=data['sma_20'], name='SMA 20'),
            row=1, col=2
        )
        fig.add_trace(
            go.Scatter(x=data.index, y=data['rsi'], name='RSI'),
            row=1, col=2
        )
        fig.add_trace(
            go.Scatter(x=data.index, y=data['macd'], name='MACD'),
            row=1, col=2
        )

    def _add_volume_traces(self, fig: go.Figure, data: pd.DataFrame):
        """Add volume analysis traces to the figure."""
        fig.add_trace(
            go.Bar(x=data.index, y=data['volume'], name='Volume'),
            row=2, col=1
        )
        fig.add_trace(
            go.Scatter(x=data.index, y=data['volume_sma'], name='Volume SMA'),
            row=2, col=1
        )

    def _add_regime_traces(self, fig: go.Figure, data: pd.DataFrame):
        """Add regime analysis traces to the figure."""
        fig.add_trace(
            go.Scatter(x=data.index, y=data['volatility_regime'], name='Volatility Regime'),
            row=2, col=2
        )
        fig.add_trace(
            go.Scatter(x=data.index, y=data['trend_regime'], name='Trend Regime'),
            row=2, col=2
        )

    def _add_performance_traces(self, fig: go.Figure, data: pd.DataFrame):
        """Add performance metric traces to the figure."""
        fig.add_trace(
            go.Scatter(x=data.index, y=data['returns'].cumsum(), name='Cumulative Returns'),
            row=3, col=1
        )
        fig.add_trace(
            go.Scatter(x=data.index, y=data['volatility'], name='Volatility'),
            row=3, col=1
        )

    def _add_commodity_traces(self, fig: go.Figure, data: pd.DataFrame):
        """Add commodity correlation traces to the figure."""
        fig.add_trace(
            go.Scatter(x=data.index, y=data['commodity_correlation'], name='Commodity Correlation'),
            row=3, col=2
        )

    def _add_risk_traces(self, fig: go.Figure, data: pd.DataFrame):
        """Add risk metric traces to the figure."""
        fig.add_trace(
            go.Scatter(x=data.index, y=data['high_low_range'], name='High-Low Range'),
            row=4, col=1
        )
        fig.add_trace(
            go.Scatter(x=data.index, y=data['regime_change_prob'], name='Regime Change Probability'),
            row=4, col=1
        )

    def _add_signal_traces(self, fig: go.Figure, data: pd.DataFrame):
        """Add trading signal traces to the figure."""
        fig.add_trace(
            go.Scatter(x=data.index, y=data['macd_signal'], name='MACD Signal'),
            row=4, col=2
        )

    def _add_health_traces(self, fig: go.Figure):
        """Add system health traces to the figure."""
        # Add GPU memory usage
        if torch.cuda.is_available():
            gpu_memory = torch.cuda.memory_allocated() / 1024**2
            fig.add_trace(
                go.Scatter(x=[datetime.now()], y=[gpu_memory], name='GPU Memory (MB)'),
                row=5, col=1
            )
        
        # Add CPU usage
        cpu_percent = psutil.cpu_percent()
        fig.add_trace(
            go.Scatter(x=[datetime.now()], y=[cpu_percent], name='CPU Usage (%)'),
            row=5, col=1
        )

    def _add_error_traces(self, fig: go.Figure):
        """Add error log traces to the figure."""
        # Read error log
        try:
            with open('data/logs/market_analyzer.log', 'r') as f:
                error_log = f.readlines()
            
            # Count errors by type
            error_counts = {}
            for line in error_log:
                if 'ERROR' in line:
                    error_type = line.split(' - ')[-1].split(':')[0]
                    error_counts[error_type] = error_counts.get(error_type, 0) + 1
            
            # Add error counts to figure
            fig.add_trace(
                go.Bar(x=list(error_counts.keys()), y=list(error_counts.values()), name='Error Counts'),
                row=5, col=2
            )
            
        except Exception as e:
            self.logger.error(f"Error reading error log: {e}")

    def retry_on_failure(max_retries: int = 3, delay: int = 1):
        """Decorator for retrying failed operations."""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                for attempt in range(max_retries):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        if attempt == max_retries - 1:
                            logging.error(f"Max retries reached for {func.__name__}: {e}")
                            raise
                        logging.warning(f"Retry {attempt + 1} for {func.__name__}: {e}")
                        time.sleep(delay)
            return wrapper
        return decorator

    def validate_data(self, data: pd.DataFrame) -> bool:
        """Validate data quality."""
        try:
            # Check for missing values
            if data.isnull().any().any():
                self.logger.warning("Missing values detected in data")
                return False
            
            # Check for infinite values
            if np.isinf(data.select_dtypes(include=np.number)).any().any():
                self.logger.warning("Infinite values detected in data")
                return False
            
            # Check for data types
            if not all(data.select_dtypes(include=np.number).dtypes == np.float64):
                self.logger.warning("Incorrect data types detected")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating data: {e}")
            return False

    def monitor_system_health(self):
        """Monitor system health metrics."""
        try:
            # Check GPU memory
            if torch.cuda.is_available():
                gpu_memory = torch.cuda.memory_allocated() / 1024**2
                if gpu_memory > 0.9 * torch.cuda.get_device_properties(0).total_memory:
                    self.logger.warning(f"High GPU memory usage: {gpu_memory:.2f} MB")
            
            # Check CPU usage
            cpu_percent = psutil.cpu_percent()
            if cpu_percent > 90:
                self.logger.warning(f"High CPU usage: {cpu_percent}%")
            
            # Check disk space
            disk_usage = psutil.disk_usage('/')
            if disk_usage.percent > 90:
                self.logger.warning(f"Low disk space: {disk_usage.percent}% used")
            
        except Exception as e:
            self.logger.error(f"Error monitoring system health: {e}") 