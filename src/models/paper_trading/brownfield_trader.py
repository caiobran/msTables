"""
Brownfield Paper Trading Framework

This module implements a paper trading system that uses the Brownfield predictor
for simulated trading with comprehensive risk management and performance tracking.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
import logging
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import json
import torch
from ..deep_learning.brownfield_predictor import BrownfieldPredictor, ModelHyperparameters

@dataclass
class Trade:
    """Represents a single trade."""
    entry_time: datetime
    entry_price: float
    position_size: float
    direction: str  # 'long' or 'short'
    stop_loss: float
    take_profit: float
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    pnl: Optional[float] = None
    exit_reason: Optional[str] = None

@dataclass
class Portfolio:
    """Represents a trading portfolio."""
    initial_capital: float
    current_capital: float
    positions: Dict[str, Trade]
    trades: List[Trade]
    cash: float
    margin_used: float
    margin_available: float

class BrownfieldTrader:
    """
    Paper trading system using Brownfield predictor.
    """
    def __init__(self,
                 model: BrownfieldPredictor,
                 initial_capital: float = 100000.0,
                 max_position_size: float = 0.1,
                 max_drawdown: float = 0.15,
                 risk_reward_ratio: float = 3.0,
                 transaction_cost: float = 0.001):
        """
        Initialize the Brownfield trader.
        
        Parameters
        ----------
        model : BrownfieldPredictor
            Brownfield prediction model
        initial_capital : float
            Initial capital
        max_position_size : float
            Maximum position size as fraction of capital
        max_drawdown : float
            Maximum allowed drawdown
        risk_reward_ratio : float
            Target risk/reward ratio
        transaction_cost : float
            Transaction cost per trade
        """
        self.model = model
        self.initial_capital = initial_capital
        self.max_position_size = max_position_size
        self.max_drawdown = max_drawdown
        self.risk_reward_ratio = risk_reward_ratio
        self.transaction_cost = transaction_cost
        
        # Initialize portfolio
        self.portfolio = Portfolio(
            initial_capital=initial_capital,
            current_capital=initial_capital,
            positions={},
            trades=[],
            cash=initial_capital,
            margin_used=0.0,
            margin_available=initial_capital
        )
        
        # Performance tracking
        self.equity_curve = []
        self.drawdown_curve = []
        self.returns = []
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            
    def calculate_position_size(self,
                              price: float,
                              risk_score: float,
                              volatility: float) -> float:
        """
        Calculate position size based on risk parameters.
        
        Parameters
        ----------
        price : float
            Current price
        risk_score : float
            Model's risk score
        volatility : float
            Current volatility
            
        Returns
        -------
        float
            Position size in units
        """
        # Base position size on risk score and volatility
        base_size = self.portfolio.current_capital * self.max_position_size
        risk_adjusted_size = base_size * (1 - risk_score)
        vol_adjusted_size = risk_adjusted_size / (1 + volatility)
        
        # Ensure position size doesn't exceed maximum
        position_size = min(vol_adjusted_size, base_size)
        
        return position_size
        
    def calculate_stop_loss(self,
                          price: float,
                          direction: str,
                          volatility: float) -> float:
        """
        Calculate stop loss level.
        
        Parameters
        ----------
        price : float
            Current price
        direction : str
            Trade direction ('long' or 'short')
        volatility : float
            Current volatility
            
        Returns
        -------
        float
            Stop loss price
        """
        # Base stop loss on volatility
        stop_distance = price * volatility * 2
        
        if direction == 'long':
            return price - stop_distance
        else:
            return price + stop_distance
            
    def calculate_take_profit(self,
                            price: float,
                            stop_loss: float,
                            direction: str) -> float:
        """
        Calculate take profit level.
        
        Parameters
        ----------
        price : float
            Current price
        stop_loss : float
            Stop loss price
        direction : str
            Trade direction ('long' or 'short')
            
        Returns
        -------
        float
            Take profit price
        """
        # Calculate risk
        risk = abs(price - stop_loss)
        
        # Calculate reward based on risk/reward ratio
        reward = risk * self.risk_reward_ratio
        
        if direction == 'long':
            return price + reward
        else:
            return price - reward
            
    def open_position(self,
                     symbol: str,
                     price: float,
                     position_size: float,
                     direction: str,
                     stop_loss: float,
                     take_profit: float) -> None:
        """
        Open a new position.
        
        Parameters
        ----------
        symbol : str
            Trading symbol
        price : float
            Entry price
        position_size : float
            Position size in units
        direction : str
            Trade direction ('long' or 'short')
        stop_loss : float
            Stop loss price
        take_profit : float
            Take profit price
        """
        # Create trade
        trade = Trade(
            entry_time=datetime.now(),
            entry_price=price,
            position_size=position_size,
            direction=direction,
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        
        # Update portfolio
        self.portfolio.positions[symbol] = trade
        self.portfolio.margin_used += position_size * price
        self.portfolio.margin_available -= position_size * price
        self.portfolio.cash -= position_size * price * (1 + self.transaction_cost)
        
        self.logger.info(f"Opened {direction} position in {symbol} at {price}")
        
    def close_position(self,
                      symbol: str,
                      price: float,
                      reason: str) -> None:
        """
        Close an existing position.
        
        Parameters
        ----------
        symbol : str
            Trading symbol
        price : float
            Exit price
        reason : str
            Reason for closing
        """
        if symbol not in self.portfolio.positions:
            self.logger.warning(f"No position found for {symbol}")
            return
            
        trade = self.portfolio.positions[symbol]
        
        # Calculate PnL
        if trade.direction == 'long':
            pnl = (price - trade.entry_price) * trade.position_size
        else:
            pnl = (trade.entry_price - price) * trade.position_size
            
        # Update trade
        trade.exit_time = datetime.now()
        trade.exit_price = price
        trade.pnl = pnl
        trade.exit_reason = reason
        
        # Update portfolio
        self.portfolio.trades.append(trade)
        self.portfolio.margin_used -= trade.position_size * trade.entry_price
        self.portfolio.margin_available += trade.position_size * trade.entry_price
        self.portfolio.cash += trade.position_size * price * (1 - self.transaction_cost)
        self.portfolio.current_capital += pnl
        
        # Update performance tracking
        self.equity_curve.append(self.portfolio.current_capital)
        self.returns.append(pnl / self.portfolio.initial_capital)
        
        # Calculate drawdown
        peak = max(self.equity_curve)
        drawdown = (peak - self.portfolio.current_capital) / peak
        self.drawdown_curve.append(drawdown)
        
        # Remove position
        del self.portfolio.positions[symbol]
        
        self.logger.info(f"Closed {trade.direction} position in {symbol} at {price}. PnL: {pnl:.2f}")
        
    def check_stop_loss(self,
                       symbol: str,
                       current_price: float) -> bool:
        """
        Check if stop loss is hit.
        
        Parameters
        ----------
        symbol : str
            Trading symbol
        current_price : float
            Current price
            
        Returns
        -------
        bool
            True if stop loss is hit
        """
        if symbol not in self.portfolio.positions:
            return False
            
        trade = self.portfolio.positions[symbol]
        
        if trade.direction == 'long':
            return current_price <= trade.stop_loss
        else:
            return current_price >= trade.stop_loss
            
    def check_take_profit(self,
                         symbol: str,
                         current_price: float) -> bool:
        """
        Check if take profit is hit.
        
        Parameters
        ----------
        symbol : str
            Trading symbol
        current_price : float
            Current price
            
        Returns
        -------
        bool
            True if take profit is hit
        """
        if symbol not in self.portfolio.positions:
            return False
            
        trade = self.portfolio.positions[symbol]
        
        if trade.direction == 'long':
            return current_price >= trade.take_profit
        else:
            return current_price <= trade.take_profit
            
    def check_drawdown(self) -> bool:
        """
        Check if maximum drawdown is exceeded.
        
        Returns
        -------
        bool
            True if maximum drawdown is exceeded
        """
        if not self.drawdown_curve:
            return False
            
        return self.drawdown_curve[-1] > self.max_drawdown
        
    def process_bar(self,
                   symbol: str,
                   bar_data: pd.Series) -> None:
        """
        Process a new price bar.
        
        Parameters
        ----------
        symbol : str
            Trading symbol
        bar_data : pd.Series
            Bar data with OHLCV
        """
        # Get model predictions
        with torch.no_grad():
            position, risk, value = self.model(bar_data)
            
        # Check existing positions
        if symbol in self.portfolio.positions:
            trade = self.portfolio.positions[symbol]
            
            # Check stop loss
            if self.check_stop_loss(symbol, bar_data['close']):
                self.close_position(symbol, bar_data['close'], 'stop_loss')
                return
                
            # Check take profit
            if self.check_take_profit(symbol, bar_data['close']):
                self.close_position(symbol, bar_data['close'], 'take_profit')
                return
                
        # Check drawdown
        if self.check_drawdown():
            self.logger.warning("Maximum drawdown exceeded. Closing all positions.")
            for sym in list(self.portfolio.positions.keys()):
                self.close_position(sym, bar_data['close'], 'max_drawdown')
            return
            
        # Check for new positions
        if symbol not in self.portfolio.positions:
            # Calculate position size
            position_size = self.calculate_position_size(
                bar_data['close'],
                risk.item(),
                bar_data['volatility']
            )
            
            if position_size > 0:
                # Determine direction
                direction = 'long' if position.item() > 0 else 'short'
                
                # Calculate stop loss and take profit
                stop_loss = self.calculate_stop_loss(
                    bar_data['close'],
                    direction,
                    bar_data['volatility']
                )
                
                take_profit = self.calculate_take_profit(
                    bar_data['close'],
                    stop_loss,
                    direction
                )
                
                # Open position
                self.open_position(
                    symbol,
                    bar_data['close'],
                    position_size,
                    direction,
                    stop_loss,
                    take_profit
                )
                
    def get_performance_metrics(self) -> Dict[str, float]:
        """
        Calculate performance metrics.
        
        Returns
        -------
        Dict[str, float]
            Performance metrics
        """
        if not self.returns:
            return {}
            
        returns = np.array(self.returns)
        
        metrics = {
            'total_return': (self.portfolio.current_capital - self.initial_capital) / self.initial_capital,
            'sharpe_ratio': np.mean(returns) / np.std(returns) * np.sqrt(252),
            'max_drawdown': max(self.drawdown_curve) if self.drawdown_curve else 0,
            'win_rate': len(returns[returns > 0]) / len(returns),
            'profit_factor': abs(np.sum(returns[returns > 0]) / np.sum(returns[returns < 0])) if np.sum(returns[returns < 0]) != 0 else float('inf'),
            'avg_trade': np.mean(returns),
            'std_trade': np.std(returns)
        }
        
        return metrics
        
    def plot_performance(self,
                        save_path: Optional[str] = None) -> None:
        """
        Plot performance charts.
        
        Parameters
        ----------
        save_path : Optional[str]
            Path to save plots
        """
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # Plot equity curve
        axes[0, 0].plot(self.equity_curve)
        axes[0, 0].set_title('Equity Curve')
        axes[0, 0].set_xlabel('Trade Number')
        axes[0, 0].set_ylabel('Portfolio Value')
        axes[0, 0].grid(True)
        
        # Plot drawdown
        axes[0, 1].plot(self.drawdown_curve)
        axes[0, 1].set_title('Drawdown')
        axes[0, 1].set_xlabel('Trade Number')
        axes[0, 1].set_ylabel('Drawdown')
        axes[0, 1].grid(True)
        
        # Plot returns distribution
        sns.histplot(self.returns, ax=axes[1, 0])
        axes[1, 0].set_title('Returns Distribution')
        axes[1, 0].set_xlabel('Return')
        axes[1, 0].set_ylabel('Frequency')
        
        # Plot cumulative returns
        cumulative_returns = np.cumsum(self.returns)
        axes[1, 1].plot(cumulative_returns)
        axes[1, 1].set_title('Cumulative Returns')
        axes[1, 1].set_xlabel('Trade Number')
        axes[1, 1].set_ylabel('Cumulative Return')
        axes[1, 1].grid(True)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path)
        plt.close()
        
    def save_results(self,
                    path: str) -> None:
        """
        Save trading results.
        
        Parameters
        ----------
        path : str
            Path to save results
        """
        results = {
            'initial_capital': self.initial_capital,
            'final_capital': self.portfolio.current_capital,
            'total_return': (self.portfolio.current_capital - self.initial_capital) / self.initial_capital,
            'num_trades': len(self.portfolio.trades),
            'equity_curve': self.equity_curve,
            'drawdown_curve': self.drawdown_curve,
            'returns': self.returns,
            'trades': [
                {
                    'entry_time': trade.entry_time.isoformat(),
                    'entry_price': trade.entry_price,
                    'position_size': trade.position_size,
                    'direction': trade.direction,
                    'stop_loss': trade.stop_loss,
                    'take_profit': trade.take_profit,
                    'exit_time': trade.exit_time.isoformat() if trade.exit_time else None,
                    'exit_price': trade.exit_price,
                    'pnl': trade.pnl,
                    'exit_reason': trade.exit_reason
                }
                for trade in self.portfolio.trades
            ],
            'performance_metrics': self.get_performance_metrics()
        }
        
        with open(path, 'w') as f:
            json.dump(results, f, indent=4)
            
def main():
    """Example usage of the Brownfield trader."""
    # Create sample data
    dates = pd.date_range(start='2020-01-01', end='2020-12-31', freq='D')
    data = pd.DataFrame({
        'open': np.random.normal(100, 1, len(dates)),
        'high': np.random.normal(101, 1, len(dates)),
        'low': np.random.normal(99, 1, len(dates)),
        'close': np.random.normal(100, 1, len(dates)),
        'volume': np.random.normal(1000000, 100000, len(dates)),
        'volatility': np.random.normal(0.01, 0.001, len(dates))
    }, index=dates)
    
    # Create model
    model = BrownfieldPredictor(
        input_dim=6,  # OHLCV + volatility
        hidden_dim=64,
        num_layers=2,
        num_heads=4,
        dropout=0.1
    )
    
    # Create trader
    trader = BrownfieldTrader(
        model=model,
        initial_capital=100000.0,
        max_position_size=0.1,
        max_drawdown=0.15,
        risk_reward_ratio=3.0,
        transaction_cost=0.001
    )
    
    # Process each bar
    for idx, bar in data.iterrows():
        trader.process_bar('SPY', bar)
        
    # Plot performance
    trader.plot_performance(save_path='performance.png')
    
    # Save results
    trader.save_results('trading_results.json')
    
    # Print performance metrics
    metrics = trader.get_performance_metrics()
    print("\nPerformance Metrics:")
    for metric, value in metrics.items():
        print(f"{metric}: {value:.4f}")

if __name__ == "__main__":
    main() 