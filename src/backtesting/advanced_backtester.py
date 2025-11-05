"""
Advanced Backtesting Framework

This module implements a comprehensive backtesting framework with support for
multiple strategies, risk management, and detailed performance analysis.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Callable
import logging
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import json
from src.models.lstm_predictor import LSTMPredictor
from src.models.rl_trading_agent import PPOTrader

class Strategy:
    """
    Base class for trading strategies.
    """
    def __init__(self, name: str):
        """
        Initialize the strategy.
        
        Parameters
        ----------
        name : str
            Strategy name
        """
        self.name = name
        
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """
        Generate trading signals.
        
        Parameters
        ----------
        data : pd.DataFrame
            Market data
            
        Returns
        -------
        pd.Series
            Trading signals (-1 to 1)
        """
        raise NotImplementedError

class LSTMPredictorStrategy(Strategy):
    """
    Strategy using LSTM predictions.
    """
    def __init__(self, model_path: str):
        """
        Initialize the LSTM strategy.
        
        Parameters
        ----------
        model_path : str
            Path to trained LSTM model
        """
        super().__init__('LSTM')
        self.model = LSTMPredictor(
            input_dim=10,  # Adjust based on your features
            hidden_dim=64,
            num_layers=2,
            output_dim=1
        )
        self.model.load_state_dict(torch.load(model_path))
        self.model.eval()
        
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate signals using LSTM predictions."""
        with torch.no_grad():
            predictions = self.model(torch.FloatTensor(data.values))
        return pd.Series(predictions.numpy(), index=data.index)

