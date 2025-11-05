"""
Reinforcement Learning Trading Environment

This module implements a trading environment for reinforcement learning,
with realistic market simulation, transaction costs, and risk management.
"""

import gym
import numpy as np
import pandas as pd
from gym import spaces
from typing import Dict, List, Tuple, Optional
import logging
from pathlib import Path
import torch
from src.models.lstm_predictor import LSTMPredictor

class TradingEnv(gym.Env):
    """
    Trading environment for reinforcement learning.
    """
    
    def __init__(self,
                 data: pd.DataFrame,
                 initial_balance: float = 100000.0,
                 transaction_fee: float = 0.001,
                 max_position: float = 1.0,
                 window_size: int = 20,
                 use_lstm: bool = True):
        """
        Initialize the trading environment.
        
        Parameters
        ----------
        data : pd.DataFrame
            Market data with features
        initial_balance : float
            Initial account balance
        transaction_fee : float
            Transaction fee as a fraction
        max_position : float
            Maximum position size as a fraction of balance
        window_size : int
            Size of observation window
        use_lstm : bool
            Whether to use LSTM for feature extraction
        """
        super().__init__()
        
        self.data = data
        self.initial_balance = initial_balance
        self.transaction_fee = transaction_fee
        self.max_position = max_position
        self.window_size = window_size
        self.use_lstm = use_lstm
        
        # Initialize LSTM if needed
        if use_lstm:
            self.lstm = LSTMPredictor(
                input_dim=data.shape[1],
                hidden_dim=64,
                num_layers=2,
                output_dim=1
            )
            # Load pre-trained weights if available
            try:
                self.lstm.load_state_dict(torch.load('data/models/best_lstm_model.pth'))
                self.lstm.eval()
            except:
                logging.warning("No pre-trained LSTM model found")
        
        # Define action space (continuous: position size from -1 to 1)
        self.action_space = spaces.Box(
            low=-1.0,
            high=1.0,
            shape=(1,),
            dtype=np.float32
        )
        
        # Define observation space
        self.observation_space = spaces.Dict({
            'market_data': spaces.Box(
                low=-np.inf,
                high=np.inf,
                shape=(window_size, data.shape[1]),
                dtype=np.float32
            ),
            'position': spaces.Box(
                low=-1.0,
                high=1.0,
                shape=(1,),
                dtype=np.float32
            ),
            'balance': spaces.Box(
                low=0.0,
                high=np.inf,
                shape=(1,),
                dtype=np.float32
            )
        })
        
        # Initialize state
        self.reset()
        
    def reset(self) -> Dict:
        """
        Reset the environment to initial state.
        
        Returns
        -------
        Dict
            Initial observation
        """
        self.current_step = self.window_size
        self.balance = self.initial_balance
        self.position = 0.0
        self.trades = []
        self.returns = []
        
        return self._get_observation()
        
    def step(self, action: np.ndarray) -> Tuple[Dict, float, bool, Dict]:
        """
        Take a step in the environment.
        
        Parameters
        ----------
        action : np.ndarray
            Action to take (position size)
            
        Returns
        -------
        Tuple[Dict, float, bool, Dict]
            Observation, reward, done, info
        """
        # Clip action to valid range
        action = np.clip(action, -1.0, 1.0)
        
        # Calculate new position
        new_position = action[0] * self.max_position
        
        # Calculate transaction cost
        position_change = abs(new_position - self.position)
        transaction_cost = position_change * self.balance * self.transaction_fee
        
        # Update position and balance
        self.position = new_position
        self.balance -= transaction_cost
        
        # Get current price and calculate returns
        current_price = self.data.iloc[self.current_step]['Close']
        next_price = self.data.iloc[self.current_step + 1]['Close']
        price_return = (next_price - current_price) / current_price
        
        # Calculate portfolio return
        portfolio_return = self.position * price_return
        self.balance *= (1 + portfolio_return)
        
        # Record trade
        self.trades.append({
            'step': self.current_step,
            'position': self.position,
            'price': current_price,
            'return': portfolio_return
        })
        
        # Calculate reward
        reward = self._calculate_reward(portfolio_return, transaction_cost)
        
        # Move to next step
        self.current_step += 1
        
        # Check if episode is done
        done = self.current_step >= len(self.data) - 1
        
        # Get observation
        observation = self._get_observation()
        
        # Additional info
        info = {
            'balance': self.balance,
            'position': self.position,
            'transaction_cost': transaction_cost,
            'portfolio_return': portfolio_return
        }
        
        return observation, reward, done, info
        
    def _get_observation(self) -> Dict:
        """
        Get current observation.
        
        Returns
        -------
        Dict
            Current observation
        """
        # Get market data window
        market_data = self.data.iloc[
            self.current_step - self.window_size:self.current_step
        ].values
        
        # Use LSTM for feature extraction if enabled
        if self.use_lstm:
            with torch.no_grad():
                market_data = self.lstm(
                    torch.FloatTensor(market_data).unsqueeze(0)
                ).squeeze().numpy()
        
        return {
            'market_data': market_data,
            'position': np.array([self.position]),
            'balance': np.array([self.balance])
        }
        
    def _calculate_reward(self,
                        portfolio_return: float,
                        transaction_cost: float) -> float:
        """
        Calculate reward for the current step.
        
        Parameters
        ----------
        portfolio_return : float
            Portfolio return for the step
        transaction_cost : float
            Transaction cost for the step
            
        Returns
        -------
        float
            Reward value
        """
        # Base reward is the portfolio return
        reward = portfolio_return
        
        # Penalize transaction costs
        reward -= transaction_cost / self.balance
        
        # Penalize excessive trading
        if len(self.trades) > 1:
            last_trade = self.trades[-2]
            if abs(self.position - last_trade['position']) > 0.5:
                reward -= 0.001
        
        # Penalize holding large positions
        reward -= 0.0001 * abs(self.position)
        
        return reward
        
    def render(self, mode='human'):
        """
        Render the current state of the environment.
        
        Parameters
        ----------
        mode : str
            Rendering mode
        """
        if mode == 'human':
            print(f"Step: {self.current_step}")
            print(f"Balance: ${self.balance:.2f}")
            print(f"Position: {self.position:.2f}")
            print(f"Current Price: ${self.data.iloc[self.current_step]['Close']:.2f}")
            
    def get_metrics(self) -> Dict:
        """
        Calculate trading performance metrics.
        
        Returns
        -------
        Dict
            Performance metrics
        """
        if not self.trades:
            return {}
            
        returns = pd.Series([t['return'] for t in self.trades])
        
        metrics = {
            'total_return': (self.balance - self.initial_balance) / self.initial_balance,
            'sharpe_ratio': returns.mean() / returns.std() * np.sqrt(252),
            'max_drawdown': (returns.cumsum() - returns.cumsum().cummax()).min(),
            'win_rate': (returns > 0).mean(),
            'num_trades': len(self.trades),
            'avg_trade_return': returns.mean(),
            'volatility': returns.std() * np.sqrt(252)
        }
        
        return metrics

def main():
    """Example usage of the trading environment."""
    # Load market data
    data = pd.DataFrame()  # Your market data here
    
    # Create environment
    env = TradingEnv(
        data=data,
        initial_balance=100000.0,
        transaction_fee=0.001,
        max_position=1.0,
        window_size=20,
        use_lstm=True
    )
    
    # Run a simple random policy
    obs = env.reset()
    done = False
    
    while not done:
        action = env.action_space.sample()
        obs, reward, done, info = env.step(action)
        env.render()
        
    # Print final metrics
    metrics = env.get_metrics()
    print("\nTrading Performance Metrics:")
    for metric, value in metrics.items():
        print(f"{metric}: {value:.4f}")

if __name__ == "__main__":
    main() 