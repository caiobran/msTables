import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

def correlate_stock_crypto(stock_data, crypto_data):
    """
    Perform a simple linear regression to find correlations between stock and crypto data.
    
    Parameters:
    -----------
    stock_data : pd.DataFrame
        DataFrame containing stock data with a 'close' column.
    crypto_data : pd.DataFrame
        DataFrame containing crypto data with a 'close' column.
    
    Returns:
    --------
    dict
        Dictionary containing regression results including slope, intercept, and R² score.
    """
    # Ensure both datasets have the same index (date)
    stock_data = stock_data.set_index('date')
    crypto_data = crypto_data.set_index('date')
    
    # Align the data
    common_dates = stock_data.index.intersection(crypto_data.index)
    stock_aligned = stock_data.loc[common_dates, 'close']
    crypto_aligned = crypto_data.loc[common_dates, 'close']
    
    # Reshape for sklearn
    X = stock_aligned.values.reshape(-1, 1)
    y = crypto_aligned.values
    
    # Fit the model
    model = LinearRegression()
    model.fit(X, y)
    
    # Predict
    y_pred = model.predict(X)
    
    # Calculate R²
    r2 = r2_score(y, y_pred)
    
    return {
        'slope': model.coef_[0],
        'intercept': model.intercept_,
        'r2_score': r2
    } 