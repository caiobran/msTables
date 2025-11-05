"""
Options Backtesting Simulation

This script simulates options strategies based on different investment styles:
- Jim Cramer's momentum-based approach
- Cathie Wood's disruptive tech focus
- Michael Burry's contrarian/value approach
- Warren Buffett's value/quality approach

Features:
- Monte Carlo simulation for 1000 scenarios
- Historical volatility analysis
- Options pricing using Black-Scholes
- Portfolio performance tracking
- Risk metrics calculation
"""

import numpy as np
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import logging
from pathlib import Path
from typing import Dict, List, Tuple
import time
from concurrent.futures import ProcessPoolExecutor
import multiprocessing

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/logs/options_backtest.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('OptionsBacktest')

class OptionsBacktester:
    def __init__(self, db_path: str, num_simulations: int = 1000):
        self.db_path = db_path
        self.num_simulations = num_simulations
        self.strategies = {
            'cramer': {
                'sectors': ['Technology', 'Consumer Cyclical', 'Communication Services'],
                'momentum_threshold': 0.05,
                'volatility_threshold': 0.3
            },
            'wood': {
                'sectors': ['Technology', 'Healthcare', 'Communication Services'],
                'growth_threshold': 0.2,
                'innovation_score': 0.7
            },
            'burry': {
                'sectors': ['Financial Services', 'Real Estate', 'Energy'],
                'value_threshold': 0.8,
                'short_interest_threshold': 0.2
            },
            'buffett': {
                'sectors': ['Consumer Defensive', 'Financial Services', 'Industrials'],
                'quality_threshold': 0.8,
                'dividend_threshold': 0.02
            }
        }
    
    def get_historical_data(self, symbol: str, lookback_days: int = 252) -> pd.DataFrame:
        """Get historical price data for a symbol from tiingo_prices."""
        try:
            conn = sqlite3.connect(self.db_path)
            query = """
            SELECT date, open, high, low, close, volume
            FROM tiingo_prices
            WHERE symbol = ?
            ORDER BY date DESC
            LIMIT ?
            """
            df = pd.read_sql_query(query, conn, params=(symbol, lookback_days))
            conn.close()
            return df
        except Exception as e:
            logger.error(f"Error fetching data for symbol {symbol}: {e}")
            return pd.DataFrame()
    
    def get_active_symbols(self, min_days: int = 252) -> List[str]:
        """Get list of active symbols in tiingo_prices with at least min_days of data."""
        try:
            conn = sqlite3.connect(self.db_path)
            query = f"""
            SELECT symbol FROM (
                SELECT symbol, COUNT(*) as cnt
                FROM tiingo_prices
                GROUP BY symbol
                HAVING cnt >= {min_days}
            )
            """
            df = pd.read_sql_query(query, conn)
            conn.close()
            return df['symbol'].tolist()
        except Exception as e:
            logger.error(f"Error fetching active symbols: {e}")
            return []
    
    def calculate_volatility(self, prices: np.ndarray, window: int = 20) -> float:
        """Calculate historical volatility."""
        returns = np.log(prices[1:] / prices[:-1])
        return np.std(returns) * np.sqrt(252)
    
    def black_scholes(self, S: float, K: float, T: float, r: float, sigma: float, option_type: str = 'call') -> float:
        """Calculate option price using Black-Scholes model."""
        d1 = (np.log(S/K) + (r + sigma**2/2)*T) / (sigma*np.sqrt(T))
        d2 = d1 - sigma*np.sqrt(T)
        
        if option_type == 'call':
            price = S*np.exp(-r*T)*self._norm_cdf(d1) - K*np.exp(-r*T)*self._norm_cdf(d2)
        else:
            price = K*np.exp(-r*T)*self._norm_cdf(-d2) - S*np.exp(-r*T)*self._norm_cdf(-d1)
        
        return price
    
    def _norm_cdf(self, x: float) -> float:
        """Calculate cumulative normal distribution."""
        return 0.5 * (1 + np.math.erf(x/np.sqrt(2)))
    
    def simulate_strategy(self, strategy: str, symbol: str) -> Dict:
        """Simulate options strategy for a given symbol."""
        try:
            hist_data = self.get_historical_data(symbol)
            if hist_data.empty:
                return {'symbol': symbol, 'strategy': strategy, 'success': False}
            
            prices = hist_data['close'].values
            volatility = self.calculate_volatility(prices)
            current_price = prices[0]
            params = self.strategies[strategy]
            
            results = []
            for _ in range(self.num_simulations):
                strike = current_price * np.random.uniform(0.8, 1.2)
                days_to_expiry = np.random.randint(30, 365)
                T = days_to_expiry / 365
                call_price = self.black_scholes(current_price, strike, T, 0.02, volatility, 'call')
                put_price = self.black_scholes(current_price, strike, T, 0.02, volatility, 'put')
                future_price = current_price * np.exp(np.random.normal(0, volatility/np.sqrt(252)) * np.sqrt(days_to_expiry))
                call_pnl = max(0, future_price - strike) - call_price
                put_pnl = max(0, strike - future_price) - put_price
                results.append({
                    'strike': strike,
                    'days_to_expiry': days_to_expiry,
                    'call_price': call_price,
                    'put_price': put_price,
                    'future_price': future_price,
                    'call_pnl': call_pnl,
                    'put_pnl': put_pnl
                })
            
            call_pnls = [r['call_pnl'] for r in results]
            put_pnls = [r['put_pnl'] for r in results]
            
            return {
                'symbol': symbol,
                'strategy': strategy,
                'success': True,
                'avg_call_pnl': np.mean(call_pnls),
                'avg_put_pnl': np.mean(put_pnls),
                'call_win_rate': np.mean([p > 0 for p in call_pnls]),
                'put_win_rate': np.mean([p > 0 for p in put_pnls]),
                'volatility': volatility
            }
        except Exception as e:
            logger.error(f"Error simulating strategy for {symbol}: {e}")
            return {'symbol': symbol, 'strategy': strategy, 'success': False}

    def run_backtest(self) -> pd.DataFrame:
        """Run backtest for only the Buffett strategy and all active symbols."""
        start_time = time.time()
        symbols = self.get_active_symbols()
        logger.info(f"Found {len(symbols)} active symbols")
        
        results = []
        strategy = 'buffett'
        
        # Process symbols in batches to avoid memory issues
        batch_size = 50
        for i in range(0, len(symbols), batch_size):
            batch_symbols = symbols[i:i + batch_size]
            with ProcessPoolExecutor(max_workers=min(multiprocessing.cpu_count(), len(batch_symbols))) as executor:
                futures = [executor.submit(self.simulate_strategy, strategy, symbol) for symbol in batch_symbols]
                for future in futures:
                    result = future.result()
                    if result['success']:
                        results.append(result)
            
            logger.info(f"Processed batch {i//batch_size + 1}/{(len(symbols) + batch_size - 1)//batch_size}")
        
        df_results = pd.DataFrame(results)
        execution_time = time.time() - start_time
        logger.info(f"Backtest completed in {execution_time:.2f} seconds")
        logger.info(f"Simulated {len(results)} scenarios")
        return df_results

def main():
    Path('data/logs').mkdir(parents=True, exist_ok=True)
    backtester = OptionsBacktester('data/mstables.sqlite')
    try:
        results = backtester.run_backtest()
        results.to_csv('data/backtest_results.csv', index=False)
        logger.info("Results saved to data/backtest_results.csv")
        print("\nBacktest Summary:")
        print(f"Total scenarios simulated: {len(results)}")
        print("\nBuffett Strategy Performance:")
        print(f"Average Call PnL: ${results['avg_call_pnl'].mean():.2f}")
        print(f"Average Put PnL: ${results['avg_put_pnl'].mean():.2f}")
        print(f"Call Win Rate: {results['call_win_rate'].mean()*100:.1f}%")
        print(f"Put Win Rate: {results['put_win_rate'].mean()*100:.1f}%")
    except Exception as e:
        logger.error(f"Error during backtest: {e}")

if __name__ == "__main__":
    main() 