import pandas as pd
from datetime import datetime

def parse_wsj_data(data):
    """Parse WSJ API response data."""
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
            'url': instrument.get('url', '')
        }
        results.append(result)
    
    return pd.DataFrame(results) 