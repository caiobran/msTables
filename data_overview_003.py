#!/usr/bin/env python
# coding: utf-8

"""
Financial Data Analysis Script
This script provides functionality to analyze financial data stored in a SQLite database
combining data from multiple sources including Morningstar (historical), WSJ, etc.
"""

import pandas as pd
import numpy as np
import sqlite3
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

# Set the style for better-looking plots
plt.style.use('seaborn-v0_8')
sns.set_theme()

class DataFrames():
    db_file = 'data/mstables.sqlite'
    MS_CUTOFF_DATE = '2022-03-15'

    def __init__(self, file=db_file):
        print(f'Creating initial DataFrames objects from file {file}...')
        self.conn = sqlite3.connect(file)
        
        # Check which tables have data
        self.tables_with_data = {}
        for table in ['master_symbols', 'wsj_data', 'morningstar_valuation', 
                     'morningstar_financial_health', 'morningstar_profitability',
                     'morningstar_efficiency', 'morningstar_growth', 'morningstar_cash_flow']:
            count = pd.read_sql(f'SELECT COUNT(*) as count FROM {table}', self.conn).iloc[0]['count']
            self.tables_with_data[table] = count > 0
            print(f"{table}: {'Has data' if count > 0 else 'No data'} ({count} records)")

        # Load tables that have data
        self.master = pd.read_sql('SELECT * FROM master_symbols', self.conn) if self.tables_with_data['master_symbols'] else pd.DataFrame()
        self.wsj_data = pd.read_sql('SELECT * FROM wsj_data', self.conn) if self.tables_with_data['wsj_data'] else pd.DataFrame()
        self.ms_valuation = pd.read_sql('SELECT * FROM morningstar_valuation', self.conn) if self.tables_with_data['morningstar_valuation'] else pd.DataFrame()
        self.ms_financial_health = pd.read_sql('SELECT * FROM morningstar_financial_health', self.conn) if self.tables_with_data['morningstar_financial_health'] else pd.DataFrame()
        self.ms_profitability = pd.read_sql('SELECT * FROM morningstar_profitability', self.conn) if self.tables_with_data['morningstar_profitability'] else pd.DataFrame()
        self.ms_efficiency = pd.read_sql('SELECT * FROM morningstar_efficiency', self.conn) if self.tables_with_data['morningstar_efficiency'] else pd.DataFrame()
        self.ms_growth = pd.read_sql('SELECT * FROM morningstar_growth', self.conn) if self.tables_with_data['morningstar_growth'] else pd.DataFrame()
        self.ms_cash_flow = pd.read_sql('SELECT * FROM morningstar_cash_flow', self.conn) if self.tables_with_data['morningstar_cash_flow'] else pd.DataFrame()
        
        print('\nData availability summary:')
        for table, has_data in self.tables_with_data.items():
            print(f"✓ {table}" if has_data else f"✗ {table} (not implemented yet)")

    def has_data(self):
        """Check if there's any data available for analysis"""
        return any(self.tables_with_data.values())

    def valuation(self):
        if self.ms_valuation.empty:
            print('No valuation data found.')
        return self.ms_valuation

    def financial_health(self):
        if self.ms_financial_health.empty:
            print('No financial health data found.')
        return self.ms_financial_health

    def profitability(self):
        if self.ms_profitability.empty:
            print('No profitability data found.')
        return self.ms_profitability

    def efficiency(self):
        if self.ms_efficiency.empty:
            print('No efficiency data found.')
        return self.ms_efficiency

    def growth(self):
        if self.ms_growth.empty:
            print('No growth data found.')
        return self.ms_growth

    def cash_flow(self):
        if self.ms_cash_flow.empty:
            print('No cash flow data found.')
        return self.ms_cash_flow

    def get_latest_data(self, symbol):
        data = {}
        master_data = self.master[self.master['symbol'] == symbol]
        if not master_data.empty:
            data['master'] = master_data.iloc[0]
        wsj_data = self.wsj_data[self.wsj_data['symbol'] == symbol]
        if not wsj_data.empty:
            data['wsj'] = wsj_data.iloc[0]
        ms_val = self.ms_valuation[self.ms_valuation['symbol'] == symbol]
        if not ms_val.empty:
            data['morningstar'] = {
                'valuation': ms_val.iloc[0] if not ms_val.empty else None,
                'financial_health': self.ms_financial_health[self.ms_financial_health['symbol'] == symbol].iloc[0] if not self.ms_financial_health[self.ms_financial_health['symbol'] == symbol].empty else None,
                'profitability': self.ms_profitability[self.ms_profitability['symbol'] == symbol].iloc[0] if not self.ms_profitability[self.ms_profitability['symbol'] == symbol].empty else None,
                'efficiency': self.ms_efficiency[self.ms_efficiency['symbol'] == symbol].iloc[0] if not self.ms_efficiency[self.ms_efficiency['symbol'] == symbol].empty else None,
                'growth': self.ms_growth[self.ms_growth['symbol'] == symbol].iloc[0] if not self.ms_growth[self.ms_growth['symbol'] == symbol].empty else None,
                'cash_flow': self.ms_cash_flow[self.ms_cash_flow['symbol'] == symbol].iloc[0] if not self.ms_cash_flow[self.ms_cash_flow['symbol'] == symbol].empty else None
            }
        return data

    def plot_metric_distribution(self, metric, sector=None, bins=30, figsize=(12, 6)):
    """Plot distribution of a metric across stocks."""
    values = []
    symbols = []
    for symbol in self.master['symbol']:
        if sector and 'sector' in self.master.columns and self.master[self.master['symbol'] == symbol]['sector'].iloc[0] != sector:
            continue
        data = self.get_latest_data(symbol)
        value = None
        if 'wsj' in data and metric in data['wsj']:
            value = data['wsj'][metric]
        elif 'morningstar' in data:
            for category in data['morningstar'].values():
                if category is not None and metric in category:
                    value = category[metric]
                    break
        if value is not None:
            values.append(value)
            symbols.append(symbol)
    if values:
        plt.figure(figsize=figsize)
        sns.histplot(values, bins=bins, kde=True)
        plt.title(f'Distribution of {metric}')
        plt.xlabel(metric)
        plt.ylabel('Number of stocks')
        plt.grid(True, alpha=0.3)
        plt.show()
        return pd.DataFrame({'symbol': symbols, metric: values})
    return None

    def plot_sector_comparison(self, metric, top_n=10):
        """Plot comparison of a metric across different sectors."""
        sector_data = {}
        for symbol in self.master['symbol']:
            if 'sector' not in self.master.columns:
                continue
            sector = self.master[self.master['symbol'] == symbol]['sector'].iloc[0]
            if pd.isna(sector):
                continue

            data = self.get_latest_data(symbol)
            value = None
            if 'wsj' in data and metric in data['wsj']:
                value = data['wsj'][metric]
            elif 'morningstar' in data:
                for category in data['morningstar'].values():
                    if category is not None and metric in category:
                        value = category[metric]
                        break

            if value is not None:
                if sector not in sector_data:
                    sector_data[sector] = []
                sector_data[sector].append(value)

        if sector_data:
            # Calculate mean for each sector
            sector_means = {sector: np.mean(values) for sector, values in sector_data.items()}
            # Sort sectors by mean value
            sorted_sectors = sorted(sector_means.items(), key=lambda x: x[1], reverse=True)[:top_n]

            plt.figure(figsize=(12, 6))
            sectors = [s[0] for s in sorted_sectors]
            means = [s[1] for s in sorted_sectors]

            sns.barplot(x=sectors, y=means)
            plt.title(f'Average {metric} by Sector (Top {top_n})')
            plt.xticks(rotation=45, ha='right')
            plt.xlabel('Sector')
            plt.ylabel(metric)
            plt.tight_layout()
            plt.show()

            return pd.DataFrame({'sector': sectors, f'avg_{metric}': means})
        return None

    def plot_correlation_matrix(self, metrics):
        """Plot correlation matrix for given metrics."""
        data = {}
        for symbol in self.master['symbol']:
            symbol_data = {}
            data[symbol] = self.get_latest_data(symbol)

            for metric in metrics:
                value = None
                if 'wsj' in data[symbol] and metric in data[symbol]['wsj']:
                    value = data[symbol]['wsj'][metric]
                elif 'morningstar' in data[symbol]:
                    for category in data[symbol]['morningstar'].values():
                        if category is not None and metric in category:
                            value = category[metric]
                            break
                symbol_data[metric] = value

            data[symbol] = symbol_data

        # Convert to DataFrame
        df = pd.DataFrame.from_dict(data, orient='index')
        # Calculate correlation matrix
        corr = df.corr()

        plt.figure(figsize=(10, 8))
        sns.heatmap(corr, annot=True, cmap='coolwarm', center=0)
        plt.title('Correlation Matrix of Financial Metrics')
        plt.tight_layout()
        plt.show()

        return corr


