import json
import requests
import pandas as pd
from datetime import datetime
import os
import time
import random
from .store import store_wsj_data

# Define paths
DATA_DIR = 'data'
CSV_DIR = os.path.join(DATA_DIR, 'csv', 'wsj')
RAW_DIR = os.path.join(DATA_DIR, 'raw', 'wsj')

# Create directories if they don't exist
os.makedirs(CSV_DIR, exist_ok=True)
os.makedirs(RAW_DIR, exist_ok=True)

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

def fetch_wsj_data(indices=None, db_path='data/mstables.sqlite'):
    """Fetch data from WSJ API and store in database."""
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
        # Add random delay between 3-7 seconds
        time.sleep(random.uniform(3, 7))
        
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        
        # Parse response
        data = response.json()
        if 'data' not in data or 'instruments' not in data['data']:
            print("No data found in response")
            return []
        
        # Convert to DataFrame
        records = []
        for item in data['data']['instruments']:
            symbol = item.get('requestSymbol', '').split('//')[-1]
            if not symbol:
                continue
                
            info = indices.get(symbol, {})
            record = {
                'symbol': symbol,
                'name': info.get('name', ''),
                'exchange': item.get('exchange', ''),
                'country': info.get('country', ''),
                'type': info.get('type', 'INDEX'),
                'last_price': item.get('lastPrice', 0),
                'change': item.get('change', 0),
                'percent_change': item.get('percentChange', 0),
                'daily_high': item.get('high', 0),
                'daily_low': item.get('low', 0),
                'timestamp': item.get('timestamp', ''),
                'url': f"https://www.wsj.com/market-data/quotes/{symbol}"
            }
            records.append(record)
        
        df = pd.DataFrame(records)
        
        # Store data
        return store_wsj_data(df, db_path)
        
    except requests.RequestException as e:
        print(f"Error fetching WSJ data: {e}")
        return []
    except Exception as e:
        print(f"Error processing WSJ data: {e}")
        return [] 