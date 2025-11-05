#!/usr/bin/env python

import json
import requests
import pandas as pd
from datetime import datetime
import time

def fetch_wsj_data():
    """Fetch data from WSJ Asia stocks API"""
    url = "https://www.wsj.com/market-data/stocks/asia"
    params = {
        "id": '{"application":"WSJ","instruments":'
              '[{"symbol":"INDEX/HK//HSI","name":"Hong Kong: Hang Seng"},'
              '{"symbol":"INDEX/JP//NIK","name":"Japan: Nikkei 225"},'
              '{"symbol":"INDEX/CN//SHCOMP","name":"China: Shanghai Composite"},'
              '{"symbol":"INDEX/IN//1","name":"India: S&P BSE Sensex"},'
              '{"symbol":"INDEX/AU//XJO","name":"Australia: S&P/ASX"},'
              '{"symbol":"INDEX/KR//SEU","name":"S. Korea: KOSPI"},'
              '{"symbol":"INDEX/US//GDOW","name":"Global Dow"},'
              '{"symbol":"FUTURE/US//DJIA FUTURES","name":"DJIA Futures"}]}',
        "type": "mdc_quotes",
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:88.0) Gecko/20100101 Firefox/88.0"
    }

    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

def explore_data_structure(data):
    """Explore the structure of the data"""
    print("\n=== Data Structure Exploration ===")
    
    # Print top-level keys
    print("\nTop-level keys:")
    for key in data.keys():
        print(f"- {key}")
    
    # Explore data section
    if "data" in data:
        print("\nData section keys:")
        for key in data["data"].keys():
            print(f"- {key}")
        
        # Explore instruments
        if "instruments" in data["data"]:
            print("\nFirst instrument keys:")
            first_instrument = data["data"]["instruments"][0]
            for key in first_instrument.keys():
                print(f"- {key}")

def create_dataframes(data):
    """Create various DataFrames from the data"""
    print("\n=== Creating DataFrames ===")
    
    # Main DataFrame with all instrument data
    main_df = pd.json_normalize(data["data"]["instruments"])
    
    # Create separate DataFrames for different aspects
    price_df = main_df[['formattedName', 'lastPrice', 'priceChange', 'percentChange', 'dailyHigh', 'dailyLow']]
    metadata_df = main_df[['formattedName', 'country', 'exchangeIsoCode', 'type', 'ticker', 'requestSymbol']]
    time_df = main_df[['formattedName', 'timestamp']]
    
    # Add timestamp parsing
    time_df['timestamp'] = pd.to_datetime(time_df['timestamp'])
    time_df['local_time'] = time_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    return {
        'main': main_df,
        'prices': price_df,
        'metadata': metadata_df,
        'timestamps': time_df
    }

def save_dataframes(dfs):
    """Save DataFrames to CSV files"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    for name, df in dfs.items():
        filename = f'test/wsj_{name}_{timestamp}.csv'
        df.to_csv(filename, index=False)
        print(f"Saved {name} DataFrame to {filename}")

def main():
    print("Starting WSJ data exploration...")
    
    # Fetch data
    data = fetch_wsj_data()
    if not data:
        print("Failed to fetch data")
        return
    
    # Explore data structure
    explore_data_structure(data)
    
    # Create DataFrames
    dfs = create_dataframes(data)
    
    # Print DataFrame summaries
    print("\n=== DataFrame Summaries ===")
    for name, df in dfs.items():
        print(f"\n{name.upper()} DataFrame:")
        print(f"Shape: {df.shape}")
        print("\nColumns:")
        for col in df.columns:
            print(f"- {col}")
        print("\nFirst few rows:")
        print(df.head())
    
    # Save DataFrames
    save_dataframes(dfs)
    
    print("\nExploration complete! Check the test directory for CSV files.")

if __name__ == '__main__':
    main() 