"""
BHAG Market Simulation

This module implements a comprehensive market simulation framework for testing
trading strategies under various market conditions, including:
- Different market regimes (bull, bear, sideways, volatile)
- Stress scenarios (flash crashes, market shocks)
- Realistic price dynamics with multiple factors
- Market microstructure effects
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
import yfinance as yf
import json

class MarketRegime:
    """Market regime parameters."""
    def __init__(self,
                 name: str,
                 drift: float,
                 volatility: float,
                 mean_reversion: float,
                 jump_probability: float,
                 jump_size: float):
        self.name = name
        self.drift = drift
        self.volatility = volatility
        self.mean_reversion = mean_reversion
        self.jump_probability = jump_probability
        self.jump_size = jump_size

class MarketRegimes:
    """Predefined market regimes."""
    BULL = MarketRegime(
        name='bull',
        drift=0.0005,  # Positive drift
        volatility=0.01,
        mean_reversion=0.1,
        jump_probability=0.05,
        jump_size=0.02
    )
    
    BEAR = MarketRegime(
        name='bear',
        drift=-0.0005,  # Negative drift
        volatility=0.015,
        mean_reversion=0.15,
        jump_probability=0.08,
        jump_size=-0.02
    )
    
    SIDEWAYS = MarketRegime(
        name='sideways',
        drift=0.0,
        volatility=0.008,
        mean_reversion=0.2,
        jump_probability=0.03,
        jump_size=0.01
    )
    
    VOLATILE = MarketRegime(
        name='volatile',
        drift=0.0,
        volatility=0.025,
        mean_reversion=0.05,
        jump_probability=0.1,
        jump_size=0.03
    )

class MarketSimulator:
    """
    Advanced market simulator with multiple regimes and realistic dynamics.
    """
    def __init__(self,
                 initial_price: float = 100.0,
                 initial_volume: float = 1000000.0,
                 seed: Optional[int] = None):
        """
        Initialize the market simulator.
        
        Parameters
        ----------
        initial_price : float
            Initial price level
        initial_volume : float
            Initial trading volume
        seed : Optional[int]
            Random seed for reproducibility
        """
        self.initial_price = initial_price
        self.initial_volume = initial_volume
        self.rng = np.random.RandomState(seed)
        
        # Create necessary directories
        Path('data/simulations').mkdir(parents=True, exist_ok=True)
        Path('data/plots').mkdir(parents=True, exist_ok=True)
        
    def simulate_price_path(self,
                          regime: MarketRegime,
                          n_steps: int,
                          dt: float = 1/252) -> pd.Series:
        """
        Simulate price path using regime parameters.
        
        Parameters
        ----------
        regime : MarketRegime
            Market regime parameters
        n_steps : int
            Number of time steps
        dt : float
            Time step size
        
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
        jump_shocks = self.rng.binomial(1, regime.jump_probability, n_steps)
        
        # Simulate price path
        for t in range(1, n_steps):
            # Mean reversion component
            mean_reversion = regime.mean_reversion * (self.initial_price - prices[t-1])
            
            # Random walk component
            random_walk = regime.drift * dt + regime.volatility * np.sqrt(dt) * normal_shocks[t]
            
            # Jump component
            jump = regime.jump_size * jump_shocks[t]
            
            # Update price
            prices[t] = prices[t-1] * (1 + mean_reversion + random_walk + jump)
            
        return pd.Series(prices)
        
    def simulate_volume(self,
                       prices: pd.Series,
                       base_volume: float,
                       volume_volatility: float = 0.2) -> pd.Series:
        """
        Simulate trading volume with price impact.
        
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
        # Calculate price changes
        returns = prices.pct_change()
        
        # Generate volume with price impact
        volume = base_volume * (1 + volume_volatility * self.rng.normal(0, 1, len(prices)))
        volume *= (1 + abs(returns))  # Higher volume on larger price moves
        
        return pd.Series(volume, index=prices.index)
        
    def add_market_impact(self,
                         prices: pd.Series,
                         volume: pd.Series,
                         impact_factor: float = 0.0001) -> pd.Series:
        """
        Add market impact to prices.
        
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
        # Calculate market impact
        impact = impact_factor * volume / volume.mean()
        
        # Apply impact
        impacted_prices = prices * (1 + impact)
        
        return impacted_prices
        
    def add_microstructure_noise(self,
                                prices: pd.Series,
                                noise_level: float = 0.0001) -> pd.Series:
        """
        Add market microstructure noise.
        
        Parameters
        ----------
        prices : pd.Series
            Price series
        noise_level : float
            Noise level
            
        Returns
        -------
        pd.Series
            Prices with microstructure noise
        """
        # Generate noise
        noise = self.rng.normal(0, noise_level, len(prices))
        
        # Apply noise
        noisy_prices = prices * (1 + noise)
        
        return noisy_prices
        
    def simulate_market_data(self,
                            regime: MarketRegime,
                            start_date: datetime,
                            end_date: datetime,
                            freq: str = 'D') -> pd.DataFrame:
        """
        Simulate complete market data.
        
        Parameters
        ----------
        regime : MarketRegime
            Market regime parameters
        start_date : datetime
            Start date
        end_date : datetime
            End date
        freq : str
            Data frequency
            
        Returns
        -------
        pd.DataFrame
            Simulated market data
        """
        # Generate date range
        dates = pd.date_range(start=start_date, end=end_date, freq=freq)
        n_steps = len(dates)
        
        # Simulate price path
        prices = self.simulate_price_path(regime, n_steps)
        
        # Simulate volume
        volume = self.simulate_volume(prices, self.initial_volume)
        
        # Add market impact
        impacted_prices = self.add_market_impact(prices, volume)
        
        # Add microstructure noise
        final_prices = self.add_microstructure_noise(impacted_prices)
        
        # Create DataFrame
        data = pd.DataFrame({
            'Open': final_prices,
            'High': final_prices * (1 + abs(self.rng.normal(0, 0.001, n_steps))),
            'Low': final_prices * (1 - abs(self.rng.normal(0, 0.001, n_steps))),
            'Close': final_prices,
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
            # Sudden price drop
            data.loc[mask, 'Close'] *= (1 - 0.1)  # 10% drop
            data.loc[mask, 'Volume'] *= 3  # Increased volume
        elif scenario_type == 'market_shock':
            # Gradual price decline
            for i, idx in enumerate(data[mask].index):
                data.loc[idx, 'Close'] *= (1 - 0.02 * (i + 1))  # 2% drop per day
                data.loc[idx, 'Volume'] *= 2
        elif scenario_type == 'volatility_spike':
            # Increased volatility
            data.loc[mask, 'Close'] *= (1 + self.rng.normal(0, 0.03, sum(mask)))
            data.loc[mask, 'Volume'] *= 2.5
        elif scenario_type == 'liquidity_crisis':
            # Reduced liquidity
            data.loc[mask, 'Close'] *= (1 + self.rng.normal(0, 0.02, sum(mask)))
            data.loc[mask, 'Volume'] *= 0.5  # Reduced volume
            
        # Update High/Low
        data.loc[mask, 'High'] = data.loc[mask, ['Open', 'Close']].max(axis=1)
        data.loc[mask, 'Low'] = data.loc[mask, ['Open', 'Close']].min(axis=1)
        
        return data
        
    def plot_simulation(self,
                       data: pd.DataFrame,
                       title: str = 'Market Simulation',
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
            'start_date': data.index[0].strftime('%Y-%m-%d'),
            'end_date': data.index[-1].strftime('%Y-%m-%d'),
            'num_points': len(data)
        }
        
        with open(f'data/simulations/{filename}_metadata.json', 'w') as f:
            json.dump(metadata, f, indent=4)

def main():
    """Example usage of the market simulator."""
    # Create simulator
    simulator = MarketSimulator(
        initial_price=100.0,
        initial_volume=1000000.0,
        seed=42
    )
    
    # Simulate different market regimes
    regimes = [
        (MarketRegimes.BULL, 'bull_market'),
        (MarketRegimes.BEAR, 'bear_market'),
        (MarketRegimes.SIDEWAYS, 'sideways_market'),
        (MarketRegimes.VOLATILE, 'volatile_market')
    ]
    
    for regime, name in regimes:
        # Simulate market data
        data = simulator.simulate_market_data(
            regime=regime,
            start_date=datetime(2020, 1, 1),
            end_date=datetime(2020, 12, 31)
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
            title=f'{name.title()} Simulation',
            save_path=f'data/plots/{name}_simulation.png'
        )
        
        # Save results
        simulator.save_simulation(data, name)

if __name__ == "__main__":
    main() 