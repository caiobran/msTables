"""
LSTM-based Time Series Predictor

This module implements an advanced LSTM model for financial time series prediction,
featuring:
- Attention mechanism for focusing on important patterns
- GPU acceleration support
- Multi-feature input handling
- Hyperparameter optimization
- Comprehensive training and evaluation tools
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Union
from datetime import datetime
import logging
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import sqlite3

class AttentionLayer(nn.Module):
    """
    Attention mechanism for focusing on important time steps.
    """
    def __init__(self, hidden_dim: int):
        super().__init__()
        self.attention = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, 1)
        )
        
    def forward(self, lstm_output: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        # Calculate attention weights
        attention_weights = self.attention(lstm_output)
        attention_weights = torch.softmax(attention_weights, dim=1)
        
        # Apply attention weights
        context = torch.sum(attention_weights * lstm_output, dim=1)
        
        return context, attention_weights

class LSTMPredictor(nn.Module):
    """
    LSTM model with attention for time series prediction.
    """
    def __init__(self,
                 input_dim: int,
                 hidden_dim: int,
                 num_layers: int,
                 output_dim: int,
                 dropout: float = 0.2,
                 use_attention: bool = True):
        """
        Initialize the LSTM predictor.
        
        Parameters
        ----------
        input_dim : int
            Number of input features
        hidden_dim : int
            Number of hidden units
        num_layers : int
            Number of LSTM layers
        output_dim : int
            Number of output features
        dropout : float
            Dropout rate
        use_attention : bool
            Whether to use attention mechanism
        """
        super().__init__()
        
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.use_attention = use_attention
        
        # LSTM layers
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )
        
        # Attention layer
        if use_attention:
            self.attention = AttentionLayer(hidden_dim)
        
        # Output layer
        self.fc = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, output_dim)
        )
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass through the network.
        
        Parameters
        ----------
        x : torch.Tensor
            Input tensor of shape (batch_size, seq_length, input_dim)
            
        Returns
        -------
        torch.Tensor
            Output tensor of shape (batch_size, output_dim)
        """
        # LSTM forward pass
        lstm_out, _ = self.lstm(x)
        
        if self.use_attention:
            # Apply attention
            context, _ = self.attention(lstm_out)
            return self.fc(context)
        else:
            # Use last hidden state
            return self.fc(lstm_out[:, -1, :])

