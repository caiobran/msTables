"""
Reinforcement Learning Trading System

This module implements a reinforcement learning system for trading using the existing
data infrastructure. It uses the data_shepherd for data management and integrates
with the mstables database for historical data.

Features:
- State representation using financial data
- Action space for trading decisions
- Reward function based on portfolio performance
- Integration with existing data infrastructure
- Support for multiple asset classes
"""

import numpy as np
import pandas as pd
import gym
from gym import spaces
import torch
import torch.nn as nn
import torch.optim as optim
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from datetime import datetime, timedelta
import sqlite3
import logging
from typing import Dict, List, Tuple, Optional

from .data_shepherd import DataShepherd

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/logs/rl_trading.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('RLTrading')

class TradingEnvironment(gym.Env):
    """
    Custom Trading Environment that follows gym interface.
    This environment simulates a trading scenario using historical data.
    """
    
    def __init__(self, db_path: str, symbols: List[str], initial_balance: float = 100000.0):
        super(TradingEnvironment, self).__init__()
        
        self.db_path = db_path
        self.symbols = symbols
        self.initial_balance = initial_balance
        self.data_shepherd = DataShepherd(db_path=db_path)
        
        # Define action space (0: hold, 1: buy, 2: sell)
        self.action_space = spaces.Discrete(3)
        
        # Define observation space
        # Features: [price, volume, technical indicators, market data]
        self.observation_space = spaces.Box(
            low=-np.inf, 
            high=np.inf, 
            shape=(len(symbols) * 10,),  # 10 features per symbol
            dtype=np.float32
        )
        
        self.reset()
    
    def _get_state(self) -> np.ndarray:
        """Get the current state of the environment."""
        state = []
        for symbol in self.symbols:
            # Get historical data for the symbol
            data = self._get_symbol_data(symbol)
            if data is not None:
                # Extract features
                features = self._extract_features(data)
                state.extend(features)
            else:
                # Pad with zeros if data is not available
                state.extend([0] * 10)
        
        return np.array(state, dtype=np.float32)
    
    def _get_symbol_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Get historical data for a symbol."""
        try:
            conn = sqlite3.connect(self.db_path)
            query = """
            SELECT date, open, high, low, close, volume
            FROM MSpricehistory
            WHERE ticker = ?
            ORDER BY date DESC
            LIMIT 100
            """
            df = pd.read_sql_query(query, conn, params=(symbol,))
            conn.close()
            return df
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return None
    
    def _extract_features(self, data: pd.DataFrame) -> List[float]:
        """Extract features from price data."""
        if data.empty:
            return [0] * 10
        
        # Calculate technical indicators
        close = data['close'].values
        volume = data['volume'].values
        
        # Simple moving averages
        sma_5 = np.mean(close[:5]) if len(close) >= 5 else close[0]
        sma_20 = np.mean(close[:20]) if len(close) >= 20 else close[0]
        
        # Volume moving average
        volume_ma = np.mean(volume[:5]) if len(volume) >= 5 else volume[0]
        
        # Price momentum
        momentum = (close[0] - close[4]) / close[4] if len(close) >= 5 else 0
        
        # Volatility
        volatility = np.std(close[:20]) if len(close) >= 20 else 0
        
        # Return features
        return [
            close[0],  # Current price
            volume[0],  # Current volume
            sma_5,
            sma_20,
            volume_ma,
            momentum,
            volatility,
            (close[0] - sma_5) / sma_5,  # Price deviation from SMA5
            (close[0] - sma_20) / sma_20,  # Price deviation from SMA20
            volume[0] / volume_ma if volume_ma > 0 else 1  # Volume ratio
        ]
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict]:
        """
        Execute one time step within the environment.
        
        Args:
            action: The action to take (0: hold, 1: buy, 2: sell)
            
        Returns:
            observation: The new state
            reward: The reward for the action
            done: Whether the episode is finished
            info: Additional information
        """
        # Get current state
        state = self._get_state()
        
        # Execute action
        reward = self._execute_action(action)
        
        # Update portfolio value
        self.portfolio_value = self._calculate_portfolio_value()
        
        # Check if episode is done
        done = self._is_done()
        
        # Additional information
        info = {
            'portfolio_value': self.portfolio_value,
            'action': action
        }
        
        return state, reward, done, info
    
    def _execute_action(self, action: int) -> float:
        """Execute the trading action and return the reward."""
        # Implement trading logic here
        # For now, return a simple reward based on portfolio value change
        old_value = self.portfolio_value
        self.portfolio_value = self._calculate_portfolio_value()
        return (self.portfolio_value - old_value) / old_value
    
    def _calculate_portfolio_value(self) -> float:
        """Calculate the current portfolio value."""
        # Implement portfolio value calculation
        # For now, return the initial balance
        return self.initial_balance
    
    def _is_done(self) -> bool:
        """Check if the episode is done."""
        # Implement episode termination conditions
        # For now, always return False
        return False
    
    def reset(self) -> np.ndarray:
        """Reset the environment to initial state."""
        self.portfolio_value = self.initial_balance
        return self._get_state()

class RLTrader:
    """
    Main class for the reinforcement learning trading system.
    """
    
    def __init__(self, db_path: str, symbols: List[str]):
        self.db_path = db_path
        self.symbols = symbols
        self.env = TradingEnvironment(db_path, symbols)
        self.model = None
    
    def train(self, total_timesteps: int = 100000):
        """Train the RL model."""
        # Create and train the model
        self.model = PPO('MlpPolicy', self.env, verbose=1)
        self.model.learn(total_timesteps=total_timesteps)
    
    def predict(self, state: np.ndarray) -> int:
        """Make a prediction for the given state."""
        if self.model is None:
            raise ValueError("Model not trained yet")
        return self.model.predict(state)[0]
    
    def save_model(self, path: str):
        """Save the trained model."""
        if self.model is None:
            raise ValueError("Model not trained yet")
        self.model.save(path)
    
    def load_model(self, path: str):
        """Load a trained model."""
        self.model = PPO.load(path)

def main():
    """Main function to run the RL trading system."""
    # Initialize the RL trader
    db_path = 'data/mstables.sqlite'
    symbols = ['AAPL', 'MSFT', 'GOOGL']  # Example symbols
    
    trader = RLTrader(db_path, symbols)
    
    # Train the model
    trader.train(total_timesteps=100000)
    
    # Save the trained model
    trader.save_model('models/rl_trading_model')

if __name__ == "__main__":
    main() 