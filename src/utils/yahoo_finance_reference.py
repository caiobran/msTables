"""
Yahoo Finance Reference Information

This module contains reference information about Yahoo Finance data sources,
exchange suffixes, and data providers. This information is useful for
understanding data availability and delays when working with Yahoo Finance data.

Source: https://help.yahoo.com/kb/SLN2310.html
Last Updated: 2024
"""

# Data Provider Information
DATA_PROVIDERS = {
    'financial_statements': 'Morningstar',
    'valuation_ratios': 'Morningstar',
    'market_cap': 'Morningstar',
    'shares_outstanding': 'Morningstar',
    'company_profile': 'S&P Global Market Intelligence',
    'us_equities': 'Commodity Systems, Inc.',
    'global_index': 'Commodity Systems, Inc.',
    'international_charts': 'Morningstar',
    'analyst_estimates': 'Refinitiv',
    'earnings': 'Refinitiv',
    'corporate_events': 'Refinitiv',
    'economic_events': 'Refinitiv',
    'non_us_ipo': 'Refinitiv',
    'insider_transactions': 'Refinitiv',
    'institutional_holders': 'Vickers-stock.com',
    'mutual_fund_holders': 'Vickers-stock.com',
    'sec_filings': 'EDGAR Online (Donnelley Financial LLC)',
    'us_ipo': 'EDGAR Online (Donnelley Financial LLC)',
    'sustainability': 'Sustainalytics and Morningstar',
    'upgrades_downgrades': 'Benzinga',
    'corporate_governance': 'Institutional Shareholder Services'
}

# Exchange Information
# Format: (country, market, suffix, delay, provider)
EXCHANGES = [
    # United States
    ('United States', 'Chicago Board of Trade (CBOT)', '.CBT', '10 min', 'ICE Data Services'),
    ('United States', 'Chicago Mercantile Exchange (CME)', '.CME', '10 min', 'ICE Data Services'),
    ('United States', 'Dow Jones Indexes', 'N/A', 'Real-time', 'ICE Data Services'),
    ('United States', 'Nasdaq Stock Exchange', 'N/A', 'Real-time', 'ICE Data Services'),
    ('United States', 'ICE Futures US', '.NYB', '30 min', 'ICE Data Services'),
    ('United States', 'New York Commodities Exchange (COMEX)', '.CMX', '30 min', 'ICE Data Services'),
    ('United States', 'New York Mercantile Exchange (NYMEX)', '.NYM', '30 min', 'ICE Data Services'),
    ('United States', 'Options Price Reporting Authority (OPRA)', 'N/A', '15 min', 'ICE Data Services'),
    ('United States', 'OTC Bulletin Board Market', 'N/A', 'Real-time', 'ICE Data Services'),
    ('United States', 'OTC Markets Group', 'N/A', '15 min', 'ICE Data Services'),
    ('United States', 'S & P Indices', 'N/A', 'Real-time', 'ICE Data Services'),
    
    # Major International Exchanges
    ('Canada', 'Toronto Stock Exchange (TSX)', '.TO', 'Real-time', 'ICE Data Services'),
    ('United Kingdom', 'London Stock Exchange', '.L', '20 min', 'ICE Data Services'),
    ('Japan', 'Tokyo Stock Exchange', '.T', '20 min', 'ICE Data Services'),
    ('Hong Kong', 'Hong Kong Stock Exchange (HKEX)', '.HK', '15 min', 'ICE Data Services'),
    ('China', 'Shanghai Stock Exchange', '.SS', '30 min', 'ICE Data Services'),
    ('China', 'Shenzhen Stock Exchange', '.SZ', '30 min', 'ICE Data Services'),
    ('Germany', 'Deutsche Boerse XETRA', '.DE', '15 min', 'ICE Data Services'),
    ('France', 'Euronext Paris', '.PA', '15 min', 'ICE Data Services'),
    ('India', 'National Stock Exchange of India', '.NS', 'Real-time', 'ICE Data Services'),
    ('Australia', 'Australian Stock Exchange (ASX)', '.AX', '20 min', 'ICE Data Services')
]

def get_exchange_suffix(exchange_name: str) -> str:
    """
    Get the Yahoo Finance suffix for a given exchange name.
    
    Args:
        exchange_name (str): Name of the exchange
        
    Returns:
        str: The corresponding suffix for the exchange, or None if not found
    """
    for _, market, suffix, _, _ in EXCHANGES:
        if market.lower() == exchange_name.lower():
            return suffix
    return None

def get_data_provider(data_type: str) -> str:
    """
    Get the data provider for a specific type of data.
    
    Args:
        data_type (str): Type of data (e.g., 'financial_statements', 'company_profile')
        
    Returns:
        str: The data provider name, or None if not found
    """
    return DATA_PROVIDERS.get(data_type)

def get_exchange_info(country: str = None) -> list:
    """
    Get information about exchanges, optionally filtered by country.
    
    Args:
        country (str, optional): Filter exchanges by country
        
    Returns:
        list: List of exchange information tuples
    """
    if country:
        return [e for e in EXCHANGES if e[0].lower() == country.lower()]
    return EXCHANGES 