class TimeSeriesDataset(Dataset):
    """
    Dataset for time series data.
    """
    def __init__(self,
                 data: pd.DataFrame,
                 target_col: str,
                 feature_cols: List[str],
                 seq_length: int,
                 target_length: int = 1):
        """
        Initialize the dataset.
        
        Parameters
        ----------
        data : pd.DataFrame
            Input data
        target_col : str
            Target column name
        feature_cols : List[str]
            Feature column names
        seq_length : int
            Sequence length for input
        target_length : int
            Length of target sequence
        """
        self.data = data
        self.target_col = target_col
        self.feature_cols = feature_cols
        self.seq_length = seq_length
        self.target_length = target_length
        
        # Prepare data
        self.X, self.y = self._prepare_data()
        
    def _prepare_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare input and target sequences."""
        X, y = [], []
        
        for i in range(len(self.data) - self.seq_length - self.target_length + 1):
            # Input sequence
            X.append(self.data[self.feature_cols].iloc[i:i+self.seq_length].values)
            
            # Target sequence
            y.append(self.data[self.target_col].iloc[i+self.seq_length:i+self.seq_length+self.target_length].values)
            
        return np.array(X), np.array(y)
        
    def __len__(self) -> int:
        return len(self.X)
        
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        return torch.FloatTensor(self.X[idx]), torch.FloatTensor(self.y[idx])

class LSTMTrainer:
    """
    Trainer for LSTM model.
    """
    def __init__(self,
                 model: LSTMPredictor,
                 device: str = 'cuda' if torch.cuda.is_available() else 'cpu'):
        """
        Initialize the trainer.
        
        Parameters
        ----------
        model : LSTMPredictor
            LSTM model
        device : str
            Device to use for training
        """
        self.model = model.to(device)
        self.device = device
        self.criterion = nn.MSELoss()
        self.optimizer = optim.Adam(model.parameters())
        self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer,
            mode='min',
            factor=0.5,
            patience=5,
            verbose=True
        )
        
    def train_epoch(self,
                   train_loader: DataLoader) -> float:
        """
        Train for one epoch.
        
        Parameters
        ----------
        train_loader : DataLoader
            Training data loader
            
        Returns
        -------
        float
            Average training loss
        """
        self.model.train()
        total_loss = 0
        
        for X, y in train_loader:
            X, y = X.to(self.device), y.to(self.device)
            
            # Forward pass
            self.optimizer.zero_grad()
            output = self.model(X)
            loss = self.criterion(output, y)
            
            # Backward pass
            loss.backward()
            self.optimizer.step()
            
            total_loss += loss.item()
            
        return total_loss / len(train_loader)
        
    def validate(self,
                val_loader: DataLoader) -> float:
        """
        Validate the model.
        
        Parameters
        ----------
        val_loader : DataLoader
            Validation data loader
            
        Returns
        -------
        float
            Average validation loss
        """
        self.model.eval()
        total_loss = 0
        
        with torch.no_grad():
            for X, y in val_loader:
                X, y = X.to(self.device), y.to(self.device)
                output = self.model(X)
                loss = self.criterion(output, y)
                total_loss += loss.item()
                
        return total_loss / len(val_loader)
        
    def train(self,
             train_loader: DataLoader,
             val_loader: DataLoader,
             num_epochs: int,
             early_stopping_patience: int = 10) -> Dict[str, List[float]]:
        """
        Train the model.
        
        Parameters
        ----------
        train_loader : DataLoader
            Training data loader
        val_loader : DataLoader
            Validation data loader
        num_epochs : int
            Number of epochs
        early_stopping_patience : int
            Patience for early stopping
            
        Returns
        -------
        Dict[str, List[float]]
            Training history
        """
        history = {
            'train_loss': [],
            'val_loss': []
        }
        
        best_val_loss = float('inf')
        patience_counter = 0
        
        for epoch in range(num_epochs):
            # Train
            train_loss = self.train_epoch(train_loader)
            
            # Validate
            val_loss = self.validate(val_loader)
            
            # Update learning rate
            self.scheduler.step(val_loss)
            
            # Early stopping
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                # Save best model
                torch.save(self.model.state_dict(), 'best_model.pth')
            else:
                patience_counter += 1
                if patience_counter >= early_stopping_patience:
                    print(f'Early stopping at epoch {epoch+1}')
                    break
            
            # Record history
            history['train_loss'].append(train_loss)
            history['val_loss'].append(val_loss)
            
            # Print progress
            progress = (epoch + 1) / num_epochs * 100
            print(f'Epoch {epoch+1}/{num_epochs} ({progress:.2f}%):')
            print(f'Train Loss: {train_loss:.6f}')
            print(f'Val Loss: {val_loss:.6f}')
            
        return history
        
    def predict(self,
               data_loader: DataLoader) -> np.ndarray:
        """
        Generate predictions.
        
        Parameters
        ----------
        data_loader : DataLoader
            Data loader for prediction
            
        Returns
        -------
        np.ndarray
            Predictions
        """
        self.model.eval()
        predictions = []
        
        with torch.no_grad():
            for X, _ in data_loader:
                X = X.to(self.device)
                output = self.model(X)
                predictions.append(output.cpu().numpy())
                
        return np.concatenate(predictions)
        
    def plot_training_history(self,
                            history: Dict[str, List[float]],
                            save_path: Optional[str] = None):
        """
        Plot training history.
        
        Parameters
        ----------
        history : Dict[str, List[float]]
            Training history
        save_path : Optional[str]
            Path to save plot
        """
        plt.figure(figsize=(10, 6))
        plt.plot(history['train_loss'], label='Training Loss')
        plt.plot(history['val_loss'], label='Validation Loss')
        plt.title('Training History')
        plt.xlabel('Epoch')
        plt.ylabel('Loss')
        plt.legend()
        plt.grid(True)
        
        if save_path:
            plt.savefig(save_path)
        plt.close()

def prepare_data(data: pd.DataFrame,
                target_col: str,
                feature_cols: List[str],
                seq_length: int,
                target_length: int = 1,
                test_size: float = 0.2,
                val_size: float = 0.2,
                batch_size: int = 32) -> Tuple[DataLoader, DataLoader, DataLoader]:
    """
    Prepare data for training.
    
    Parameters
    ----------
    data : pd.DataFrame
        Input data
    target_col : str
        Target column name
    feature_cols : List[str]
        Feature column names
    seq_length : int
        Sequence length for input
    target_length : int
        Length of target sequence
    test_size : float
        Test set size
    val_size : float
        Validation set size
    batch_size : int
        Batch size
        
    Returns
    -------
    Tuple[DataLoader, DataLoader, DataLoader]
        Train, validation, and test data loaders
    """
    # Debugging: Print the shape of the data
    print(f"Data shape before split: {data.shape}")
    
    # Split data
    train_data, test_data = train_test_split(data, test_size=test_size, shuffle=False)
    train_data, val_data = train_test_split(train_data, test_size=val_size, shuffle=False)
    
    # Debugging: Print the shape of the split data
    print(f"Train data shape: {train_data.shape}")
    print(f"Validation data shape: {val_data.shape}")
    print(f"Test data shape: {test_data.shape}")
    
    # Create datasets
    train_dataset = TimeSeriesDataset(train_data, target_col, feature_cols, seq_length, target_length)
    val_dataset = TimeSeriesDataset(val_data, target_col, feature_cols, seq_length, target_length)
    test_dataset = TimeSeriesDataset(test_data, target_col, feature_cols, seq_length, target_length)
    
    # Create data loaders
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size)
    test_loader = DataLoader(test_dataset, batch_size=batch_size)
    
    return train_loader, val_loader, test_loader

def track_results(combination, results):
    """
    Track and store the results of different combinations of strategies in the mstables.sqlite database.
    
    Parameters
    ----------
    combination : str
        Description of the combination of strategies used.
    results : dict
        Dictionary containing the results of the combination.
    """
    conn = sqlite3.connect('data/mstables.sqlite')
    cursor = conn.cursor()
    
    # Create a table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS strategy_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        combination TEXT,
        results TEXT
    )
    ''')
    
    # Insert the results
    cursor.execute('INSERT INTO strategy_results (combination, results) VALUES (?, ?)',
                   (combination, str(results)))
    
    conn.commit()
    conn.close()

def prepare_stock_data(stock_data, sp500_data):
    """
    Prepare data for training a model that compares every stock against every other stock and against the S&P 500.
    
    Parameters
    ----------
    stock_data : pd.DataFrame
        DataFrame containing stock data.
    sp500_data : pd.DataFrame
        DataFrame containing S&P 500 data.
        
    Returns
    -------
    pd.DataFrame
        Prepared data for training.
    """
    # Ensure the data is aligned by date
    stock_data = stock_data.set_index('date')
    sp500_data = sp500_data.set_index('date')
    
    # Calculate returns for each stock and the S&P 500
    stock_returns = stock_data.pct_change().dropna()
    sp500_returns = sp500_data.pct_change().dropna()
    
    # Create a DataFrame to store the comparison data
    comparison_data = pd.DataFrame()
    
    # Compare each stock against every other stock
    for stock1 in stock_returns.columns:
        for stock2 in stock_returns.columns:
            if stock1 != stock2:
                comparison_data[f'{stock1}_vs_{stock2}'] = stock_returns[stock1] - stock_returns[stock2]
    
    # Compare each stock against the S&P 500
    for stock in stock_returns.columns:
        comparison_data[f'{stock}_vs_SP500'] = stock_returns[stock] - sp500_returns['SP500']
    
    return comparison_data

def load_data_from_db():
    """
    Load stock and S&P 500 data from the mstables.sqlite database.
    If the tables do not exist, create them with sample data.
    
    Returns
    -------
    pd.DataFrame, pd.DataFrame
        Stock data and S&P 500 data.
    """
    conn = sqlite3.connect('data/mstables.sqlite')
    cursor = conn.cursor()
    
    # Check if the tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stock_data'")
    if cursor.fetchone() is None:
        # Create stock_data table with sample data
        cursor.execute('''
        CREATE TABLE stock_data (
            date TEXT,
            AAPL REAL,
            MSFT REAL,
            GOOGL REAL
        )
        ''')
        # Insert sample data
        sample_data = [
            ('2020-01-01', 100.0, 200.0, 300.0),
            ('2020-01-02', 101.0, 201.0, 301.0),
            ('2020-01-03', 102.0, 202.0, 302.0),
            ('2020-01-04', 103.0, 203.0, 303.0),
            ('2020-01-05', 104.0, 204.0, 304.0),
            ('2020-01-06', 105.0, 205.0, 305.0),
            ('2020-01-07', 106.0, 206.0, 306.0),
            ('2020-01-08', 107.0, 207.0, 307.0),
            ('2020-01-09', 108.0, 208.0, 308.0),
            ('2020-01-10', 109.0, 209.0, 309.0)
        ]
        cursor.executemany('INSERT INTO stock_data VALUES (?, ?, ?, ?)', sample_data)
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sp500_data'")
    if cursor.fetchone() is None:
        # Create sp500_data table with sample data
        cursor.execute('''
        CREATE TABLE sp500_data (
            date TEXT,
            SP500 REAL
        )
        ''')
        # Insert sample data
        sample_data = [
            ('2020-01-01', 3000.0),
            ('2020-01-02', 3010.0),
            ('2020-01-03', 3020.0),
            ('2020-01-04', 3030.0),
            ('2020-01-05', 3040.0),
            ('2020-01-06', 3050.0),
            ('2020-01-07', 3060.0),
            ('2020-01-08', 3070.0),
            ('2020-01-09', 3080.0),
            ('2020-01-10', 3090.0)
        ]
        cursor.executemany('INSERT INTO sp500_data VALUES (?, ?)', sample_data)
    
    conn.commit()
    
    # Load stock data
    stock_data = pd.read_sql_query("SELECT * FROM stock_data", conn)
    
    # Load S&P 500 data
    sp500_data = pd.read_sql_query("SELECT * FROM sp500_data", conn)
    
    conn.close()
    
    return stock_data, sp500_data

def augment_data(data, method='gaussian_noise', **kwargs):
    """
    Apply data augmentation techniques to the input data.
    
    Parameters
    ----------
    data : pd.DataFrame
        Input data to augment.
    method : str
        Augmentation method to apply.
    **kwargs : dict
        Additional parameters for the augmentation method.
        
    Returns
    -------
    pd.DataFrame
        Augmented data.
    """
    if method == 'gaussian_noise':
        noise_level = kwargs.get('noise_level', 0.01)
        return data + np.random.normal(0, noise_level, data.shape)
    elif method == 'scaling':
        scale_factor = kwargs.get('scale_factor', 1.1)
        return data * scale_factor
    elif method == 'time_warping':
        # Implement time warping logic here
        pass
    elif method == 'jittering':
        # Implement jittering logic here
        pass
    elif method == 'synthetic':
        # Implement synthetic data generation logic here
        pass
    else:
        raise ValueError(f"Unknown augmentation method: {method}")

def engineer_features(data, method='technical_indicators', **kwargs):
    """
    Apply feature engineering techniques to the input data.
    
    Parameters
    ----------
    data : pd.DataFrame
        Input data to engineer features from.
    method : str
        Feature engineering method to apply.
    **kwargs : dict
        Additional parameters for the feature engineering method.
        
    Returns
    -------
    pd.DataFrame
        Data with engineered features.
    """
    if method == 'technical_indicators':
        # Example: Calculate moving averages
        for col in data.columns:
            data[f'{col}_MA5'] = data[col].rolling(window=5).mean()
            data[f'{col}_MA10'] = data[col].rolling(window=10).mean()
        return data
    elif method == 'sentiment_analysis':
        # Implement sentiment analysis logic here
        pass
    elif method == 'cross_asset_features':
        # Implement cross-asset features logic here
        pass
    elif method == 'time_frames':
        # Implement time frames logic here
        pass
    elif method == 'feature_combination':
        # Implement feature combination logic here
        pass
    else:
        raise ValueError(f"Unknown feature engineering method: {method}")

def main():
    """Example usage of the LSTM predictor."""
    # Set random seed
    torch.manual_seed(42)
    np.random.seed(42)
    
    # Load data from the database
    stock_data, sp500_data = load_data_from_db()
    
    # Prepare data for training
    comparison_data = prepare_stock_data(stock_data, sp500_data)
    
    # Apply data augmentation
    augmented_data = augment_data(comparison_data, method='gaussian_noise', noise_level=0.01)
    
    # Apply feature engineering
    engineered_data = engineer_features(augmented_data, method='technical_indicators')
    
    # Prepare data for the model
    target_col = 'AAPL_vs_MSFT'  # Example target column
    feature_cols = [col for col in engineered_data.columns if col != target_col]
    seq_length = 10
    target_length = 1
    
    train_loader, val_loader, test_loader = prepare_data(
        data=engineered_data,
        target_col=target_col,
        feature_cols=feature_cols,
        seq_length=seq_length,
        target_length=target_length
    )
    
    # Create model
    model = LSTMPredictor(
        input_dim=len(feature_cols),
        hidden_dim=64,
        num_layers=2,
        output_dim=target_length,
        dropout=0.2,
        use_attention=True
    )
    
    # Create trainer
    trainer = LSTMTrainer(model)
    
    # Train model
    history = trainer.train(
        train_loader=train_loader,
        val_loader=val_loader,
        num_epochs=5000,
        early_stopping_patience=10
    )
    
    # Plot training history
    trainer.plot_training_history(
        history=history,
        save_path='training_history.png'
    )
    
    # Generate predictions
    predictions = trainer.predict(test_loader)
    
    # Plot predictions
    plt.figure(figsize=(12, 6))
    plt.plot(comparison_data.index[-len(predictions):], comparison_data[target_col].iloc[-len(predictions):], label='Actual')
    plt.plot(comparison_data.index[-len(predictions):], predictions, label='Predicted')
    plt.title('LSTM Predictions')
    plt.xlabel('Date')
    plt.ylabel('Return')
    plt.legend()
    plt.grid(True)
    plt.savefig('predictions.png')
    plt.close()

    # Example of tracking results
    combination = "Cross-Training with Stocks and Cryptocurrencies"
    results = {
        'train_loss': history['train_loss'][-1],
        'val_loss': history['val_loss'][-1]
    }
    track_results(combination, results)

if __name__ == "__main__":
    main() 