def main():
    print("Initializing DataFrames...")
    df = DataFrames()

    if not df.has_data():
        print("\nNo data available for analysis. Please ensure data is fetched and stored in the database.")
        print("Required steps:")
        print("1. Fetch data from Alpha Vantage")
        print("2. Fetch data from WSJ")
        print("3. Fetch data from Morningstar")
        print("4. Store the data in the appropriate tables")
        return

    print("\nFiltering active records...")
    cutoff_days = 1

    # Use correct column names: 'symbol' instead of 'ticker', 'last_updated' instead of 'update_date'
    df_updated_ct = df.master[['last_updated', 'symbol']].groupby('last_updated').count().sort_index()

    try:
        cutoff_date = df_updated_ct[df_updated_ct['symbol'] > 100].index[0]
        print(f"Cutoff date: {cutoff_date}")

        # Filter master table for active records
        active_records = df.master[df.master['last_updated'] >= cutoff_date]
        print(f"Active records: {len(active_records)}")

        # Example: Get stock price ratios
        print("\nGetting stock price ratios...")
        df_vals = df.valuation()

        # Example: Screen for stocks with P/E ratio < 15 and P/B ratio < 1.5
        print("\nScreening for value stocks...")
        value_stocks = df_vals[
            (df_vals['pe_ratio'] < 15) &
            (df_vals['price_to_book'] < 1.5)
        ]
        print(f"Found {len(value_stocks)} value stocks")

        # Generate visualizations
        print("\nGenerating visualizations...")
        
        # Plot P/E ratio distribution
        pe_dist = df.plot_metric_distribution('pe_ratio')
        if pe_dist is not None:
            print("\nP/E Ratio Statistics:")
            print(pe_dist['pe_ratio'].describe())

        # Plot sector comparison of P/E ratios
        sector_pe = df.plot_sector_comparison('pe_ratio')
        if sector_pe is not None:
            print("\nSector P/E Ratio Averages:")
            print(sector_pe)

        # Plot correlation matrix of key metrics
        metrics = ['pe_ratio', 'price_to_book', 'price_to_sales', 'dividend_yield']
        corr_matrix = df.plot_correlation_matrix(metrics)
        if corr_matrix is not None:
            print("\nCorrelation Matrix:")
            print(corr_matrix)

    except IndexError:
        print("No cutoff date found with more than 100 records")
    except Exception as e:
        print(f"Error: {str(e)}")

    print("\nAnalysis complete.")


if __name__ == "__main__":
    main()