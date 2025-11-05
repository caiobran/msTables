"""
Script to run regime-aware backtest with real data.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sqlite3
from pathlib import Path
import logging
from typing import Dict, List, Tuple
import sys
import os
import scipy.stats as stats

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.models.backtesting.regime_aware_backtester import RegimeAwareBacktester

def load_asset_data(db_path: str, symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """
    Load asset data from database.
    
    Parameters
    ----------
    db_path : str
        Path to database
    symbol : str
        Asset symbol
    start_date : datetime
        Start date
    end_date : datetime
        End date
        
    Returns
    -------
    pd.DataFrame
        Asset data
    """
    conn = sqlite3.connect(db_path)
    
    # Format dates to match database format
    start_str = start_date.strftime('%Y-%m-%d %H:%M:%S')
    end_str = end_date.strftime('%Y-%m-%d %H:%M:%S')
    
    # Try tiingo_prices first
    query = f"""
    SELECT date, open, high, low, close, volume
    FROM tiingo_prices
    WHERE symbol = '{symbol}'
    AND date BETWEEN '{start_str}' AND '{end_str}'
    ORDER BY date
    """
    
    df = pd.read_sql_query(query, conn)
    
    if df.empty:
        # Try metal_prices with correct schema
        query = f"""
        SELECT timestamp as date, price as close
        FROM metal_prices
        WHERE symbol = '{symbol}'
        AND timestamp BETWEEN '{start_str}' AND '{end_str}'
        ORDER BY timestamp
        """
        df = pd.read_sql_query(query, conn)
        
        # Add required columns for metal prices
        if not df.empty:
            df['open'] = df['close']
            df['high'] = df['close']
            df['low'] = df['close']
            df['volume'] = 0  # No volume data for metals
    
    conn.close()
    
    if df.empty:
        raise ValueError(f"No data found for {symbol}")
        
    # Convert date column to datetime, handling both formats
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    
    return df

def get_top_metals(db_path: str, start_date: datetime, end_date: datetime, n: int = 5) -> List[str]:
    """
    Get top N metals by data availability.
    
    Parameters
    ----------
    db_path : str
        Path to database
    start_date : datetime
        Start date
    end_date : datetime
        End date
    n : int
        Number of metals to return
        
    Returns
    -------
    List[str]
        Top N metal symbols
    """
    conn = sqlite3.connect(db_path)
    
    query = f"""
    SELECT symbol, COUNT(*) as count
    FROM metal_prices
    WHERE timestamp BETWEEN '{start_date.strftime('%Y-%m-%d')}' AND '{end_date.strftime('%Y-%m-%d')}'
    GROUP BY symbol
    ORDER BY count DESC
    LIMIT {n}
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    return df['symbol'].tolist()

def get_high_mover_stocks(db_path: str, start_date: datetime, end_date: datetime, n: int = 10) -> List[str]:
    """
    Get top N stocks by volatility (calculated in pandas).
    """
    conn = sqlite3.connect(db_path)
    query = f"""
    SELECT symbol, date, close
    FROM tiingo_prices
    WHERE date BETWEEN '{start_date.strftime('%Y-%m-%d')}' AND '{end_date.strftime('%Y-%m-%d')}'
    ORDER BY symbol, date
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    if df.empty:
        return []
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['symbol', 'date'])
    # Calculate daily returns
    df['return'] = df.groupby('symbol')['close'].pct_change()
    # Calculate volatility for each symbol
    vol = df.groupby('symbol')['return'].std().sort_values(ascending=False)
    return vol.head(n).index.tolist()

def get_tariff_sensitive_bonds(db_path: str, start_date: datetime, end_date: datetime) -> List[str]:
    """
    Get bonds that are sensitive to tariff changes.
    
    Parameters
    ----------
    db_path : str
        Path to database
    start_date : datetime
        Start date
    end_date : datetime
        End date
        
    Returns
    -------
    List[str]
        Bond symbols
    """
    # Common bond ETFs that are sensitive to trade policy
    return ['TLT', 'IEF', 'SHY', 'AGG', 'BND']

def get_cramer_stocks_and_benchmarks():
    """Return lists of tickers for Cramer-style stocks, lithium, gold, and bonds."""
    # Using stocks that have good data coverage in our database
    stocks = [
        'AAPL', 'MSFT', 'JPM', 'DIS', 'NFLX',  # Original picks that exist in DB
        'A', 'AAL', 'AAP', 'ABBV', 'ABC'  # Additional stocks with good coverage
    ]
    etfs = ['GLD']  # Gold ETF
    bonds = ['TLT', 'IEF']  # Treasury ETFs
    return stocks, etfs, bonds

def calculate_alpha_sharpe_confidence(asset_returns, benchmark_returns):
    # Align lengths
    min_len = min(len(asset_returns), len(benchmark_returns))
    asset_returns = asset_returns[-min_len:]
    benchmark_returns = benchmark_returns[-min_len:]
    # Calculate excess returns
    excess = np.array(asset_returns) - np.array(benchmark_returns)
    alpha = np.mean(excess)
    sharpe = np.mean(asset_returns) / (np.std(asset_returns) + 1e-8) * np.sqrt(252)
    # 95% confidence interval for alpha (t-distribution)
    n = len(excess)
    se = np.std(excess, ddof=1) / np.sqrt(n)
    t_crit = stats.t.ppf(0.975, df=n-1) if n > 1 else 0
    ci_low = alpha - t_crit * se
    ci_high = alpha + t_crit * se
    return alpha, sharpe, (ci_low, ci_high)

def create_data_not_available_table(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS data_not_available (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            last_checked TEXT,
            num_attempts INTEGER DEFAULT 0,
            reason TEXT
        );
    """)
    conn.commit()
    conn.close()

