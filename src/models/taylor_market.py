"""
Taylor Market Simulation

This module implements a market simulation framework using Taylor series expansion
to model price dynamics. It captures higher-order moments and non-linear effects
in market behavior, including:
- Higher-order price derivatives
- Non-linear price impact
- Volatility clustering
- Market regime transitions
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Union
from datetime import datetime, timedelta
import logging
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import norm, levy_stable
import json

class TaylorMarketSimulator:
    """
    Market simulator using Taylor series expansion for price dynamics.
    """
    def __init__(self,
                 initial_price: float = 100.0,
                 initial_volume: float = 1000000.0,
                 order: int = 4,
                 seed: Optional[int] = None):
        """
        Initialize the Taylor market simulator.
        
        Parameters
        ----------
        initial_price : float
            Initial price level
        initial_volume : float
            Initial trading volume
        order : int
            Order of Taylor series expansion
        seed : Optional[int]
            Random seed for reproducibility
        """
        self.initial_price = initial_price
        self.initial_volume = initial_volume
        self.order = order
        self.rng = np.random.RandomState(seed)
        
        # Create necessary directories
        Path('data/simulations').mkdir(parents=True, exist_ok=True)
        Path('data/plots').mkdir(parents=True, exist_ok=True)
        
    def compute_derivatives(self,
                          prices: np.ndarray,
                          dt: float = 1/252) -> List[np.ndarray]:
        """
        Compute price derivatives up to specified order.
        
        Parameters
        ----------
        prices : np.ndarray
            Price series
        dt : float
            Time step size
            
        Returns
        -------
        List[np.ndarray]
            List of derivatives [price, velocity, acceleration, jerk, ...]
        """
        derivatives = [prices]
        
        for i in range(1, self.order + 1):
            # Compute i-th derivative using finite differences
            deriv = np.zeros_like(prices)
            deriv[1:] = np.diff(derivatives[-1]) / dt
            derivatives.append(deriv)
            
        return derivatives
        
    def simulate_price_path(self,
                          n_steps: int,
                          dt: float = 1/252,
                          volatility: float = 0.01,
                          mean_reversion: float = 0.1,
                          jump_probability: float = 0.05,
                          jump_size: float = 0.02) -> pd.Series:
        """
        Simulate price path using Taylor series expansion.
        
        Parameters
        ----------
        n_steps : int
            Number of time steps
        dt : float
            Time step size
        volatility : float
            Base volatility
        mean_reversion : float
            Mean reversion strength
        jump_probability : float
            Probability of price jumps
        jump_size : float
            Size of price jumps
            
        Returns
        -------
        pd.Series
            Simulated price path
        """
        # Initialize arrays
        prices = np.zeros(n_steps)
        prices[0] = self.initial_price
        
        # Generate random components
        normal_shocks = self.rng.normal(0, 1, n_steps)
        jump_shocks = self.rng.binomial(1, jump_probability, n_steps)
        
        # Simulate price path
        for t in range(1, n_steps):
            # Get current derivatives
            derivatives = self.compute_derivatives(prices[:t+1], dt)
            
            # Taylor series expansion
            price_change = 0
            for i, deriv in enumerate(derivatives[1:], 1):
                price_change += deriv[-1] * (dt ** i) / np.math.factorial(i)
            
            # Add mean reversion
            mean_reversion_term = mean_reversion * (self.initial_price - prices[t-1]) * dt
            
            # Add random component
            random_term = volatility * np.sqrt(dt) * normal_shocks[t]
            
            # Add jump component
            jump_term = jump_size * jump_shocks[t]
            
            # Update price
            prices[t] = prices[t-1] + price_change + mean_reversion_term + random_term + jump_term
            
        return pd.Series(prices)
        
    def simulate_volume(self,
                       prices: pd.Series,
                       base_volume: float,
                       volume_volatility: float = 0.2) -> pd.Series:
        """
        Simulate trading volume with non-linear price impact.
        
        Parameters
        ----------
        prices : pd.Series
            Price series
        base_volume : float
            Base trading volume
        volume_volatility : float
            Volume volatility
            
        Returns
        -------
        pd.Series
            Simulated volume series
        """
        # Calculate price changes and their derivatives
        returns = prices.pct_change()
        returns_deriv = returns.diff()
        
        # Generate volume with non-linear price impact
        volume = base_volume * (1 + volume_volatility * self.rng.normal(0, 1, len(prices)))
        
        # Higher-order volume impact
        volume *= (1 + abs(returns) + 0.5 * abs(returns_deriv))
        
        return pd.Series(volume, index=prices.index)
        
    def add_market_impact(self,
                         prices: pd.Series,
                         volume: pd.Series,
                         impact_factor: float = 0.0001) -> pd.Series:
        """
        Add non-linear market impact to prices.
        
        Parameters
        ----------
        prices : pd.Series
            Price series
        volume : pd.Series
            Volume series
        impact_factor : float
            Market impact factor
            
        Returns
        -------
        pd.Series
            Prices with market impact
        """
        # Calculate non-linear market impact
        relative_volume = volume / volume.mean()
        impact = impact_factor * (relative_volume + 0.5 * relative_volume ** 2)
        
        # Apply impact
        impacted_prices = prices * (1 + impact)
        
        return impacted_prices
        
    def simulate_market_data(self,
                            start_date: datetime,
                            end_date: datetime,
                            freq: str = 'D',
                            volatility: float = 0.01,
                            mean_reversion: float = 0.1) -> pd.DataFrame:
        """
        Simulate complete market data.
        
        Parameters
        ----------
        start_date : datetime
            Start date
        end_date : datetime
            End date
        freq : str
            Data frequency
        volatility : float
            Base volatility
        mean_reversion : float
            Mean reversion strength
            
        Returns
        -------
        pd.DataFrame
            Simulated market data
        """
        # Generate date range
        dates = pd.date_range(start=start_date, end=end_date, freq=freq)
        n_steps = len(dates)
        
        # Simulate price path
        prices = self.simulate_price_path(
            n_steps=n_steps,
            volatility=volatility,
            mean_reversion=mean_reversion
        )
        
        # Simulate volume
        volume = self.simulate_volume(prices, self.initial_volume)
        
        # Add market impact
        impacted_prices = self.add_market_impact(prices, volume)
        
        # Create DataFrame
        data = pd.DataFrame({
            'Open': impacted_prices,
            'High': impacted_prices * (1 + abs(self.rng.normal(0, 0.001, n_steps))),
            'Low': impacted_prices * (1 - abs(self.rng.normal(0, 0.001, n_steps))),
            'Close': impacted_prices,
            'Volume': volume
        }, index=dates)
        
        return data
        
    def add_stress_scenario(self,
                           data: pd.DataFrame,
                           scenario_type: str,
                           start_date: datetime,
                           duration: int = 5) -> pd.DataFrame:
        """
        Add stress scenario to market data.
        
        Parameters
        ----------
        data : pd.DataFrame
            Market data
        scenario_type : str
            Type of stress scenario
        start_date : datetime
            Start date of scenario
        duration : int
            Duration in days
            
        Returns
        -------
        pd.DataFrame
            Market data with stress scenario
        """
        # Get scenario dates
        end_date = start_date + timedelta(days=duration)
        mask = (data.index >= start_date) & (data.index <= end_date)
        
        # Apply scenario
        if scenario_type == 'flash_crash':
            # Sudden price drop with higher-order effects
            data.loc[mask, 'Close'] *= (1 - 0.1 - 0.02 * np.arange(sum(mask)))
            data.loc[mask, 'Volume'] *= (3 + 0.5 * np.arange(sum(mask)))
        elif scenario_type == 'market_shock':
            # Gradual price decline with acceleration
            for i, idx in enumerate(data[mask].index):
                data.loc[idx, 'Close'] *= (1 - 0.02 * (i + 1) - 0.001 * (i + 1) ** 2)
                data.loc[idx, 'Volume'] *= (2 + 0.1 * i)
        elif scenario_type == 'volatility_spike':
            # Increased volatility with clustering
            volatility = 0.03 * (1 + 0.1 * np.arange(sum(mask)))
            data.loc[mask, 'Close'] *= (1 + self.rng.normal(0, volatility, sum(mask)))
            data.loc[mask, 'Volume'] *= (2.5 + 0.2 * np.arange(sum(mask)))
        elif scenario_type == 'liquidity_crisis':
            # Reduced liquidity with feedback
            for i, idx in enumerate(data[mask].index):
                data.loc[idx, 'Close'] *= (1 + self.rng.normal(0, 0.02 * (1 + 0.1 * i), 1))
                data.loc[idx, 'Volume'] *= (0.5 - 0.05 * i)
            
        # Update High/Low
        data.loc[mask, 'High'] = data.loc[mask, ['Open', 'Close']].max(axis=1)
        data.loc[mask, 'Low'] = data.loc[mask, ['Open', 'Close']].min(axis=1)
        
        return data
        
    def plot_simulation(self,
                       data: pd.DataFrame,
                       title: str = 'Taylor Market Simulation',
                       save_path: Optional[str] = None):
        """
        Plot simulation results.
        
        Parameters
        ----------
        data : pd.DataFrame
            Market data
        title : str
            Plot title
        save_path : Optional[str]
            Path to save plot
        """
        # Create figure with subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [3, 1]})
        
        # Plot prices
        ax1.plot(data.index, data['Close'], label='Close Price')
        ax1.set_title(title)
        ax1.set_ylabel('Price')
        ax1.grid(True)
        ax1.legend()
        
        # Plot volume
        ax2.bar(data.index, data['Volume'], label='Volume', alpha=0.5)
        ax2.set_ylabel('Volume')
        ax2.set_xlabel('Date')
        ax2.grid(True)
        ax2.legend()
        
        # Save plot
        if save_path:
            plt.savefig(save_path)
        plt.close()
        
    def save_simulation(self,
                       data: pd.DataFrame,
                       filename: str):
        """
        Save simulation results.
        
        Parameters
        ----------
        data : pd.DataFrame
            Market data
        filename : str
            Output filename
        """
        # Save to CSV
        data.to_csv(f'data/simulations/{filename}.csv')
        
        # Save metadata
        metadata = {
            'initial_price': self.initial_price,
            'initial_volume': self.initial_volume,
            'taylor_order': self.order,
            'start_date': data.index[0].strftime('%Y-%m-%d'),
            'end_date': data.index[-1].strftime('%Y-%m-%d'),
            'num_points': len(data)
        }
        
        with open(f'data/simulations/{filename}_metadata.json', 'w') as f:
            json.dump(metadata, f, indent=4)

def main():
    """Example usage of the Taylor market simulator."""
    # Create simulator
    simulator = TaylorMarketSimulator(
        initial_price=100.0,
        initial_volume=1000000.0,
        order=4,
        seed=42
    )
    
    # Simulate market data
    data = simulator.simulate_market_data(
        start_date=datetime(2020, 1, 1),
        end_date=datetime(2020, 12, 31),
        volatility=0.01,
        mean_reversion=0.1
    )
    
    # Add stress scenario
    data = simulator.add_stress_scenario(
        data=data,
        scenario_type='flash_crash',
        start_date=datetime(2020, 6, 1)
    )
    
    # Plot results
    simulator.plot_simulation(
        data=data,
        title='Taylor Market Simulation',
        save_path='data/plots/taylor_simulation.png'
    )
    
    # Save results
    simulator.save_simulation(data, 'taylor_market')

if __name__ == "__main__":
    main() 