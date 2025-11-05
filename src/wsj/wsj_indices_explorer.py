#!/usr/bin/env python

import json
import requests
import pandas as pd
from datetime import datetime
import time

# Define the indices we know about
KNOWN_INDICES = {
    # Asia Pacific
    'HSI': {'name': 'Hong Kong: Hang Seng', 'country': 'HK'},
    'NIK': {'name': 'Japan: Nikkei 225', 'country': 'JP'},
    'SHCOMP': {'name': 'China: Shanghai Composite', 'country': 'CN'},
    '1': {'name': 'India: S&P BSE Sensex', 'country': 'IN'},
    'XJO': {'name': 'Australia: S&P/ASX', 'country': 'AU'},
    'SEU': {'name': 'S. Korea: KOSPI', 'country': 'KR'},
    
    # Global
    'GDOW': {'name': 'Global Dow', 'country': 'US'},
    
    # US Indices
    'DJI': {'name': 'Dow Jones Industrial Average', 'country': 'US'},
    'SPX': {'name': 'S&P 500', 'country': 'US'},
    'COMP': {'name': 'Nasdaq Composite', 'country': 'US'},
    'RUT': {'name': 'Russell 2000', 'country': 'US'},
    
    # European Indices
    'UKX': {'name': 'FTSE 100', 'country': 'UK'},
    'DAX': {'name': 'DAX', 'country': 'DE'},
    'CAC': {'name': 'CAC 40', 'country': 'FR'},
    
    # Futures
    'YM00': {'name': 'DJIA Futures', 'country': 'US', 'type': 'FUTURE'},
    'ES00': {'name': 'S&P 500 Futures', 'country': 'US', 'type': 'FUTURE'},
    'NQ00': {'name': 'Nasdaq Futures', 'country': 'US', 'type': 'FUTURE'},
    'RTY00': {'name': 'Russell 2000 Futures', 'country': 'US', 'type': 'FUTURE'},
    'Z00': {'name': 'FTSE 100 Futures', 'country': 'UK', 'type': 'FUTURE'},
    'DX00': {'name': 'DAX Futures', 'country': 'DE', 'type': 'FUTURE'},
    'CAC00': {'name': 'CAC 40 Futures', 'country': 'FR', 'type': 'FUTURE'},
}

def fetch_wsj_data(indices=None):
    """Fetch data from WSJ for specified indices"""
    if indices is None:
        indices = KNOWN_INDICES
    
    url = "https://www.wsj.com/market-data/stocks/asia"
    
    # Build the instruments list
    instruments = []
    for symbol, info in indices.items():
        instrument_type = info.get('type', 'INDEX')
        instruments.append({
            "symbol": f"{instrument_type}/{info['country']}//{symbol}",
            "name": info['name']
        })
    
    params = {
        "id": json.dumps({
            "application": "WSJ",
            "instruments": instruments
        }),
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

def explore_available_indices():
    """Try to discover additional indices available from WSJ"""
    # Common exchange suffixes
    exchanges = ['US', 'UK', 'EU', 'JP', 'HK', 'CN', 'IN', 'AU', 'KR', 'SG', 'CA', 'BR', 'RU', 'DE', 'FR', 'CH', 'IT', 'ES', 'NL']
    
    # Common index types
    index_types = ['INDEX', 'FUTURE', 'STOCK']
    
    # Common index symbols to try
    common_symbols = ['DJI', 'SPX', 'COMP', 'RUT', 'UKX', 'DAX', 'CAC', 'HSI', 'NIK', 'SHCOMP', '1', 'XJO', 'SEU']
    
    results = []
    
    for exchange in exchanges:
        for index_type in index_types:
            for symbol in common_symbols:
                # Try to fetch data for this exchange/type/symbol combination
                test_params = {
                    "id": json.dumps({
                        "application": "WSJ",
                        "instruments": [{
                            "symbol": f"{index_type}/{exchange}//{symbol}",
                            "name": f"Test {exchange} {index_type} {symbol}"
                        }]
                    }),
                    "type": "mdc_quotes",
                }
                
                try:
                    response = requests.get(
                        "https://www.wsj.com/market-data/stocks/asia",
                        params=test_params,
                        headers={"User-Agent": "Mozilla/5.0"}
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        if 'data' in data and 'instruments' in data['data']:
                            results.append({
                                'exchange': exchange,
                                'type': index_type,
                                'symbol': symbol,
                                'status': 'Available',
                                'response': len(data['data']['instruments'])
                            })
                        else:
                            results.append({
                                'exchange': exchange,
                                'type': index_type,
                                'symbol': symbol,
                                'status': 'No data',
                                'response': 0
                            })
                except Exception as e:
                    results.append({
                        'exchange': exchange,
                        'type': index_type,
                        'symbol': symbol,
                        'status': f'Error: {str(e)}',
                        'response': 0
                    })
                
                time.sleep(1)  # Be nice to the server
    
    return pd.DataFrame(results)

def analyze_index_data(data):
    """Analyze the data structure for a specific index"""
    if not data or 'data' not in data or 'instruments' not in data['data']:
        return None
    
    instruments = data['data']['instruments']
    results = []
    
    for instrument in instruments:
        # Extract all available fields
        result = {
            'symbol': instrument.get('requestSymbol', ''),
            'name': instrument.get('formattedName', ''),
            'country': instrument.get('country', ''),
            'exchange': instrument.get('exchangeIsoCode', ''),
            'type': instrument.get('type', ''),
            'last_price': instrument.get('lastPrice', ''),
            'change': instrument.get('priceChange', ''),
            'percent_change': instrument.get('percentChange', ''),
            'daily_high': instrument.get('dailyHigh', ''),
            'daily_low': instrument.get('dailyLow', ''),
            'timestamp': instrument.get('timestamp', ''),
            'available_fields': list(instrument.keys())
        }
        results.append(result)
    
    return pd.DataFrame(results)

def main():
    print("Starting WSJ indices exploration...")
    
    # 1. Test known indices
    print("\n=== Testing Known Indices ===")
    data = fetch_wsj_data()
    if data:
        df = analyze_index_data(data)
        if df is not None:
            print("\nKnown Indices Data:")
            print(df[['symbol', 'name', 'country', 'last_price', 'change', 'percent_change']])
            
            # Save to CSV
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            df.to_csv(f'test/wsj_known_indices_{timestamp}.csv', index=False)
            print(f"\nSaved known indices data to test/wsj_known_indices_{timestamp}.csv")
    
    # 2. Explore available indices
    print("\n=== Exploring Available Indices ===")
    available_df = explore_available_indices()
    print("\nAvailable Indices:")
    print(available_df)
    
    # Save available indices to CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    available_df.to_csv(f'test/wsj_available_indices_{timestamp}.csv', index=False)
    print(f"\nSaved available indices data to test/wsj_available_indices_{timestamp}.csv")
    
    print("\nExploration complete! Check the test directory for CSV files.")

if __name__ == '__main__':
    main() 