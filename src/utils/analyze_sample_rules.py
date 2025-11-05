import pandas as pd
import sqlite3
import logging
import matplotlib.pyplot as plt
import seaborn as sns

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('analyze_sample_rules.log'),
        logging.StreamHandler()
    ]
)

def analyze_sample_rules(db_path='data/mstables.sqlite'):
    # Read data from database
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query("SELECT * FROM sample_rules", conn)
    logging.info(f"Read {len(df)} rows from sample_rules")

    # Compare average PE_TTM and CAGR_Rev across sectors
    sector_metrics = df.groupby('sector').agg({
        'PE_TTM': 'mean',
        'CAGR_Rev': 'mean'
    }).round(2)
    logging.info("Average PE_TTM and CAGR_Rev by sector:")
    logging.info(sector_metrics)

    # Identify top-performing companies in a specific industry (e.g., Technology) based on CAGR_Rev
    industry = 'Technology'
    top_companies = df[df['sector'] == industry].sort_values('CAGR_Rev', ascending=False).head(5)
    logging.info(f"Top 5 companies in {industry} by CAGR_Rev:")
    logging.info(top_companies[['company', 'CAGR_Rev']])

    # Analyze distribution of yield and Dividend_Y10 across sectors
    plt.figure(figsize=(12, 6))
    sns.boxplot(x='sector', y='yield', data=df)
    plt.title('Distribution of Yield by Sector')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('yield_by_sector.png')
    logging.info("Yield distribution plot saved as yield_by_sector.png")

    plt.figure(figsize=(12, 6))
    sns.boxplot(x='sector', y='Dividend_Y10', data=df)
    plt.title('Distribution of Dividend_Y10 by Sector')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('dividend_y10_by_sector.png')
    logging.info("Dividend_Y10 distribution plot saved as dividend_y10_by_sector.png")

if __name__ == "__main__":
    analyze_sample_rules() 