#!/usr/bin/env python

import json
import requests
import pandas as pd
from datetime import datetime
import time

def test_url(url_id, url, exchange="XNYS", ticker="AAPL"):
    """Test if a URL is accessible"""
    try:
        # Format the URL with exchange and ticker
        formatted_url = url.format(exchange, ticker)
        
        # Make the request
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:88.0) Gecko/20100101 Firefox/88.0"
        }
        response = requests.get(formatted_url, headers=headers)
        
        # Check if we got a valid response
        if response.status_code == 200 and len(response.text) > 0:
            return True, response.status_code, len(response.text)
        else:
            return False, response.status_code, 0
    except Exception as e:
        return False, str(e), 0

def main():
    # Load the API URLs
    with open('input/api.json') as f:
        apis = json.load(f)
    
    # Test each URL
    results = []
    for url_id, url in apis.items():
        print(f"\nTesting URL ID {url_id}...")
        success, status, length = test_url(url_id, url)
        results.append({
            'URL ID': url_id,
            'URL': url,
            'Status': 'Working' if success else 'Not Working',
            'Response': status,
            'Data Length': length
        })
        time.sleep(1)  # Be nice to the server
    
    # Create a DataFrame for better viewing
    df = pd.DataFrame(results)
    print("\nResults:")
    print(df.to_string(index=False))
    
    # Save results to CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    df.to_csv(f'test/url_status_{timestamp}.csv', index=False)
    print(f"\nResults saved to test/url_status_{timestamp}.csv")

if __name__ == '__main__':
    main() 