class RLStrategy(Strategy):
    """
    Strategy using trained RL agent.
    """
    def __init__(self, model_path: str):
        """
        Initialize the RL strategy.
        
        Parameters
        ----------
        model_path : str
            Path to trained RL model
        """
        super().__init__('RL')
        self.agent = PPOTrader(None)  # Environment not needed for inference
        self.agent.load(model_path)
        
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate signals using RL agent."""
        signals = []
        for i in range(len(data)):
            obs = {
                'market_data': data.iloc[i-20:i].values if i >= 20 else data.iloc[:i+1].values,
                'position': np.array([0.0]),
                'balance': np.array([100000.0])
            }
            with torch.no_grad():
                action, _ = self.agent.actor_critic(
                    self.agent._process_observation(obs).unsqueeze(0)
                )
            signals.append(action.item())
        return pd.Series(signals, index=data.index)

class RiskManager:
    """
    Risk management system.
    """
    def __init__(self,
                 max_position_size: float = 1.0,
                 max_drawdown: float = 0.2,
                 stop_loss: float = 0.05,
                 take_profit: float = 0.1):
        """
        Initialize the risk manager.
        
        Parameters
        ----------
        max_position_size : float
            Maximum position size as a fraction of portfolio
        max_drawdown : float
            Maximum allowed drawdown
        stop_loss : float
            Stop loss level
        take_profit : float
            Take profit level
        """
        self.max_position_size = max_position_size
        self.max_drawdown = max_drawdown
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        
    def adjust_position(self,
                       signal: float,
                       current_position: float,
                       portfolio_value: float,
                       current_drawdown: float) -> float:
        """
        Adjust position based on risk parameters.
        
        Parameters
        ----------
        signal : float
            Strategy signal
        current_position : float
            Current position size
        portfolio_value : float
            Current portfolio value
        current_drawdown : float
            Current drawdown
            
        Returns
        -------
        float
            Adjusted position size
        """
        # Check drawdown limit
        if current_drawdown > self.max_drawdown:
            return 0.0
            
        # Apply position size limit
        position = signal * self.max_position_size
        
        # Check stop loss
        if current_position > 0 and signal < -self.stop_loss:
            return 0.0
        elif current_position < 0 and signal > self.stop_loss:
            return 0.0
            
        # Check take profit
        if current_position > 0 and signal > self.take_profit:
            return 0.0
        elif current_position < 0 and signal < -self.take_profit:
            return 0.0
            
        return position

class AdvancedBacktester:
    """
    Advanced backtesting framework.
    """
    def __init__(self,
                 data: pd.DataFrame,
                 initial_capital: float = 100000.0,
                 transaction_cost: float = 0.001):
        """
        Initialize the backtester.
        
        Parameters
        ----------
        data : pd.DataFrame
            Market data
        initial_capital : float
            Initial capital
        transaction_cost : float
            Transaction cost as a fraction
        """
        self.data = data
        self.initial_capital = initial_capital
        self.transaction_cost = transaction_cost
        self.strategies: Dict[str, Strategy] = {}
        self.risk_manager = RiskManager()
        
        # Create necessary directories
        Path('data/backtests').mkdir(parents=True, exist_ok=True)
        Path('data/plots').mkdir(parents=True, exist_ok=True)
        
    def add_strategy(self, strategy: Strategy):
        """
        Add a strategy to the backtester.
        
        Parameters
        ----------
        strategy : Strategy
            Trading strategy
        """
        self.strategies[strategy.name] = strategy
        
    def run_backtest(self,
                    start_date: Optional[datetime] = None,
                    end_date: Optional[datetime] = None) -> Dict:
        """
        Run backtest for all strategies.
        
        Parameters
        ----------
        start_date : Optional[datetime]
            Start date for backtest
        end_date : Optional[datetime]
            End date for backtest
            
        Returns
        -------
        Dict
            Backtest results
        """
        results = {}
        
        # Filter data for date range
        if start_date and end_date:
            mask = (self.data.index >= start_date) & (self.data.index <= end_date)
            data = self.data[mask].copy()
        else:
            data = self.data.copy()
            
        for name, strategy in self.strategies.items():
            # Generate signals
            signals = strategy.generate_signals(data)
            
            # Initialize portfolio
            portfolio_value = self.initial_capital
            position = 0.0
            trades = []
            
            # Run simulation
            for i in range(1, len(data)):
                # Get current price and signal
                current_price = data.iloc[i]['Close']
                signal = signals.iloc[i]
                
                # Calculate current drawdown
                if i > 0:
                    current_drawdown = (portfolio_value - self.initial_capital) / self.initial_capital
                else:
                    current_drawdown = 0.0
                    
                # Adjust position based on risk management
                new_position = self.risk_manager.adjust_position(
                    signal=signal,
                    current_position=position,
                    portfolio_value=portfolio_value,
                    current_drawdown=current_drawdown
                )
                
                # Calculate position change and transaction cost
                position_change = abs(new_position - position)
                transaction_cost = position_change * portfolio_value * self.transaction_cost
                
                # Update portfolio
                price_change = (current_price - data.iloc[i-1]['Close']) / data.iloc[i-1]['Close']
                portfolio_return = position * price_change
                portfolio_value = portfolio_value * (1 + portfolio_return) - transaction_cost
                position = new_position
                
                # Record trade
                if position_change > 0:
                    trades.append({
                        'date': data.index[i],
                        'price': current_price,
                        'position': position,
                        'portfolio_value': portfolio_value,
                        'transaction_cost': transaction_cost
                    })
                    
            # Calculate performance metrics
            results[name] = self._calculate_metrics(trades, portfolio_value)
            
            # Plot results
            self._plot_results(name, trades, data)
            
        return results
        
    def _calculate_metrics(self,
                          trades: List[Dict],
                          final_value: float) -> Dict:
        """
        Calculate performance metrics.
        
        Parameters
        ----------
        trades : List[Dict]
            List of trades
        final_value : float
            Final portfolio value
            
        Returns
        -------
        Dict
            Performance metrics
        """
        if not trades:
            return {}
            
        # Convert trades to DataFrame
        trades_df = pd.DataFrame(trades)
        
        # Calculate returns
        returns = trades_df['portfolio_value'].pct_change()
        
        # Calculate metrics
        total_return = (final_value - self.initial_capital) / self.initial_capital
        sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252)
        max_drawdown = (trades_df['portfolio_value'].cummax() - trades_df['portfolio_value']).max() / trades_df['portfolio_value'].cummax()
        win_rate = (returns > 0).mean()
        
        # Calculate additional metrics
        metrics = {
            'total_return': total_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'num_trades': len(trades),
            'avg_trade_return': returns.mean(),
            'volatility': returns.std() * np.sqrt(252),
            'avg_holding_period': self._calculate_avg_holding_period(trades),
            'profit_factor': self._calculate_profit_factor(returns),
            'calmar_ratio': total_return / max_drawdown if max_drawdown > 0 else 0
        }
        
        return metrics
        
    def _calculate_avg_holding_period(self, trades: List[Dict]) -> float:
        """Calculate average holding period in days."""
        if len(trades) < 2:
            return 0.0
        holding_periods = []
        for i in range(1, len(trades)):
            period = (trades[i]['date'] - trades[i-1]['date']).days
            if period > 0:
                holding_periods.append(period)
        return np.mean(holding_periods) if holding_periods else 0.0
        
    def _calculate_profit_factor(self, returns: pd.Series) -> float:
        """Calculate profit factor."""
        gross_profit = returns[returns > 0].sum()
        gross_loss = abs(returns[returns < 0].sum())
        return gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
    def _plot_results(self,
                     strategy_name: str,
                     trades: List[Dict],
                     data: pd.DataFrame):
        """
        Plot backtest results.
        
        Parameters
        ----------
        strategy_name : str
            Name of the strategy
        trades : List[Dict]
            List of trades
        data : pd.DataFrame
            Market data
        """
        # Convert trades to DataFrame
        trades_df = pd.DataFrame(trades)
        
        # Create figure with subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [3, 1]})
        
        # Plot portfolio value
        ax1.plot(trades_df['date'], trades_df['portfolio_value'], label='Portfolio Value')
        ax1.set_title(f'{strategy_name} Strategy Performance')
        ax1.set_ylabel('Portfolio Value ($)')
        ax1.grid(True)
        ax1.legend()
        
        # Plot drawdown
        drawdown = (trades_df['portfolio_value'].cummax() - trades_df['portfolio_value']) / trades_df['portfolio_value'].cummax()
        ax2.fill_between(trades_df['date'], drawdown, 0, color='red', alpha=0.3)
        ax2.set_title('Drawdown')
        ax2.set_ylabel('Drawdown')
        ax2.set_xlabel('Date')
        ax2.grid(True)
        
        # Save plot
        plt.tight_layout()
        plt.savefig(f'data/plots/backtest_{strategy_name}.png')
        plt.close()
        
    def save_results(self, results: Dict, filename: str):
        """
        Save backtest results to file.
        
        Parameters
        ----------
        results : Dict
            Backtest results
        filename : str
            Output filename
        """
        # Convert results to DataFrame
        results_df = pd.DataFrame(results).T
        
        # Save to CSV
        results_df.to_csv(f'data/backtests/{filename}.csv')
        
        # Save detailed results to JSON
        with open(f'data/backtests/{filename}.json', 'w') as f:
            json.dump(results, f, indent=4)

def main():
    """Example usage of the advanced backtester."""
    # Load market data
    data = pd.DataFrame()  # Your market data here
    
    # Create backtester
    backtester = AdvancedBacktester(
        data=data,
        initial_capital=100000.0,
        transaction_cost=0.001
    )
    
    # Add strategies
    backtester.add_strategy(LSTMPredictorStrategy('data/models/best_lstm_model.pth'))
    backtester.add_strategy(RLStrategy('data/models/ppo_trader.pth'))
    
    # Run backtest
    results = backtester.run_backtest(
        start_date=datetime(2020, 1, 1),
        end_date=datetime(2021, 12, 31)
    )
    
    # Save results
    backtester.save_results(results, 'backtest_results')
    
    # Print results
    print("\nBacktest Results:")
    for strategy, metrics in results.items():
        print(f"\n{strategy}:")
        for metric, value in metrics.items():
            print(f"{metric}: {value:.4f}")

if __name__ == "__main__":
    main() 