def log_data_not_available(db_path, symbol, start_date, end_date, reason):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO data_not_available (symbol, start_date, end_date, last_checked, num_attempts, reason)
        VALUES (?, ?, ?, datetime('now'), 1, ?)
    """, (symbol, str(start_date), str(end_date), reason))
    conn.commit()
    conn.close()

def main():
    """Run regime-aware backtest with real data."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # Parameters
    db_path = 'data/mstables.sqlite'
    start_date = datetime(2017, 4, 3, 13, 30, 0)  # Start of available data
    end_date = datetime(2017, 8, 31, 20, 0, 0)   # End of available data
    
    # Create the missing data table
    create_data_not_available_table(db_path)
    
    # Create backtester
    backtester = RegimeAwareBacktester(
        initial_capital=1000000.0,
        max_position_size=0.1,
        max_drawdown=0.15,
        risk_reward_ratio=3.0
    )
    
    # Add regime events
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
    
    # Load assets
    stocks, etfs, bonds = get_cramer_stocks_and_benchmarks()
    all_tickers = stocks + etfs + bonds
    asset_types = {t: 'stock' for t in stocks}
    asset_types.update({t: 'etf' for t in etfs})
    asset_types.update({t: 'bond' for t in bonds})
    logger.info("Loading selected assets...")
    loaded_assets = []
    for symbol in all_tickers:
        try:
            data = load_asset_data(db_path, symbol, start_date, end_date)
            backtester.add_asset(symbol, asset_types[symbol], data, regime_sensitivity=0.7)
            loaded_assets.append(symbol)
            logger.info(f"Added asset: {symbol}")
        except Exception as e:
            logger.error(f"Error loading {symbol}: {e}")
            log_data_not_available(db_path, symbol, start_date, end_date, str(e))
    
    # Run backtest
    logger.info("Running backtest...")
    metrics = backtester.run_backtest(start_date, end_date)
    
    # Collect daily returns for each asset
    asset_returns = {}
    for symbol in loaded_assets:
        df = backtester.assets[symbol].data
        asset_returns[symbol] = df['close'].pct_change().dropna().values
    
    # Use SPY as benchmark if available, else use average of all assets
    benchmark = 'SPY' if 'SPY' in asset_returns else None
    if not benchmark:
        # Use average return of all assets as benchmark
        all_returns = np.vstack([r for r in asset_returns.values() if len(r) > 0])
        benchmark_returns = np.nanmean(all_returns, axis=0)
    else:
        benchmark_returns = asset_returns[benchmark]
    
    # Calculate alpha, Sharpe, confidence for each asset
    summary = []
    for symbol in loaded_assets:
        r = asset_returns[symbol]
        if len(r) < 10:
            continue
        alpha, sharpe, (ci_low, ci_high) = calculate_alpha_sharpe_confidence(r, benchmark_returns)
        summary.append({
            'symbol': symbol,
            'alpha': alpha,
            'sharpe': sharpe,
            'ci_low': ci_low,
            'ci_high': ci_high
        })
    
    # Output summary table
    summary_df = pd.DataFrame(summary)
    print("\nSummary Table (alpha, Sharpe, 95% CI):")
    print(summary_df.sort_values('alpha'))
    
    # Save summary to CSV
    summary_df.to_csv('backtest_summary.csv', index=False)
    
    # Plot results
    logger.info("Plotting results...")
    backtester.plot_results(save_path='backtest_results.png')
    
    # Save results
    logger.info("Saving results...")
    backtester.save_results('backtest_results.json')
    
    # Print metrics
    logger.info("\nBacktest Results:")
    for metric, value in metrics.items():
        logger.info(f"{metric}: {value:.4f}")

if __name__ == "__main__":
    main() 