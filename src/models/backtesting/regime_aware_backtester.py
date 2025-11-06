"""
Regime-Aware Backtesting Framework

This module implements a comprehensive backtesting framework that:
- Supports multiple asset classes (metals, stocks, bonds)
- Detects regime changes (including tariff events)
- Implements Brownfield-style risk management
- Provides detailed performance analytics
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
from ..deep_learning.brownfield_predictor import BrownfieldPredictor
from ..paper_trading.brownfield_trader import BrownfieldTrader

@dataclass
class Asset:
    """Represents a trading asset."""
    symbol: str
    asset_type: str  # 'metal', 'stock', 'bond'
    data: pd.DataFrame
    regime_sensitivity: float  # How sensitive to regime changes (0-1)
    volatility: float
    correlation: float  # Correlation with regime indicator

@dataclass
class RegimeEvent:
    """Represents a regime change event."""
    date: datetime
    event_type: str  # 'tariff', 'policy', 'market'
    magnitude: float  # Impact magnitude (-1 to 1)
    affected_assets: List[str]
    description: str

class RegimeAwareBacktester:
    """
    Backtesting framework with regime awareness.
    """
    def __init__(self,
                 initial_capital: float = 1000000.0,
                 max_position_size: float = 0.1,
                 max_drawdown: float = 0.15,
                 risk_reward_ratio: float = 3.0,
                 transaction_cost: float = 0.001):
        """
        Initialize the backtester.
        
        Parameters
        ----------
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
        self.initial_capital = initial_capital
        self.max_position_size = max_position_size
        self.max_drawdown = max_drawdown
        self.risk_reward_ratio = risk_reward_ratio
        self.transaction_cost = transaction_cost
        
        # Initialize components
        self.assets: Dict[str, Asset] = {}
        self.regime_events: List[RegimeEvent] = []
        self.regime_indicator: pd.Series = None
        
        # Performance tracking
        self.portfolio_value = []
        self.positions = {}
        self.trades = []
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            
    def add_asset(self,
                  symbol: str,
                  asset_type: str,
                  data: pd.DataFrame,
                  regime_sensitivity: float = 0.5) -> None:
        """
        Add an asset to the backtester.
        
        Parameters
        ----------
        symbol : str
            Asset symbol
        asset_type : str
            Asset type ('metal', 'stock', 'bond')
        data : pd.DataFrame
            Price data
        regime_sensitivity : float
            Sensitivity to regime changes
        """
        # Calculate volatility
        returns = data['close'].pct_change()
        volatility = returns.std() * np.sqrt(252)
        
        # Calculate correlation with regime indicator if available
        correlation = 0.0
        if self.regime_indicator is not None:
            correlation = returns.corr(self.regime_indicator)
            
        self.assets[symbol] = Asset(
            symbol=symbol,
            asset_type=asset_type,
            data=data,
            regime_sensitivity=regime_sensitivity,
            volatility=volatility,
            correlation=correlation
        )
        
    def add_regime_event(self,
                        date: datetime,
                        event_type: str,
                        magnitude: float,
                        affected_assets: List[str],
                        description: str) -> None:
        """
        Add a regime change event.
        
        Parameters
        ----------
        date : datetime
            Event date
        event_type : str
            Event type
        magnitude : float
            Impact magnitude
        affected_assets : List[str]
            Affected assets
        description : str
            Event description
        """
        self.regime_events.append(RegimeEvent(
            date=date,
            event_type=event_type,
            magnitude=magnitude,
            affected_assets=affected_assets,
            description=description
        ))
        
    def calculate_regime_indicator(self, start_date: datetime, end_date: datetime) -> None:
        """
        Calculate regime indicator from events.
        
        Parameters
        ----------
        start_date : datetime
            Start date of backtest
        end_date : datetime
            End date of backtest
        """
        if not self.regime_events:
            return
            
        # Create time series of regime impact for the entire backtest period
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # Initialize as float to avoid dtype warnings
        regime_impact = pd.Series(0.0, index=dates)
        
        for event in self.regime_events:
            # Only process events within the backtest period
            if start_date <= event.date <= end_date:
                # Add immediate impact
                regime_impact[event.date] += event.magnitude
                
                # Add decaying impact
                decay_days = 30
                decay = np.exp(-np.arange(decay_days) / 7)  # Weekly decay
                
                # Get the correct date range for decay
                decay_dates = pd.date_range(event.date, periods=decay_days, freq='D')
                
                # Only update dates that exist in regime_impact
                valid_dates = decay_dates.intersection(regime_impact.index)
                if len(valid_dates) > 0:
                    regime_impact.loc[valid_dates] += event.magnitude * decay[:len(valid_dates)]
            
        self.regime_indicator = regime_impact
        
    def adjust_position_size(self,
                           asset: Asset,
                           current_regime: float) -> float:
        """
        Adjust position size based on regime.
        
        Parameters
        ----------
        asset : Asset
            Trading asset
        current_regime : float
            Current regime indicator value
            
        Returns
        -------
        float
            Adjusted position size
        """
        # Base position size
        base_size = self.initial_capital * self.max_position_size
        
        # Adjust for regime sensitivity
        regime_adjustment = 1 - abs(asset.regime_sensitivity * current_regime)
        
        # Adjust for volatility
        vol_adjustment = 1 / (1 + asset.volatility)
        
        # Adjust for correlation
        corr_adjustment = 1 - abs(asset.correlation)
        
        # Calculate final position size
        position_size = base_size * regime_adjustment * vol_adjustment * corr_adjustment
        
        return min(position_size, base_size)
        
    def run_backtest(self,
                    start_date: datetime,
                    end_date: datetime) -> Dict[str, float]:
        """
        Run backtest.
        
        Parameters
        ----------
        start_date : datetime
            Start date
        end_date : datetime
            End date
            
        Returns
        -------
        Dict[str, float]
            Performance metrics
        """
        # Calculate regime indicator
        self.calculate_regime_indicator(start_date, end_date)
        
        # Initialize portfolio
        portfolio_value = self.initial_capital
        self.portfolio_value = [portfolio_value]
        
        # Get common date range
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        
        for date in dates:
            # Get current regime
            current_regime = self.regime_indicator[date] if self.regime_indicator is not None else 0
            
            # Process each asset
            for symbol, asset in self.assets.items():
                if date in asset.data.index:
                    # Get current price
                    price = asset.data.loc[date, 'close']
                    
                    # Calculate position size
                    position_size = self.adjust_position_size(asset, current_regime)
                    
                    # Update portfolio
                    if symbol in self.positions:
                        # Close existing position
                        old_position = self.positions[symbol]
                        pnl = (price - old_position['entry_price']) * old_position['size']
                        portfolio_value += pnl
                        
                        # Record trade
                        self.trades.append({
                            'symbol': symbol,
                            'entry_date': old_position['entry_date'],
                            'exit_date': date,
                            'entry_price': old_position['entry_price'],
                            'exit_price': price,
                            'size': old_position['size'],
                            'pnl': pnl
                        })
                        
                    # Open new position
                    self.positions[symbol] = {
                        'entry_date': date,
                        'entry_price': price,
                        'size': position_size
                    }
                    
            # Record portfolio value
            self.portfolio_value.append(portfolio_value)
            
        return self.calculate_performance_metrics()
        
    def _to_serializable(self, obj):
        """Recursively convert numpy/pandas objects to native Python types for JSON serialization."""
        if isinstance(obj, (np.integer, int)):
            return int(obj)
        elif isinstance(obj, (np.floating, float)):
            return float(obj)
        elif isinstance(obj, (np.ndarray, list, pd.Series)):
            return [self._to_serializable(x) for x in obj]
        elif isinstance(obj, dict):
            return {k: self._to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        else:
            return obj

    def calculate_performance_metrics(self) -> dict:
        """
        Calculate performance metrics.
        Returns
        -------
        Dict[str, float]
            Performance metrics
        """
        if not self.portfolio_value:
            return {}
        # Calculate returns
        returns = pd.Series(self.portfolio_value).pct_change().dropna()
        # Calculate metrics
        total_return = float((self.portfolio_value[-1] - self.initial_capital) / self.initial_capital)
        sharpe_ratio = float(returns.mean() / returns.std() * np.sqrt(252)) if returns.std() != 0 else float('nan')
        max_drawdown = float((pd.Series(self.portfolio_value).cummax() - self.portfolio_value).max() / pd.Series(self.portfolio_value).cummax().max())
        # Calculate trade metrics
        trade_returns = [float(t['pnl'] / (t['size'] * t['entry_price'])) for t in self.trades if t['size'] and t['entry_price']]
        win_rate = float(len([r for r in trade_returns if r > 0]) / len(trade_returns)) if trade_returns else 0.0
        return {
            'total_return': total_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'num_trades': int(len(self.trades)),
            'avg_trade_return': float(np.mean(trade_returns)) if trade_returns else 0.0
        }

    def plot_results(self,
                    save_path: Optional[str] = None) -> None:
        """
        Plot backtest results.
        
        Parameters
        ----------
        save_path : Optional[str]
            Path to save plots
        """
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # Plot portfolio value
        axes[0, 0].plot(self.portfolio_value)
        axes[0, 0].set_title('Portfolio Value')
        axes[0, 0].set_xlabel('Time')
        axes[0, 0].set_ylabel('Value')
        axes[0, 0].grid(True)
        
        # Plot regime indicator
        if self.regime_indicator is not None:
            axes[0, 1].plot(self.regime_indicator)
            axes[0, 1].set_title('Regime Indicator')
            axes[0, 1].set_xlabel('Time')
            axes[0, 1].set_ylabel('Regime Impact')
            axes[0, 1].grid(True)
            
        # Plot drawdown
        drawdown = (pd.Series(self.portfolio_value).cummax() - self.portfolio_value) / pd.Series(self.portfolio_value).cummax()
        axes[1, 0].plot(drawdown)
        axes[1, 0].set_title('Drawdown')
        axes[1, 0].set_xlabel('Time')
        axes[1, 0].set_ylabel('Drawdown')
        axes[1, 0].grid(True)
        
        # Plot trade returns distribution
        trade_returns = [t['pnl'] / (t['size'] * t['entry_price']) for t in self.trades]
        sns.histplot(trade_returns, ax=axes[1, 1])
        axes[1, 1].set_title('Trade Returns Distribution')
        axes[1, 1].set_xlabel('Return')
        axes[1, 1].set_ylabel('Frequency')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path)
        plt.close()
        
    def save_results(self,
                    path: str) -> None:
        """
        Save backtest results.
        
        Parameters
        ----------
        path : str
            Path to save results
        """
        results = {
            'initial_capital': float(self.initial_capital),
            'final_value': float(self.portfolio_value[-1]) if hasattr(self.portfolio_value, '__getitem__') else self.portfolio_value,
            'portfolio_value': list(self.portfolio_value) if isinstance(self.portfolio_value, (pd.Series, list, np.ndarray)) else [self.portfolio_value],
            'performance_metrics': self.calculate_performance_metrics(),
            'trades': self.trades,
            'regime_events': [
                {
                    'date': e.date.isoformat(),
                    'event_type': e.event_type,
                    'magnitude': e.magnitude,
                    'affected_assets': e.affected_assets,
                    'description': e.description
                }
                for e in self.regime_events
            ],
            # Serialize regime_indicator as a list of dicts
            'regime_indicator': [
                {'date': idx.strftime('%Y-%m-%d'), 'value': float(val)}
                for idx, val in self.regime_indicator.items()
            ] if self.regime_indicator is not None else None
        }
        # Recursively convert all numpy/pandas objects
        results = self._to_serializable(results)
        with open(path, 'w') as f:
            json.dump(results, f, indent=4)

