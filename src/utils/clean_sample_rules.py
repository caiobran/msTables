import pandas as pd
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/clean_sample_rules.log'),
        logging.StreamHandler()
    ]
)

def clean_sample_rules(csv_path='data/sample_rules_output.csv', output_path='data/sample_rules_cleaned.csv'):
    csv_path = Path(csv_path)
    if not csv_path.exists():
        logging.error(f"CSV file not found: {csv_path}")
        return

    try:
        # Read CSV
        df = pd.read_csv(csv_path)
        logging.info(f"Read {len(df)} rows from {csv_path}")

        # Validate required columns
        required_columns = [
            'avevol', 'yield', 'Dividend_Y10', 'Rev_Growth_Y9',
            'OpeInc_Growth_Y9', 'NetInc_Growth_Y9', 'PE_TTM',
            'PB_TTM', 'PS_TTM', 'PC_TTM'
        ]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logging.error(f"Missing required columns: {missing_columns}")
            return

        # Fill missing values with appropriate defaults
        numeric_defaults = {
            'avevol': 0,
            'yield': 0,
            'Dividend_Y10': 0,
            'Rev_Growth_Y9': 0,
            'OpeInc_Growth_Y9': 0,
            'NetInc_Growth_Y9': 0,
            'PE_TTM': 0,
            'PB_TTM': 0,
            'PS_TTM': 0,
            'PC_TTM': 0
        }

        for col, default in numeric_defaults.items():
            df[col] = df[col].fillna(default)
            # Log if there were any missing values
            if df[col].isna().any():
                logging.warning(f"Column {col} still contains missing values after filling")

        # Standardize formats
        numeric_cols = [
            'openprice', 'yield', 'avevol', 'CAGR_Rev', 'CAGR_OpeInc',
            'CAGR_OpeCF', 'CAGR_FreeCF', 'Dividend_Y10', 'Rev_Growth_Y9',
            'OpeInc_Growth_Y9', 'NetInc_Growth_Y9', 'PE_TTM', 'PB_TTM',
            'PS_TTM', 'PC_TTM'
        ]
        
        # Only round columns that exist
        existing_numeric_cols = [col for col in numeric_cols if col in df.columns]
        df[existing_numeric_cols] = df[existing_numeric_cols].round(2)

        # Validate data ranges
        for col in existing_numeric_cols:
            if df[col].min() < 0 and col not in ['Rev_Growth_Y9', 'OpeInc_Growth_Y9', 'NetInc_Growth_Y9']:
                logging.warning(f"Column {col} contains negative values")
            if df[col].max() > 1e6:
                logging.warning(f"Column {col} contains unusually large values")

        # Save cleaned data
        df.to_csv(output_path, index=False)
        logging.info(f"Cleaned data saved to {output_path}")
        
        # Log summary statistics
        logging.info("Summary of cleaned data:")
        logging.info(f"Total rows: {len(df)}")
        logging.info(f"Columns processed: {len(existing_numeric_cols)}")
        
    except Exception as e:
        logging.error(f"Error during cleaning process: {str(e)}")
        raise

if __name__ == "__main__":
    clean_sample_rules() 