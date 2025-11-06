#!/usr/bin/env python

import json
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
import time

def fetch_wsj_data():
    """Fetch data from WSJ Asia stocks page and API"""
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
        # Fetch both HTML and API data
        html_response = requests.get(url, headers=headers)
        html_response.raise_for_status()
        
        api_response = requests.get(url, params=params, headers=headers)
        api_response.raise_for_status()
        
        return {
            'html': html_response.text,
            'api': api_response.json()
        }
    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

def explore_html_data(html_content):
    """Explore data from HTML content using BeautifulSoup"""
    print("\n=== HTML Data Exploration ===")
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find all tables
    tables = soup.find_all('table')
    print(f"\nFound {len(tables)} tables in the page")
    
    # Find all JSON data in script tags
    scripts = soup.find_all('script', type='application/json')
    print(f"Found {len(scripts)} JSON script tags")
    
    # Find all data attributes
    data_elements = soup.find_all(attrs={"data-": True})
    print(f"Found {len(data_elements)} elements with data attributes")
    
    # Store found data
    data = {
        'tables': [],
        'json_data': [],
        'data_attributes': []
    }
    
    # Extract table data
    for i, table in enumerate(tables):
        try:
            df = pd.read_html(str(table))[0]
            data['tables'].append({
                'index': i,
                'columns': df.columns.tolist(),
                'shape': df.shape,
                'preview': df.head(2).to_dict()
            })
        except Exception as e:
            print(f"Error parsing table {i}: {e}")
    
    # Extract JSON data
    for i, script in enumerate(scripts):
        try:
            json_data = json.loads(script.string)
            data['json_data'].append({
                'index': i,
                'keys': list(json_data.keys()) if isinstance(json_data, dict) else 'Not a dictionary',
                'preview': str(json_data)[:200] + '...' if len(str(json_data)) > 200 else str(json_data)
            })
        except Exception as e:
            print(f"Error parsing JSON {i}: {e}")
    
    # Extract data attributes
    for i, element in enumerate(data_elements):
        try:
            data['data_attributes'].append({
                'index': i,
                'tag': element.name,
                'attributes': {k: v for k, v in element.attrs.items() if k.startswith('data-')},
                'text': element.text[:100] + '...' if len(element.text) > 100 else element.text
            })
        except Exception as e:
            print(f"Error parsing data attributes {i}: {e}")
    
    return data

def explore_api_data(api_data):
    """Explore data from the API response"""
    print("\n=== API Data Exploration ===")
    
    # Print top-level keys
    print("\nTop-level keys:")
    for key in api_data.keys():
        print(f"- {key}")
    
    # Explore data section
    if "data" in api_data:
        print("\nData section keys:")
        for key in api_data["data"].keys():
            print(f"- {key}")
        
        # Explore instruments
        if "instruments" in api_data["data"]:
            print("\nFirst instrument keys:")
            first_instrument = api_data["data"]["instruments"][0]
            for key in first_instrument.keys():
                print(f"- {key}")

def create_api_dataframes(api_data):
    """Create DataFrames from API data"""
    print("\n=== Creating API DataFrames ===")
    
    # Main DataFrame with all instrument data
    main_df = pd.json_normalize(api_data["data"]["instruments"])
    
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

def save_data(html_data, api_dfs, timestamp):
    """Save all data to files"""
    # Save HTML content
    with open(f'test/wsj_html_{timestamp}.html', 'w', encoding='utf-8') as f:
        f.write(html_data)
    print(f"\nSaved raw HTML to test/wsj_html_{timestamp}.html")
    
    # Save HTML exploration results
    for name, data in html_data.items():
        if data:  # Only save if there's data
            df = pd.DataFrame(data)
            df.to_csv(f'test/wsj_html_{name}_{timestamp}.csv', index=False)
            print(f"Saved HTML {name} to test/wsj_html_{name}_{timestamp}.csv")
    
    # Save API DataFrames
    for name, df in api_dfs.items():
        df.to_csv(f'test/wsj_api_{name}_{timestamp}.csv', index=False)
        print(f"Saved API {name} to test/wsj_api_{name}_{timestamp}.csv")

def main():
    print("Starting WSJ data exploration...")
    
    # Fetch both HTML and API data
    data = fetch_wsj_data()
    if not data:
        print("Failed to fetch data")
        return
    
    # Explore HTML data
    html_data = explore_html_data(data['html'])
    
    # Explore API data
    explore_api_data(data['api'])
    
    # Create API DataFrames
    api_dfs = create_api_dataframes(data['api'])
    
    # Print DataFrame summaries
    print("\n=== API DataFrame Summaries ===")
    for name, df in api_dfs.items():
        print(f"\n{name.upper()} DataFrame:")
        print(f"Shape: {df.shape}")
        print("\nColumns:")
        for col in df.columns:
            print(f"- {col}")
        print("\nFirst few rows:")
        print(df.head())
    
    # Save all data
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_data(html_data, api_dfs, timestamp)
    
    print("\nExploration complete! Check the test directory for all data files.")

if __name__ == '__main__':
    main() 