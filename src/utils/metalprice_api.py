import requests
import pandas as pd
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)

API_KEY = '0679f72247618142bf3dce0417dac7c4'
BASE_URL = 'https://api.metalpriceapi.com/v1/latest'

def fetch_metal_price(metal):
    params = {
        'api_key': API_KEY,
        'base': metal,
        'currencies': 'USD'
    }
    response = requests.get(BASE_URL, params=params)
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        logging.error(f"Error fetching data for {metal}: {response.status_code}")
        return None

def fetch_multiple_metals(metals):
    results = {}
    for metal in metals:
        data = fetch_metal_price(metal)
        if data:
            results[metal] = data
    return results

if __name__ == "__main__":
    metals = ['XAU', 'XAG', 'XPT', 'XPD', 'XCU']  # Gold, Silver, Platinum, Palladium, Copper
    results = fetch_multiple_metals(metals)
    for metal, data in results.items():
        logging.info(f"Data for {metal}: {data}") 