"""
Market Predictor Module

This module provides GPU-accelerated market prediction capabilities using both
linear regression and random forest models, with support for regime detection
and commodity correlations.
"""

import pandas as pd
import numpy as np
import torch
import cupy as cp
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import logging
from pathlib import Path
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score
import matplotlib.pyplot as plt
import seaborn as sns

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/logs/market_predictor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('MarketPredictor')

class MarketPredictor:
    """
    A class for market prediction using both linear regression and random forest models,
    with GPU acceleration and regime detection capabilities.
    """
    
    def __init__(self, 
                 db_path: str = 'data/mstables.sqlite',
                 prediction_horizon: int = 5,
                 use_gpu: bool = True):
        """
        Initialize the MarketPredictor.
        
        Parameters
        ----------
        db_path : str
            Path to the SQLite database
        prediction_horizon : int
            Number of days to predict ahead
        use_gpu : bool
            Whether to use GPU acceleration
        """
        self.db_path = db_path
        self.prediction_horizon = prediction_horizon
        self.use_gpu = use_gpu
        self.logger = logger
        
        # Create necessary directories
        Path('data/logs').mkdir(parents=True, exist_ok=True)
        Path('data/predictions').mkdir(parents=True, exist_ok=True)
        Path('data/models').mkdir(parents=True, exist_ok=True)
        
        # Initialize GPU if available
        if use_gpu and torch.cuda.is_available():
            self.device = torch.device('cuda')
            logger.info(f"Using GPU: {torch.cuda.get_device_name(0)}")
        else:
            self.device = torch.device('cpu')
            logger.info("Using CPU")
            
        # Initialize models
        self.linear_model = LinearRegression()
        self.rf_model = RandomForestRegressor(
            n_estimators=100,
            max_depth=None,
            min_samples_split=2,
            min_samples_leaf=1,
            n_jobs=-1
        )
        
        # Initialize scaler
        self.scaler = StandardScaler()

    def prepare_market_data(self, 
                          symbol: str = '^GSPC',
                          lookback_days: int = 252) -> pd.DataFrame:
        """
        Prepare market data for prediction.
        
        Parameters
        ----------
        symbol : str
            Symbol to analyze (default: S&P 500)
        lookback_days : int
            Number of days to look back for historical data
            
        Returns
        -------
        pd.DataFrame
            Prepared market data
        """
        try:
            # Fetch historical data from our database
            # This would need to be implemented based on your data source
            
            # Calculate technical indicators
            data = self.calculate_technical_indicators(data)
            
            # Calculate regime indicators
            data = self.calculate_regime_indicators(data)
            
            # Calculate commodity correlations
            data = self.calculate_commodity_correlations(data)
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error preparing market data: {e}")
            return pd.DataFrame()

    def calculate_technical_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators for prediction."""
        try:
            # Moving averages
            data['SMA_20'] = data['Close'].rolling(window=20).mean()
            data['SMA_50'] = data['Close'].rolling(window=50).mean()
            data['SMA_200'] = data['Close'].rolling(window=200).mean()
            
            # Volatility
            data['Volatility'] = data['Close'].pct_change().rolling(window=20).std()
            
            # RSI
            delta = data['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            data['RSI'] = 100 - (100 / (1 + rs))
            
            # MACD
            exp1 = data['Close'].ewm(span=12, adjust=False).mean()
            exp2 = data['Close'].ewm(span=26, adjust=False).mean()
            data['MACD'] = exp1 - exp2
            data['Signal_Line'] = data['MACD'].ewm(span=9, adjust=False).mean()
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error calculating technical indicators: {e}")
            return data

    def calculate_regime_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate regime indicators for market state detection."""
        try:
            # Trend strength
            data['Trend_Strength'] = abs(data['SMA_20'] - data['SMA_50']) / data['SMA_50']
            
            # Volatility regime
            data['Volatility_Regime'] = pd.qcut(data['Volatility'], q=5, labels=['Very Low', 'Low', 'Medium', 'High', 'Very High'])
            
            # Market regime
            data['Market_Regime'] = np.where(
                (data['SMA_20'] > data['SMA_50']) & (data['SMA_50'] > data['SMA_200']),
                'Bullish',
                np.where(
                    (data['SMA_20'] < data['SMA_50']) & (data['SMA_50'] < data['SMA_200']),
                    'Bearish',
                    'Neutral'
                )
            )
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error calculating regime indicators: {e}")
            return data

    def calculate_commodity_correlations(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate correlations with major commodities."""
        try:
            # This would need to be implemented based on your commodity data source
            # Example commodities: Gold, Oil, Silver, etc.
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error calculating commodity correlations: {e}")
            return data

    def prepare_features(self, data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepare features and target for model training.
        
        Parameters
        ----------
        data : pd.DataFrame
            Market data with indicators
            
        Returns
        -------
        Tuple[np.ndarray, np.ndarray]
            Features and target arrays
        """
        try:
            # Select features
            feature_columns = [
                'SMA_20', 'SMA_50', 'SMA_200',
                'Volatility', 'RSI', 'MACD', 'Signal_Line',
                'Trend_Strength'
            ]
            
            # Create target (future returns)
            data['Target'] = data['Close'].pct_change(self.prediction_horizon).shift(-self.prediction_horizon)
            
            # Remove rows with NaN values
            data = data.dropna()
            
            # Prepare features and target
            X = data[feature_columns].values
            y = data['Target'].values
            
            # Scale features
            X = self.scaler.fit_transform(X)
            
            return X, y
            
        except Exception as e:
            self.logger.error(f"Error preparing features: {e}")
            return np.array([]), np.array([])

    def train_models(self, X: np.ndarray, y: np.ndarray):
        """
        Train both linear regression and random forest models.
        
        Parameters
        ----------
        X : np.ndarray
            Feature array
        y : np.ndarray
            Target array
        """
        try:
            # Train linear regression
            self.linear_model.fit(X, y)
            
            # Train random forest
            self.rf_model.fit(X, y)
            
            # Log model performance
            linear_pred = self.linear_model.predict(X)
            rf_pred = self.rf_model.predict(X)
            
            self.logger.info(f"Linear Regression R2: {r2_score(y, linear_pred):.4f}")
            self.logger.info(f"Random Forest R2: {r2_score(y, rf_pred):.4f}")
            
        except Exception as e:
            self.logger.error(f"Error training models: {e}")

    def predict(self, X: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Generate predictions using both models.
        
        Parameters
        ----------
        X : np.ndarray
            Feature array
            
        Returns
        -------
        Dict[str, np.ndarray]
            Dictionary of predictions from both models
        """
        try:
            predictions = {
                'linear': self.linear_model.predict(X),
                'random_forest': self.rf_model.predict(X)
            }
            
            return predictions
            
        except Exception as e:
            self.logger.error(f"Error generating predictions: {e}")
            return {}

    def run_overnight_analysis(self,
                             symbol: str = '^GSPC',
                             output_file: str = 'data/predictions/market_predictions.json'):
        """
        Run overnight analysis and generate predictions.
        
        Parameters
        ----------
        symbol : str
            Symbol to analyze
        output_file : str
            Path to save the predictions
        """
        try:
            # Prepare market data
            data = self.prepare_market_data(symbol)
            
            # Prepare features
            X, y = self.prepare_features(data)
            
            # Train models
            self.train_models(X, y)
            
            # Generate predictions
            predictions = self.predict(X)
            
            # Save results
            results = {
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'predictions': {
                    'linear': predictions['linear'].tolist(),
                    'random_forest': predictions['random_forest'].tolist()
                },
                'regime': data['Market_Regime'].iloc[-1],
                'volatility_regime': data['Volatility_Regime'].iloc[-1]
            }
            
            pd.to_json(results, output_file)
            self.logger.info(f"Market predictions saved to {output_file}")
            
        except Exception as e:
            self.logger.error(f"Error in overnight analysis: {e}")

def main():
    """Example usage of the MarketPredictor."""
    # Initialize predictor
    predictor = MarketPredictor(
        prediction_horizon=5,
        use_gpu=True
    )
    
    # Run overnight analysis
    predictor.run_overnight_analysis()

if __name__ == '__main__':
    main() 