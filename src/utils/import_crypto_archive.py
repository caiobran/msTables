import pandas as pd
import sqlite3
import os
import logging
from tqdm import tqdm
import numpy as np
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crypto_import.log'),
        logging.StreamHandler()
    ]
)

def validate_dataframe(df, file_name):
    """Validate the dataframe has required columns and data types."""
    if 'crypto_tradinds.csv' in file_name:
        # Handle crypto_tradinds.csv format
        required_columns = ['trade_date', 'volume', 'price_usd', 'price_btc', 'market_cap']
        if not all(col in df.columns for col in required_columns):
            missing_cols = [col for col in required_columns if col not in df.columns]
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Convert date column to datetime
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        
        # Convert numeric columns
        numeric_cols = ['volume', 'price_usd', 'price_btc', 'market_cap']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Rename columns to match expected format
        df = df.rename(columns={
            'trade_date': 'Date',
            'price_usd': 'Price',
            'price_btc': 'Price_BTC',
            'volume': 'Vol',
            'market_cap': 'Market_Cap'
        })
        
        # Add missing columns with default values
        df['Open'] = df['Price']
        df['High'] = df['Price']
        df['Low'] = df['Price']
        df['Change_Pct'] = 0.0
        
    else:
        # Handle standard format
        required_columns = ['Date', 'Price', 'Open', 'High', 'Low', 'Vol.', 'Change %']
        if not all(col in df.columns for col in required_columns):
            missing_cols = [col for col in required_columns if col not in df.columns]
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Convert date column to datetime
        df['Date'] = pd.to_datetime(df['Date'])
        
        # Convert numeric columns
        numeric_cols = ['Price', 'Open', 'High', 'Low', 'Vol.', 'Change %']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Rename columns
        df = df.rename(columns={
            'Vol.': 'Vol',
            'Change %': 'Change_Pct'
        })
    
    return df

def process_file(file_path, conn, batch_size=10000):
    """Process a single file in batches."""
    try:
        # Read the file in chunks
        chunks = pd.read_csv(file_path, chunksize=batch_size)
        total_rows = 0
        
        for chunk in chunks:
            try:
                # Validate and clean the chunk
                chunk = validate_dataframe(chunk, os.path.basename(file_path))
                
                # Drop any remaining NaN values
                chunk = chunk.dropna()
                
                # Write to database
                chunk.to_sql('crypto_archive', conn, if_exists='append', index=False)
                total_rows += len(chunk)
                
            except Exception as e:
                logging.error(f"Error processing chunk in {os.path.basename(file_path)}: {str(e)}")
                continue
        
        return total_rows
    
    except Exception as e:
        logging.error(f"Error reading file {os.path.basename(file_path)}: {str(e)}")
        return 0

def main():
    folder = '/Users/xavier/sbox/Financial_Data/Crypto_Data/data_crypto_archive_2018_2022'
    db_path = 'data/mstables.sqlite'
    
    # Create database connection
    conn = sqlite3.connect(db_path)
    
    # Get list of CSV files
    csv_files = [f for f in os.listdir(folder) if f.endswith('.csv')]
    
    # Process each file with progress bar
    total_files = len(csv_files)
    logging.info(f"Found {total_files} CSV files to process")
    
    for file in tqdm(csv_files, desc="Processing files"):
        file_path = os.path.join(folder, file)
        try:
            # Process the file
            rows_imported = process_file(file_path, conn)
            
            if rows_imported > 0:
                # Delete the original file after successful import
                os.remove(file_path)
                logging.info(f"Successfully imported {rows_imported} rows from {file} and deleted the file")
            else:
                logging.warning(f"No rows were imported from {file}")
                
        except Exception as e:
            logging.error(f"Failed to process {file}: {str(e)}")
            continue
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    logging.info("Import process completed")

if __name__ == "__main__":
    main() 