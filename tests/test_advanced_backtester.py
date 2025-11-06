"""
Tests for the advanced backtesting framework.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import torch
from pathlib import Path
from src.backtesting.advanced_backtester import (
    Strategy,
    LSTMPredictorStrategy,
    RLStrategy,
    RiskManager,
    AdvancedBacktester
)

class MockStrategy(Strategy):
    """Mock strategy for testing."""
    def __init__(self, name: str, signals: pd.Series):
        super().__init__(name)
        self.signals = signals
        
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        return self.signals

@pytest.fixture
def sample_data():
    """Create sample market data for testing."""
    dates = pd.date_range(start='2020-01-01', end='2020-12-31', freq='D')
    data = pd.DataFrame({
        'Open': np.random.normal(100, 1, len(dates)),
        'High': np.random.normal(101, 1, len(dates)),
        'Low': np.random.normal(99, 1, len(dates)),
        'Close': np.random.normal(100, 1, len(dates)),
        'Volume': np.random.normal(1000000, 100000, len(dates))
    }, index=dates)
    return data

@pytest.fixture
def sample_signals():
    """Create sample trading signals."""
    dates = pd.date_range(start='2020-01-01', end='2020-12-31', freq='D')
    signals = pd.Series(np.random.uniform(-1, 1, len(dates)), index=dates)
    return signals

class TestStrategy:
    """Tests for the Strategy base class."""
    
    def test_strategy_initialization(self):
        """Test strategy initialization."""
        strategy = MockStrategy('Test', pd.Series())
        assert strategy.name == 'Test'
        
    def test_generate_signals_not_implemented(self):
        """Test that base class raises NotImplementedError."""
        strategy = Strategy('Test')
        with pytest.raises(NotImplementedError):
            strategy.generate_signals(pd.DataFrame())

class TestLSTMPredictorStrategy:
    """Tests for the LSTM predictor strategy."""
    
    def test_lstm_strategy_initialization(self, tmp_path):
        """Test LSTM strategy initialization."""
        # Create a dummy model file
        model_path = tmp_path / "dummy_model.pth"
        torch.save(torch.randn(10), model_path)
        
        strategy = LSTMPredictorStrategy(str(model_path))
        assert strategy.name == 'LSTM'
        assert isinstance(strategy.model, torch.nn.Module)
        
    def test_lstm_strategy_signal_generation(self, tmp_path, sample_data):
        """Test LSTM strategy signal generation."""
        # Create a dummy model file
        model_path = tmp_path / "dummy_model.pth"
        torch.save(torch.randn(10), model_path)
        
        strategy = LSTMPredictorStrategy(str(model_path))
        signals = strategy.generate_signals(sample_data)
        assert isinstance(signals, pd.Series)
        assert len(signals) == len(sample_data)

class TestRLStrategy:
    """Tests for the RL strategy."""
    
    def test_rl_strategy_initialization(self, tmp_path):
        """Test RL strategy initialization."""
        # Create a dummy model file
        model_path = tmp_path / "dummy_model.pth"
        torch.save(torch.randn(10), model_path)
        
        strategy = RLStrategy(str(model_path))
        assert strategy.name == 'RL'
        
    def test_rl_strategy_signal_generation(self, tmp_path, sample_data):
        """Test RL strategy signal generation."""
        # Create a dummy model file
        model_path = tmp_path / "dummy_model.pth"
        torch.save(torch.randn(10), model_path)
        
        strategy = RLStrategy(str(model_path))
        signals = strategy.generate_signals(sample_data)
        assert isinstance(signals, pd.Series)
        assert len(signals) == len(sample_data)

class TestRiskManager:
    """Tests for the risk management system."""
    
    @pytest.fixture
    def risk_manager(self):
        """Create a risk manager instance."""
        return RiskManager(
            max_position_size=1.0,
            max_drawdown=0.2,
            stop_loss=0.05,
            take_profit=0.1
        )
        
    def test_risk_manager_initialization(self, risk_manager):
        """Test risk manager initialization."""
        assert risk_manager.max_position_size == 1.0
        assert risk_manager.max_drawdown == 0.2
        assert risk_manager.stop_loss == 0.05
        assert risk_manager.take_profit == 0.1
        
    def test_position_adjustment_drawdown(self, risk_manager):
        """Test position adjustment with drawdown limit."""
        position = risk_manager.adjust_position(
            signal=1.0,
            current_position=0.0,
            portfolio_value=100000.0,
            current_drawdown=0.25  # Exceeds max_drawdown
        )
        assert position == 0.0
        
    def test_position_adjustment_stop_loss(self, risk_manager):
        """Test position adjustment with stop loss."""
        position = risk_manager.adjust_position(
            signal=-0.06,  # Exceeds stop loss
            current_position=1.0,
            portfolio_value=100000.0,
            current_drawdown=0.1
        )
        assert position == 0.0
        
    def test_position_adjustment_take_profit(self, risk_manager):
        """Test position adjustment with take profit."""
        position = risk_manager.adjust_position(
            signal=0.11,  # Exceeds take profit
            current_position=1.0,
            portfolio_value=100000.0,
            current_drawdown=0.1
        )
        assert position == 0.0

class TestAdvancedBacktester:
    """Tests for the advanced backtesting framework."""
    
    @pytest.fixture
    def backtester(self, sample_data):
        """Create a backtester instance."""
        return AdvancedBacktester(
            data=sample_data,
            initial_capital=100000.0,
            transaction_cost=0.001
        )
        
    def test_backtester_initialization(self, backtester, sample_data):
        """Test backtester initialization."""
        assert backtester.data.equals(sample_data)
        assert backtester.initial_capital == 100000.0
        assert backtester.transaction_cost == 0.001
        assert isinstance(backtester.strategies, dict)
        assert isinstance(backtester.risk_manager, RiskManager)
        
    def test_add_strategy(self, backtester, sample_signals):
        """Test adding a strategy."""
        strategy = MockStrategy('Test', sample_signals)
        backtester.add_strategy(strategy)
        assert 'Test' in backtester.strategies
        assert backtester.strategies['Test'] == strategy
        
    def test_run_backtest(self, backtester, sample_signals):
        """Test running a backtest."""
        strategy = MockStrategy('Test', sample_signals)
        backtester.add_strategy(strategy)
        
        results = backtester.run_backtest(
            start_date=datetime(2020, 1, 1),
            end_date=datetime(2020, 12, 31)
        )
        
        assert 'Test' in results
        assert isinstance(results['Test'], dict)
        assert all(key in results['Test'] for key in [
            'total_return', 'sharpe_ratio', 'max_drawdown',
            'win_rate', 'num_trades', 'avg_trade_return',
            'volatility', 'avg_holding_period', 'profit_factor',
            'calmar_ratio'
        ])
        
    def test_calculate_metrics(self, backtester):
        """Test performance metrics calculation."""
        trades = [
            {
                'date': datetime(2020, 1, 1),
                'price': 100.0,
                'position': 1.0,
                'portfolio_value': 100000.0,
                'transaction_cost': 100.0
            },
            {
                'date': datetime(2020, 1, 2),
                'price': 101.0,
                'position': 0.0,
                'portfolio_value': 101000.0,
                'transaction_cost': 100.0
            }
        ]
        
        metrics = backtester._calculate_metrics(trades, 101000.0)
        assert isinstance(metrics, dict)
        assert metrics['total_return'] == 0.01
        assert metrics['num_trades'] == 2
        
    def test_save_results(self, backtester, sample_signals, tmp_path):
        """Test saving backtest results."""
        strategy = MockStrategy('Test', sample_signals)
        backtester.add_strategy(strategy)
        
        results = backtester.run_backtest()
        backtester.save_results(results, 'test_results')
        
        # Check if files were created
        assert Path('data/backtests/test_results.csv').exists()
        assert Path('data/backtests/test_results.json').exists()
        
    def test_plot_results(self, backtester, sample_signals):
        """Test plotting backtest results."""
        strategy = MockStrategy('Test', sample_signals)
        backtester.add_strategy(strategy)
        
        results = backtester.run_backtest()
        
        # Check if plot was created
        assert Path('data/plots/backtest_Test.png').exists()

def main():
    """Run the tests."""
    pytest.main([__file__])

if __name__ == "__main__":
    main() 