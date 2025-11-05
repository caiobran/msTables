import requests
import pandas as pd
import logging
from datetime import datetime
import sqlite3

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/metalprice_api.log'),
        logging.StreamHandler()
    ]
)

# TODO 1.0.0: Move API key to environment variables for security
API_KEY = '0679f72247618142bf3dce0417dac7c4'
BASE_URL = 'https://api.metalpriceapi.com/v1/latest'
SYMBOLS_URL = 'https://api.metalpriceapi.com/v1/symbols'
DB_PATH = 'data/mstables.sqlite'


def fetch_all_symbols():
    params = {'api_key': API_KEY}
    # TODO 1.1.0: Add proper rate limiting and error handling
    response = requests.get(SYMBOLS_URL, params=params)
    if response.status_code == 200:
        data = response.json()
        return list(data.get('symbols', {}).keys())
    else:
        logging.error(f"Error fetching symbols: {response.status_code}")
        return []


def fetch_metal_price(metal):
    params = {
        'api_key': API_KEY,
        'base': metal,
        'currencies': 'USD'
    }
    # TODO 1.1.0: Add retry logic and better error handling
    response = requests.get(BASE_URL, params=params)
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        logging.error(f"Error fetching data for {metal}: {response.status_code}")
        return None


def save_to_db(metal, price, timestamp):
    # TODO 1.0.0: Use the new precious_metals_data table instead of metal_prices
    with sqlite3.connect(DB_PATH) as conn:
        # TODO 1.0.0: This table should be renamed to currency_prices
        conn.execute('''CREATE TABLE IF NOT EXISTS metal_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            price REAL,
            timestamp TEXT
        )''')
        conn.execute('''INSERT INTO metal_prices (symbol, price, timestamp) VALUES (?, ?, ?)''',
                     (metal, price, timestamp))
        conn.commit()
        logging.info(f"Saved {metal} price {price} at {timestamp} to database.")

def log_unavailable_symbol(metal, reason):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS unavailable_symbols (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            reason TEXT,
            timestamp TEXT
        )''')
        conn.execute('''INSERT INTO unavailable_symbols (symbol, reason, timestamp) VALUES (?, ?, ?)''',
                     (metal, reason, datetime.utcnow().isoformat()))
        conn.commit()
        logging.warning(f"Logged unavailable symbol: {metal}, reason: {reason}")


def main():
    """Main function to demonstrate usage."""
    # TODO 1.0.0: Add proper command line argument parsing
    # TODO 1.0.0: Add configuration file support
    
    # Get all available symbols
    symbols = fetch_all_symbols()
    print(f"Available symbols: {symbols}")
    
    # Fetch prices for major metals
    metals = ['XAU', 'XAG', 'XPT', 'XPD']  # Gold, Silver, Platinum, Palladium
    
    for metal in metals:
        if metal in symbols:
            data = fetch_metal_price(metal)
            if data and 'rates' in data:
                price = data['rates'].get('USD', 0)
                timestamp = data.get('timestamp', datetime.utcnow().isoformat())
                save_to_db(metal, price, timestamp)
                print(f"Saved {metal}: ${price}")
            else:
                log_unavailable_symbol(metal, "No data returned")
        else:
            log_unavailable_symbol(metal, "Symbol not available")


if __name__ == "__main__":
    main() 