import pandas as pd
import sqlite3
from datetime import datetime
import random

def get_csv_data(ticker):
    """Get data from CSV file for a specific ticker"""
    # Read the CSV file
    df = pd.read_csv('data/data_stocks.csv')
    
    # Convert Unix timestamp to datetime
    df['DATE'] = pd.to_datetime(df['DATE'], unit='s')
    
    # Get the column name for the ticker
    ticker_col = f'NASDAQ.{ticker}' if f'NASDAQ.{ticker}' in df.columns else f'NYSE.{ticker}'
    
    # Select relevant columns
    result = df[['DATE', ticker_col]].copy()
    result.columns = ['Date', 'Close']
    
    return result

def get_db_data(ticker):
    """Get data from database for a specific ticker"""
    conn = sqlite3.connect('data/mstables.sqlite')
    
    # Try different tables for price data
    tables_to_try = [
        ('tiingo_prices', 'date', 'close'),
        ('YahooQuote', 'date', 'close')
    ]
    
    df = None
    for table, date_col, close_col in tables_to_try:
        try:
            query = f'''
                SELECT {date_col} as Date, 
                       {close_col} as Close
                FROM {table}
                WHERE symbol = '{ticker}'
                ORDER BY {date_col}
            '''
            df = pd.read_sql_query(query, conn)
            if not df.empty:
                print(f"Found data for {ticker} in {table}")
                break
        except Exception as e:
            print(f"No data in {table} for {ticker}: {str(e)}")
            continue
    
    conn.close()
    
    if df is not None and not df.empty:
        df['Date'] = pd.to_datetime(df['Date'])
    
    return df

def compare_data(ticker):
    """Compare data between CSV and database"""
    # Get data from both sources
    csv_data = get_csv_data(ticker)
    db_data = get_db_data(ticker)
    
    if db_data is None or db_data.empty:
        print(f"No database data found for {ticker}")
        return {
            'ticker': ticker,
            'csv_count': len(csv_data),
            'db_count': 0,
            'matching_dates': 0,
            'price_diff_stats': None
        }
    
    # Ensure both Date columns are timezone-naive
    csv_data['Date'] = csv_data['Date'].dt.tz_localize(None)
    db_data['Date'] = db_data['Date'].dt.tz_localize(None)
    
    # Merge the data
    merged = pd.merge(csv_data, db_data, on='Date', how='outer', suffixes=('_csv', '_db'))
    
    # Calculate statistics
    print(f"\nComparison for {ticker}:")
    print(f"Number of records in CSV: {len(csv_data)}")
    print(f"Number of records in DB: {len(db_data)}")
    print(f"Number of matching dates: {len(merged.dropna())}")
    
    # Calculate price differences
    merged['price_diff'] = merged['Close_csv'] - merged['Close_db']
    print("\nPrice difference statistics:")
    stats = merged['price_diff'].describe()
    print(stats)
    
    # Show sample of differences
    print("\nSample of dates with different prices:")
    sample = merged[merged['price_diff'].abs() > 0.01].head()
    print(sample[['Date', 'Close_csv', 'Close_db', 'price_diff']])
    
    return {
        'ticker': ticker,
        'csv_count': len(csv_data),
        'db_count': len(db_data),
        'matching_dates': len(merged.dropna()),
        'price_diff_stats': stats
    }

def get_random_tickers(n=10):
    df = pd.read_csv('data/data_stocks.csv', nrows=1)
    tickers = [col.split('.')[-1] for col in df.columns if col not in ['DATE', 'SP500']]
    return random.sample(tickers, n)

def main():
    random_tickers = get_random_tickers(10)
    print(f"Comparing the following 10 random tickers: {random_tickers}\n")
    for ticker in random_tickers:
        result = compare_data(ticker)
        print(f"Ticker: {result['ticker']}")
        print(f"  CSV records: {result['csv_count']}")
        print(f"  DB records: {result['db_count']}")
        print(f"  Matching dates: {result['matching_dates']}")
        if result['price_diff_stats'] is not None:
            print(f"  Price diff stats:\n{result['price_diff_stats']}")
        else:
            print("  No price comparison possible (no DB data)")
        print()

if __name__ == "__main__":
    main() 