def main():
    """Example usage of the regime-aware backtester."""
    # Create backtester
    backtester = RegimeAwareBacktester(
        initial_capital=1000000.0,
        max_position_size=0.1,
        max_drawdown=0.15,
        risk_reward_ratio=3.0
    )
    
    # Add sample regime events
    backtester.add_regime_event(
        date=datetime(2018, 3, 1),
        event_type='tariff',
        magnitude=0.5,
        affected_assets=['GOLD', 'SILVER', 'TLT'],
        description='US-China trade war escalation'
    )
    
    backtester.add_regime_event(
        date=datetime(2019, 12, 15),
        event_type='tariff',
        magnitude=-0.3,
        affected_assets=['GOLD', 'SILVER', 'TLT'],
        description='US-China phase one trade deal'
    )
    
    # Add sample assets
    # Note: In practice, you would load real data here
    dates = pd.date_range(start='2018-01-01', end='2020-12-31', freq='D')
    
    # Gold
    gold_data = pd.DataFrame({
        'close': np.random.normal(1500, 50, len(dates)),
        'volume': np.random.normal(1000000, 100000, len(dates))
    }, index=dates)
    backtester.add_asset('GOLD', 'metal', gold_data, regime_sensitivity=0.8)
    
    # Silver
    silver_data = pd.DataFrame({
        'close': np.random.normal(20, 1, len(dates)),
        'volume': np.random.normal(500000, 50000, len(dates))
    }, index=dates)
    backtester.add_asset('SILVER', 'metal', silver_data, regime_sensitivity=0.7)
    
    # Treasury bonds
    tlt_data = pd.DataFrame({
        'close': np.random.normal(120, 5, len(dates)),
        'volume': np.random.normal(2000000, 200000, len(dates))
    }, index=dates)
    backtester.add_asset('TLT', 'bond', tlt_data, regime_sensitivity=0.6)
    
    # Run backtest
    metrics = backtester.run_backtest(
        start_date=datetime(2018, 1, 1),
        end_date=datetime(2020, 12, 31)
    )
    
    # Plot results
    backtester.plot_results(save_path='backtest_results.png')
    
    # Save results
    backtester.save_results('backtest_results.json')
    
    # Print metrics
    print("\nBacktest Results:")
    for metric, value in metrics.items():
        print(f"{metric}: {value:.4f}")

if __name__ == "__main__":
    main() 