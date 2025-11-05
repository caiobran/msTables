"""
Financial Ratio Calculator Module

This module provides standardized calculation of financial ratios and metrics,
with capabilities for Morningstar-style analysis and backtesting.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Union, Optional
from datetime import datetime, timedelta
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/logs/ratio_calculator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('RatioCalculator')

class RatioCalculator:
    """
    A class for calculating financial ratios and performing Morningstar-style analysis.
    """
    
    def __init__(self, db_path: str = 'data/mstables.sqlite'):
        """
        Initialize the RatioCalculator.
        
        Parameters
        ----------
        db_path : str
            Path to the SQLite database
        """
        self.db_path = db_path
        self.logger = logger
        
        # Create necessary directories
        Path('data/logs').mkdir(parents=True, exist_ok=True)
        Path('data/analysis').mkdir(parents=True, exist_ok=True)

    def calculate_liquidity_ratios(self, data: pd.DataFrame) -> Dict[str, float]:
        """Calculate liquidity measurement ratios."""
        ratios = {}
        
        try:
            # Current Ratio
            ratios['current_ratio'] = data['current_assets'] / data['current_liabilities']
            
            # Quick Ratio
            quick_assets = (data['cash'] + data['short_term_investments'] + 
                          data['accounts_receivable'])
            ratios['quick_ratio'] = quick_assets / data['current_liabilities']
            
            # Cash Ratio
            ratios['cash_ratio'] = data['cash'] / data['current_liabilities']
            
            # Days of Sales Outstanding (DSO)
            avg_receivables = (data['accounts_receivable'].shift(1) + 
                             data['accounts_receivable']) / 2
            ratios['dso'] = (avg_receivables / (data['revenue'] / 365))
            
            # Days of Inventory Outstanding (DIO)
            avg_inventory = (data['inventory'].shift(1) + data['inventory']) / 2
            ratios['dio'] = (avg_inventory / (data['cogs'] / 365))
            
            # Operating Cycle
            ratios['operating_cycle'] = ratios['dso'] + ratios['dio']
            
            # Days of Payables Outstanding (DPO)
            avg_payables = (data['accounts_payable'].shift(1) + 
                          data['accounts_payable']) / 2
            ratios['dpo'] = (avg_payables / (data['cogs'] / 365))
            
            # Cash Conversion Cycle
            ratios['cash_conversion_cycle'] = (ratios['dso'] + ratios['dio'] - 
                                             ratios['dpo'])
            
        except Exception as e:
            self.logger.error(f"Error calculating liquidity ratios: {e}")
            
        return ratios

    def calculate_profitability_ratios(self, data: pd.DataFrame) -> Dict[str, float]:
        """Calculate profitability indicator ratios."""
        ratios = {}
        
        try:
            # Gross Profit Margin
            ratios['gross_profit_margin'] = data['gross_profit'] / data['revenue']
            
            # Operating Profit Margin
            ratios['operating_profit_margin'] = data['operating_income'] / data['revenue']
            
            # Net Profit Margin
            ratios['net_profit_margin'] = data['net_income'] / data['revenue']
            
            # Return On Assets (ROA)
            avg_assets = (data['total_assets'].shift(1) + data['total_assets']) / 2
            ratios['roa'] = data['net_income'] / avg_assets
            
            # Return On Equity (ROE)
            avg_equity = (data['total_equity'].shift(1) + data['total_equity']) / 2
            ratios['roe'] = data['net_income'] / avg_equity
            
            # Return On Capital Employed (ROCE)
            avg_capital = (data['total_assets'].shift(1) + data['total_assets'] - 
                         data['current_liabilities'].shift(1) - data['current_liabilities']) / 2
            ratios['roce'] = data['ebit'] / avg_capital
            
        except Exception as e:
            self.logger.error(f"Error calculating profitability ratios: {e}")
            
        return ratios

    def calculate_valuation_ratios(self, data: pd.DataFrame) -> Dict[str, float]:
        """Calculate investment valuation ratios."""
        ratios = {}
        
        try:
            # Price to Book Value
            ratios['price_to_book'] = data['stock_price'] / data['book_value_per_share']
            
            # Price to Cash Flow
            ratios['price_to_cash_flow'] = (data['stock_price'] / 
                                          data['operating_cash_flow_per_share'])
            
            # Price to Earnings (P/E)
            ratios['pe_ratio'] = data['stock_price'] / data['eps']
            
            # Price to Sales
            ratios['price_to_sales'] = data['stock_price'] / data['revenue_per_share']
            
            # Enterprise Value to EBITDA
            ratios['ev_to_ebitda'] = data['enterprise_value'] / data['ebitda']
            
        except Exception as e:
            self.logger.error(f"Error calculating valuation ratios: {e}")
            
        return ratios

    def calculate_morningstar_style_ratios(self, data: pd.DataFrame) -> Dict[str, float]:
        """Calculate Morningstar-specific style ratios."""
        ratios = {}
        
        try:
            # Growth Rates
            ratios['revenue_growth'] = data['revenue'].pct_change(periods=4)  # Year over Year
            ratios['earnings_growth'] = data['net_income'].pct_change(periods=4)
            ratios['cash_flow_growth'] = data['operating_cash_flow'].pct_change(periods=4)
            
            # Quality Metrics
            ratios['return_on_equity'] = data['net_income'] / data['total_equity']
            ratios['return_on_assets'] = data['net_income'] / data['total_assets']
            ratios['operating_margin'] = data['operating_income'] / data['revenue']
            
            # Financial Health
            ratios['debt_to_equity'] = data['total_debt'] / data['total_equity']
            ratios['interest_coverage'] = data['ebit'] / data['interest_expense']
            ratios['current_ratio'] = data['current_assets'] / data['current_liabilities']
            
        except Exception as e:
            self.logger.error(f"Error calculating Morningstar style ratios: {e}")
            
        return ratios

    def estimate_morningstar_rating(self, ratios: Dict[str, float]) -> Dict[str, float]:
        """
        Estimate Morningstar-style ratings based on calculated ratios.
        This is a simplified model and should be used for research purposes only.
        """
        scores = {}
        
        try:
            # Growth Score (0-100)
            growth_score = (
                (ratios.get('revenue_growth', 0) * 0.4) +
                (ratios.get('earnings_growth', 0) * 0.4) +
                (ratios.get('cash_flow_growth', 0) * 0.2)
            ) * 100
            scores['growth_score'] = min(max(growth_score, 0), 100)
            
            # Quality Score (0-100)
            quality_score = (
                (ratios.get('return_on_equity', 0) * 0.3) +
                (ratios.get('return_on_assets', 0) * 0.3) +
                (ratios.get('operating_margin', 0) * 0.4)
            ) * 100
            scores['quality_score'] = min(max(quality_score, 0), 100)
            
            # Financial Health Score (0-100)
            health_score = (
                (1 / (1 + ratios.get('debt_to_equity', 0))) * 0.4 +
                (min(ratios.get('interest_coverage', 0) / 5, 1)) * 0.3 +
                (min(ratios.get('current_ratio', 0) / 2, 1)) * 0.3
            ) * 100
            scores['health_score'] = min(max(health_score, 0), 100)
            
            # Overall Score (0-100)
            scores['overall_score'] = (
                scores['growth_score'] * 0.4 +
                scores['quality_score'] * 0.4 +
                scores['health_score'] * 0.2
            )
            
        except Exception as e:
            self.logger.error(f"Error estimating Morningstar rating: {e}")
            
        return scores

    def backtest_ratios(self, 
                       data: pd.DataFrame, 
                       start_date: datetime,
                       end_date: datetime,
                       window: int = 252) -> pd.DataFrame:
        """
        Backtest ratio performance over a specified time period.
        
        Parameters
        ----------
        data : pd.DataFrame
            Historical financial data
        start_date : datetime
            Start date for backtesting
        end_date : datetime
            End date for backtesting
        window : int
            Rolling window size in days (default: 252 for trading days)
            
        Returns
        -------
        pd.DataFrame
            Backtest results with ratio performance
        """
        results = pd.DataFrame()
        
        try:
            # Filter data for date range
            mask = (data.index >= start_date) & (data.index <= end_date)
            period_data = data[mask].copy()
            
            # Calculate rolling ratios
            for i in range(window, len(period_data)):
                window_data = period_data.iloc[i-window:i]
                
                # Calculate all ratios for the window
                liquidity = self.calculate_liquidity_ratios(window_data)
                profitability = self.calculate_profitability_ratios(window_data)
                valuation = self.calculate_valuation_ratios(window_data)
                morningstar = self.calculate_morningstar_style_ratios(window_data)
                
                # Combine all ratios
                all_ratios = {**liquidity, **profitability, **valuation, **morningstar}
                
                # Calculate Morningstar-style rating
                rating = self.estimate_morningstar_rating(all_ratios)
                
                # Store results
                results = results.append({
                    'date': period_data.index[i],
                    **all_ratios,
                    **rating
                }, ignore_index=True)
                
        except Exception as e:
            self.logger.error(f"Error in backtesting: {e}")
            
        return results

    def analyze_fund_ratios(self, fund_id: str) -> Dict[str, pd.DataFrame]:
        """
        Analyze ratios for a specific fund.
        
        Parameters
        ----------
        fund_id : str
            Morningstar fund identifier
            
        Returns
        -------
        Dict[str, pd.DataFrame]
            Dictionary containing various ratio analyses
        """
        analysis = {}
        
        try:
            # Fetch fund data from database
            # This would need to be implemented based on your database structure
            
            # Calculate various ratios
            analysis['liquidity'] = pd.DataFrame(self.calculate_liquidity_ratios(data))
            analysis['profitability'] = pd.DataFrame(self.calculate_profitability_ratios(data))
            analysis['valuation'] = pd.DataFrame(self.calculate_valuation_ratios(data))
            analysis['morningstar_style'] = pd.DataFrame(self.calculate_morningstar_style_ratios(data))
            
            # Calculate Morningstar-style rating
            analysis['rating'] = pd.DataFrame(self.estimate_morningstar_rating(analysis['morningstar_style']))
            
        except Exception as e:
            self.logger.error(f"Error analyzing fund ratios: {e}")
            
        return analysis

def main():
    """Example usage of the RatioCalculator."""
    calculator = RatioCalculator()
    
    # Example: Analyze a fund
    fund_id = 'FOUSA06WRH'  # Example Morningstar fund ID
    analysis = calculator.analyze_fund_ratios(fund_id)
    
    # Example: Backtest ratios
    start_date = datetime.now() - timedelta(days=365)
    end_date = datetime.now()
    backtest_results = calculator.backtest_ratios(data, start_date, end_date)
    
    # Save results
    for name, df in analysis.items():
        df.to_csv(f'data/analysis/{fund_id}_{name}_analysis.csv')
    
    backtest_results.to_csv(f'data/analysis/{fund_id}_backtest_results.csv')

if __name__ == '__main__':
    main() 