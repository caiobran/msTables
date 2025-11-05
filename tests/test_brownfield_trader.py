"""
Tests for the Brownfield trader implementation.
"""

import unittest
import pandas as pd
import numpy as np
import torch
from datetime import datetime
from src.models.deep_learning.brownfield_predictor import BrownfieldPredictor
from src.models.paper_trading.brownfield_trader import BrownfieldTrader, Trade, Portfolio

class TestBrownfieldTrader(unittest.TestCase):
    """Test cases for the Brownfield trader."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create sample data
        self.dates = pd.date_range(start='2020-01-01', end='2020-12-31', freq='D')
        self.data = pd.DataFrame({
            'open': np.random.normal(100, 1, len(self.dates)),
            'high': np.random.normal(101, 1, len(self.dates)),
            'low': np.random.normal(99, 1, len(self.dates)),
            'close': np.random.normal(100, 1, len(self.dates)),
            'volume': np.random.normal(1000000, 100000, len(self.dates)),
            'volatility': np.random.normal(0.01, 0.001, len(self.dates))
        }, index=self.dates)
        
        # Create model
        self.model = BrownfieldPredictor(
            input_dim=6,  # OHLCV + volatility
            hidden_dim=64,
            num_layers=2,
            num_heads=4,
            dropout=0.1
        )
        
        # Create trader
        self.trader = BrownfieldTrader(
            model=self.model,
            initial_capital=100000.0,
            max_position_size=0.1,
            max_drawdown=0.15,
            risk_reward_ratio=3.0,
            transaction_cost=0.001
        )
        
    def test_initialization(self):
        """Test trader initialization."""
        self.assertEqual(self.trader.initial_capital, 100000.0)
        self.assertEqual(self.trader.max_position_size, 0.1)
        self.assertEqual(self.trader.max_drawdown, 0.15)
        self.assertEqual(self.trader.risk_reward_ratio, 3.0)
        self.assertEqual(self.trader.transaction_cost, 0.001)
        
        # Check portfolio initialization
        self.assertEqual(self.trader.portfolio.initial_capital, 100000.0)
        self.assertEqual(self.trader.portfolio.current_capital, 100000.0)
        self.assertEqual(len(self.trader.portfolio.positions), 0)
        self.assertEqual(len(self.trader.portfolio.trades), 0)
        self.assertEqual(self.trader.portfolio.cash, 100000.0)
        self.assertEqual(self.trader.portfolio.margin_used, 0.0)
        self.assertEqual(self.trader.portfolio.margin_available, 100000.0)
        
    def test_calculate_position_size(self):
        """Test position size calculation."""
        # Test with low risk and volatility
        position_size = self.trader.calculate_position_size(
            price=100.0,
            risk_score=0.1,
            volatility=0.01
        )
        self.assertGreater(position_size, 0)
        self.assertLessEqual(position_size, self.trader.initial_capital * self.trader.max_position_size)
        
        # Test with high risk and volatility
        position_size = self.trader.calculate_position_size(
            price=100.0,
            risk_score=0.9,
            volatility=0.05
        )
        self.assertLess(position_size, self.trader.initial_capital * self.trader.max_position_size)
        
    def test_calculate_stop_loss(self):
        """Test stop loss calculation."""
        # Test long position
        stop_loss = self.trader.calculate_stop_loss(
            price=100.0,
            direction='long',
            volatility=0.01
        )
        self.assertLess(stop_loss, 100.0)
        
        # Test short position
        stop_loss = self.trader.calculate_stop_loss(
            price=100.0,
            direction='short',
            volatility=0.01
        )
        self.assertGreater(stop_loss, 100.0)
        
    def test_calculate_take_profit(self):
        """Test take profit calculation."""
        # Test long position
        stop_loss = 95.0
        take_profit = self.trader.calculate_take_profit(
            price=100.0,
            stop_loss=stop_loss,
            direction='long'
        )
        self.assertGreater(take_profit, 100.0)
        self.assertAlmostEqual(
            (take_profit - 100.0) / (100.0 - stop_loss),
            self.trader.risk_reward_ratio
        )
        
        # Test short position
        stop_loss = 105.0
        take_profit = self.trader.calculate_take_profit(
            price=100.0,
            stop_loss=stop_loss,
            direction='short'
        )
        self.assertLess(take_profit, 100.0)
        self.assertAlmostEqual(
            (100.0 - take_profit) / (stop_loss - 100.0),
            self.trader.risk_reward_ratio
        )
        
    def test_open_position(self):
        """Test opening a position."""
        # Open long position
        self.trader.open_position(
            symbol='SPY',
            price=100.0,
            position_size=1000.0,
            direction='long',
            stop_loss=95.0,
            take_profit=110.0
        )
        
        # Check portfolio updates
        self.assertEqual(len(self.trader.portfolio.positions), 1)
        self.assertIn('SPY', self.trader.portfolio.positions)
        
        trade = self.trader.portfolio.positions['SPY']
        self.assertEqual(trade.entry_price, 100.0)
        self.assertEqual(trade.position_size, 1000.0)
        self.assertEqual(trade.direction, 'long')
        self.assertEqual(trade.stop_loss, 95.0)
        self.assertEqual(trade.take_profit, 110.0)
        
        # Check margin updates
        self.assertEqual(self.trader.portfolio.margin_used, 1000.0 * 100.0)
        self.assertEqual(
            self.trader.portfolio.margin_available,
            self.trader.initial_capital - 1000.0 * 100.0
        )
        
    def test_close_position(self):
        """Test closing a position."""
        # Open position
        self.trader.open_position(
            symbol='SPY',
            price=100.0,
            position_size=1000.0,
            direction='long',
            stop_loss=95.0,
            take_profit=110.0
        )
        
        # Close position
        self.trader.close_position(
            symbol='SPY',
            price=105.0,
            reason='take_profit'
        )
        
        # Check portfolio updates
        self.assertEqual(len(self.trader.portfolio.positions), 0)
        self.assertEqual(len(self.trader.portfolio.trades), 1)
        
        trade = self.trader.portfolio.trades[0]
        self.assertEqual(trade.exit_price, 105.0)
        self.assertEqual(trade.pnl, 5000.0)  # (105 - 100) * 1000
        self.assertEqual(trade.exit_reason, 'take_profit')
        
        # Check margin updates
        self.assertEqual(self.trader.portfolio.margin_used, 0.0)
        self.assertEqual(self.trader.portfolio.margin_available, self.trader.initial_capital)
        
    def test_check_stop_loss(self):
        """Test stop loss checking."""
        # Open long position
        self.trader.open_position(
            symbol='SPY',
            price=100.0,
            position_size=1000.0,
            direction='long',
            stop_loss=95.0,
            take_profit=110.0
        )
        
        # Test stop loss hit
        self.assertTrue(self.trader.check_stop_loss('SPY', 94.0))
        self.assertFalse(self.trader.check_stop_loss('SPY', 96.0))
        
        # Open short position
        self.trader.open_position(
            symbol='QQQ',
            price=100.0,
            position_size=1000.0,
            direction='short',
            stop_loss=105.0,
            take_profit=90.0
        )
        
        # Test stop loss hit
        self.assertTrue(self.trader.check_stop_loss('QQQ', 106.0))
        self.assertFalse(self.trader.check_stop_loss('QQQ', 104.0))
        
    def test_check_take_profit(self):
        """Test take profit checking."""
        # Open long position
        self.trader.open_position(
            symbol='SPY',
            price=100.0,
            position_size=1000.0,
            direction='long',
            stop_loss=95.0,
            take_profit=110.0
        )
        
        # Test take profit hit
        self.assertTrue(self.trader.check_take_profit('SPY', 111.0))
        self.assertFalse(self.trader.check_take_profit('SPY', 109.0))
        
        # Open short position
        self.trader.open_position(
            symbol='QQQ',
            price=100.0,
            position_size=1000.0,
            direction='short',
            stop_loss=105.0,
            take_profit=90.0
        )
        
        # Test take profit hit
        self.assertTrue(self.trader.check_take_profit('QQQ', 89.0))
        self.assertFalse(self.trader.check_take_profit('QQQ', 91.0))
        
    def test_check_drawdown(self):
        """Test drawdown checking."""
        # No drawdown initially
        self.assertFalse(self.trader.check_drawdown())
        
        # Simulate some trades
        self.trader.equity_curve = [100000.0, 110000.0, 90000.0]
        self.trader.drawdown_curve = [0.0, 0.0, 0.1818]  # (110000 - 90000) / 110000
        
        # Check drawdown
        self.assertTrue(self.trader.check_drawdown())  # 0.1818 > 0.15
        
    def test_process_bar(self):
        """Test bar processing."""
        # Process a bar
        bar = self.data.iloc[0]
        self.trader.process_bar('SPY', bar)
        
        # Check if position was opened (depends on model prediction)
        if len(self.trader.portfolio.positions) > 0:
            self.assertIn('SPY', self.trader.portfolio.positions)
            trade = self.trader.portfolio.positions['SPY']
            self.assertIsNotNone(trade.entry_price)
            self.assertIsNotNone(trade.position_size)
            self.assertIsNotNone(trade.direction)
            self.assertIsNotNone(trade.stop_loss)
            self.assertIsNotNone(trade.take_profit)
            
    def test_get_performance_metrics(self):
        """Test performance metrics calculation."""
        # Simulate some trades
        self.trader.returns = [0.01, -0.005, 0.02, -0.01, 0.015]
        self.trader.equity_curve = [100000.0, 101000.0, 100495.0, 102504.9, 101479.85, 103002.05]
        self.trader.drawdown_curve = [0.0, 0.0, 0.005, 0.0, 0.01, 0.0]
        
        metrics = self.trader.get_performance_metrics()
        
        self.assertIn('total_return', metrics)
        self.assertIn('sharpe_ratio', metrics)
        self.assertIn('max_drawdown', metrics)
        self.assertIn('win_rate', metrics)
        self.assertIn('profit_factor', metrics)
        self.assertIn('avg_trade', metrics)
        self.assertIn('std_trade', metrics)
        
    def test_save_results(self):
        """Test saving trading results."""
        # Simulate some trades
        self.trader.returns = [0.01, -0.005, 0.02]
        self.trader.equity_curve = [100000.0, 101000.0, 100495.0, 102504.9]
        self.trader.drawdown_curve = [0.0, 0.0, 0.005, 0.0]
        
        # Save results
        self.trader.save_results('test_results.json')
        
        # Check if file was created
        import os
        self.assertTrue(os.path.exists('test_results.json'))
        
        # Clean up
        os.remove('test_results.json')

if __name__ == '__main__':
    unittest.main() 