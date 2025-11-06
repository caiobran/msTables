import pandas as pd
import json
import logging
from pathlib import Path
import sys
import shutil

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pot_stocks_clean.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

class PotStocksCleaner:
    def __init__(self,
                 source_file: str = 'doc/pot_stocks.ods',
                 target_dir: str = 'input/data'):
        self.source_file = Path(source_file)
        self.target_dir = Path(target_dir)
        
    def clean_sym_column(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean the Sym column by extracting the ticker symbol"""
        def extract_ticker(sym_str):
            try:
                # Remove brackets and split by comma
                sym_str = sym_str.strip('[]').split(',')[0]
                # Remove quotes and spaces
                return sym_str.strip().strip('"')
            except:
                return None
                
        df['ticker'] = df['Sym'].apply(extract_ticker)
        return df
        
    def clean_market_cap(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert market cap to a more readable format"""
        df['market_cap'] = df['Market Cap'].apply(
            lambda x: f"${x:,.2f}" if pd.notnull(x) else None
        )
        return df
        
    def clean_percentage(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean percentage columns"""
        def clean_percent(x):
            if pd.isnull(x):
                return None
            try:
                # Remove % and convert to float
                if isinstance(x, str):
                    x = x.strip('%')
                return f"{float(x):.2f}%"
            except:
                return None
                
        for col in ['%Chg']:
            if col in df.columns:
                df[col] = df[col].apply(clean_percent)
        return df
        
    def clean_volume(self, df: pd.DataFrame) -> pd.DataFrame:
        """Format volume numbers"""
        df['volume'] = df['Share Volume'].apply(
            lambda x: f"{int(x):,}" if pd.notnull(x) else None
        )
        return df
        
    def process_data(self) -> pd.DataFrame:
        """Read and clean the data"""
        try:
            # Read the ODS file
            df = pd.read_excel(self.source_file, engine='odf')
            logging.info(f"Read {len(df)} rows from {self.source_file}")
            
            # Clean the data
            df = self.clean_sym_column(df)
            df = self.clean_market_cap(df)
            df = self.clean_percentage(df)
            df = self.clean_volume(df)
            
            # Select and rename columns
            columns = {
                'Symbol': 'symbol',
                'Country': 'country',
                'Company': 'company',
                'Last': 'last_price',
                'Chg': 'change',
                '%Chg': 'percent_change',
                'ticker': 'ticker',
                'volume': 'volume',
                'market_cap': 'market_cap'
            }
            
            df = df[columns.keys()].rename(columns=columns)
            
            # Remove rows with no ticker
            df = df.dropna(subset=['ticker'])
            logging.info(f"Cleaned data: {len(df)} rows remaining")
            
            return df
            
        except Exception as e:
            logging.error(f"Error processing data: {str(e)}")
            raise
            
    def save_data(self, df: pd.DataFrame) -> None:
        """Save the cleaned data to CSV"""
        try:
            # Create target directory if it doesn't exist
            self.target_dir.mkdir(parents=True, exist_ok=True)
            
            # Save as CSV
            output_file = self.target_dir / 'pot_stocks.csv'
            df.to_csv(output_file, index=False)
            logging.info(f"Saved cleaned data to {output_file}")
            
            # Create backup of original
            backup_file = self.target_dir / 'pot_stocks.ods'
            shutil.copy2(self.source_file, backup_file)
            logging.info(f"Created backup of original at {backup_file}")
            
        except Exception as e:
            logging.error(f"Error saving data: {str(e)}")
            raise
            
    def run(self) -> None:
        """Run the cleaning process"""
        try:
            df = self.process_data()
            self.save_data(df)
            logging.info("Successfully cleaned and saved pot_stocks data")
        except Exception as e:
            logging.error(f"Process failed: {str(e)}")
            raise

if __name__ == "__main__":
    cleaner = PotStocksCleaner()
    cleaner.run() 