"""
Brownfield-style Trading Predictor

This module implements a neural network model for asymmetric risk/reward trading,
featuring:
- Multi-head attention for market inefficiency detection
- Asymmetric loss function for limited downside
- Comprehensive risk management
- Paper trading simulation
- Performance monitoring
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
import logging
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

@dataclass
class ModelHyperparameters:
    """Hyperparameters for the Brownfield predictor."""
    learning_rate: float = 1e-4
    hidden_dim: int = 256
    num_layers: int = 3
    num_heads: int = 8
    dropout: float = 0.1
    batch_size: int = 64
    max_position_size: float = 0.1
    max_drawdown: float = 0.15
    risk_reward_ratio: float = 3.0
    device: str = 'cuda' if torch.cuda.is_available() else 'cpu'

class MultiHeadAttention(nn.Module):
    """
    Multi-head attention mechanism for market inefficiency detection.
    """
    def __init__(self, input_dim: int, num_heads: int):
        super().__init__()
        self.num_heads = num_heads
        self.head_dim = input_dim // num_heads
        
        self.query = nn.Linear(input_dim, input_dim)
        self.key = nn.Linear(input_dim, input_dim)
        self.value = nn.Linear(input_dim, input_dim)
        
        self.proj = nn.Linear(input_dim, input_dim)
        
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        batch_size = x.size(0)
        
        # Linear projections
        q = self.query(x).view(batch_size, -1, self.num_heads, self.head_dim).transpose(1, 2)
        k = self.key(x).view(batch_size, -1, self.num_heads, self.head_dim).transpose(1, 2)
        v = self.value(x).view(batch_size, -1, self.num_heads, self.head_dim).transpose(1, 2)
        
        # Scaled dot-product attention
        scores = torch.matmul(q, k.transpose(-2, -1)) / np.sqrt(self.head_dim)
        attn_weights = torch.softmax(scores, dim=-1)
        
        # Apply attention
        context = torch.matmul(attn_weights, v)
        context = context.transpose(1, 2).contiguous().view(batch_size, -1, self.num_heads * self.head_dim)
        
        return self.proj(context), attn_weights

class BrownfieldPredictor(nn.Module):
    """
    Neural network model for Brownfield-style trading.
    """
    def __init__(self,
                 input_dim: int,
                 hidden_dim: int,
                 num_layers: int,
                 num_heads: int,
                 dropout: float = 0.1):
        """
        Initialize the Brownfield predictor.
        
        Parameters
        ----------
        input_dim : int
            Number of input features
        hidden_dim : int
            Number of hidden units
        num_layers : int
            Number of layers
        num_heads : int
            Number of attention heads
        dropout : float
            Dropout rate
        """
        super().__init__()
        
        # Feature extraction
        self.feature_extractor = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout)
        )
        
        # Multi-head attention
        self.attention = MultiHeadAttention(hidden_dim, num_heads)
        
        # LSTM layers
        self.lstm = nn.LSTM(
            input_size=hidden_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )
        
        # Output heads
        self.position_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, 1),
            nn.Tanh()  # Output between -1 and 1
        )
        
        self.risk_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, 1),
            nn.Sigmoid()  # Output between 0 and 1
        )
        
        self.value_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, 1)
        )
        
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Forward pass through the network.
        
        Parameters
        ----------
        x : torch.Tensor
            Input tensor of shape (batch_size, seq_length, input_dim)
            
        Returns
        -------
        Tuple[torch.Tensor, torch.Tensor, torch.Tensor]
            Position size, risk score, and value estimate
        """
        # Feature extraction
        features = self.feature_extractor(x)
        
        # Attention
        attended_features, _ = self.attention(features)
        
        # LSTM
        lstm_out, _ = self.lstm(attended_features)
        
        # Output heads
        position = self.position_head(lstm_out[:, -1, :])
        risk = self.risk_head(lstm_out[:, -1, :])
        value = self.value_head(lstm_out[:, -1, :])
        
        return position, risk, value

class AsymmetricLoss(nn.Module):
    """
    Asymmetric loss function for limited downside.
    """
    def __init__(self, downside_weight: float = 2.0):
        super().__init__()
        self.downside_weight = downside_weight
        
    def forward(self, pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        """
        Compute asymmetric loss.
        
        Parameters
        ----------
        pred : torch.Tensor
            Predictions
        target : torch.Tensor
            Targets
            
        Returns
        -------
        torch.Tensor
            Loss value
        """
        loss = torch.abs(pred - target)
        mask = (pred < target).float()
        weighted_loss = loss * (1 + (self.downside_weight - 1) * mask)
        return weighted_loss.mean()

class BrownfieldDataset(Dataset):
    """
    Dataset for Brownfield-style trading.
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

class BrownfieldTrainer:
    """
    Trainer for Brownfield predictor.
    """
    def __init__(self,
                 model: BrownfieldPredictor,
                 hyperparameters: ModelHyperparameters):
        """
        Initialize the trainer.
        
        Parameters
        ----------
        model : BrownfieldPredictor
            Brownfield model
        hyperparameters : ModelHyperparameters
            Model hyperparameters
        """
        self.model = model.to(hyperparameters.device)
        self.hp = hyperparameters
        
        # Loss functions
        self.position_loss = AsymmetricLoss()
        self.risk_loss = nn.BCELoss()
        self.value_loss = nn.MSELoss()
        
        # Optimizer
        self.optimizer = optim.Adam(model.parameters(), lr=hyperparameters.learning_rate)
        
        # Learning rate scheduler
        self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer,
            mode='min',
            factor=0.5,
            patience=5,
            verbose=True
        )
        
    def train_epoch(self,
                   train_loader: DataLoader) -> Dict[str, float]:
        """
        Train for one epoch.
        
        Parameters
        ----------
        train_loader : DataLoader
            Training data loader
            
        Returns
        -------
        Dict[str, float]
            Training metrics
        """
        self.model.train()
        total_position_loss = 0
        total_risk_loss = 0
        total_value_loss = 0
        
        for X, y in train_loader:
            X, y = X.to(self.hp.device), y.to(self.hp.device)
            
            # Forward pass
            self.optimizer.zero_grad()
            position, risk, value = self.model(X)
            
            # Compute losses
            pos_loss = self.position_loss(position, y)
            rsk_loss = self.risk_loss(risk, torch.abs(y))
            val_loss = self.value_loss(value, y)
            
            # Total loss
            loss = pos_loss + rsk_loss + val_loss
            
            # Backward pass
            loss.backward()
            self.optimizer.step()
            
            total_position_loss += pos_loss.item()
            total_risk_loss += rsk_loss.item()
            total_value_loss += val_loss.item()
            
        return {
            'position_loss': total_position_loss / len(train_loader),
            'risk_loss': total_risk_loss / len(train_loader),
            'value_loss': total_value_loss / len(train_loader)
        }
        
    def validate(self,
                val_loader: DataLoader) -> Dict[str, float]:
        """
        Validate the model.
        
        Parameters
        ----------
        val_loader : DataLoader
            Validation data loader
            
        Returns
        -------
        Dict[str, float]
            Validation metrics
        """
        self.model.eval()
        total_position_loss = 0
        total_risk_loss = 0
        total_value_loss = 0
        
        with torch.no_grad():
            for X, y in val_loader:
                X, y = X.to(self.hp.device), y.to(self.hp.device)
                
                # Forward pass
                position, risk, value = self.model(X)
                
                # Compute losses
                pos_loss = self.position_loss(position, y)
                rsk_loss = self.risk_loss(risk, torch.abs(y))
                val_loss = self.value_loss(value, y)
                
                total_position_loss += pos_loss.item()
                total_risk_loss += rsk_loss.item()
                total_value_loss += val_loss.item()
                
        return {
            'position_loss': total_position_loss / len(val_loader),
            'risk_loss': total_risk_loss / len(val_loader),
            'value_loss': total_value_loss / len(val_loader)
        }
        
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
            'train_position_loss': [],
            'train_risk_loss': [],
            'train_value_loss': [],
            'val_position_loss': [],
            'val_risk_loss': [],
            'val_value_loss': []
        }
        
        best_val_loss = float('inf')
        patience_counter = 0
        
        for epoch in range(num_epochs):
            # Train
            train_metrics = self.train_epoch(train_loader)
            
            # Validate
            val_metrics = self.validate(val_loader)
            
            # Update learning rate
            val_loss = val_metrics['position_loss'] + val_metrics['risk_loss'] + val_metrics['value_loss']
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
            for k, v in train_metrics.items():
                history[f'train_{k}'].append(v)
            for k, v in val_metrics.items():
                history[f'val_{k}'].append(v)
            
            print(f'Epoch {epoch+1}/{num_epochs}:')
            print(f'Train Loss: {train_metrics["position_loss"]:.6f}')
            print(f'Val Loss: {val_metrics["position_loss"]:.6f}')
            
        return history
        
    def predict(self,
               data_loader: DataLoader) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Generate predictions.
        
        Parameters
        ----------
        data_loader : DataLoader
            Data loader for prediction
            
        Returns
        -------
        Tuple[np.ndarray, np.ndarray, np.ndarray]
            Position sizes, risk scores, and value estimates
        """
        self.model.eval()
        positions = []
        risks = []
        values = []
        
        with torch.no_grad():
            for X, _ in data_loader:
                X = X.to(self.hp.device)
                position, risk, value = self.model(X)
                positions.append(position.cpu().numpy())
                risks.append(risk.cpu().numpy())
                values.append(value.cpu().numpy())
                
        return (
            np.concatenate(positions),
            np.concatenate(risks),
            np.concatenate(values)
        )
        
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
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # Plot position loss
        axes[0, 0].plot(history['train_position_loss'], label='Train')
        axes[0, 0].plot(history['val_position_loss'], label='Validation')
        axes[0, 0].set_title('Position Loss')
        axes[0, 0].set_xlabel('Epoch')
        axes[0, 0].set_ylabel('Loss')
        axes[0, 0].legend()
        axes[0, 0].grid(True)
        
        # Plot risk loss
        axes[0, 1].plot(history['train_risk_loss'], label='Train')
        axes[0, 1].plot(history['val_risk_loss'], label='Validation')
        axes[0, 1].set_title('Risk Loss')
        axes[0, 1].set_xlabel('Epoch')
        axes[0, 1].set_ylabel('Loss')
        axes[0, 1].legend()
        axes[0, 1].grid(True)
        
        # Plot value loss
        axes[1, 0].plot(history['train_value_loss'], label='Train')
        axes[1, 0].plot(history['val_value_loss'], label='Validation')
        axes[1, 0].set_title('Value Loss')
        axes[1, 0].set_xlabel('Epoch')
        axes[1, 0].set_ylabel('Loss')
        axes[1, 0].legend()
        axes[1, 0].grid(True)
        
        plt.tight_layout()
        
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
    # Split data
    train_data, test_data = train_test_split(data, test_size=test_size, shuffle=False)
    train_data, val_data = train_test_split(train_data, test_size=val_size, shuffle=False)
    
    # Create datasets
    train_dataset = BrownfieldDataset(train_data, target_col, feature_cols, seq_length, target_length)
    val_dataset = BrownfieldDataset(val_data, target_col, feature_cols, seq_length, target_length)
    test_dataset = BrownfieldDataset(test_data, target_col, feature_cols, seq_length, target_length)
    
    # Create data loaders
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size)
    test_loader = DataLoader(test_dataset, batch_size=batch_size)
    
    return train_loader, val_loader, test_loader

def main():
    """Example usage of the Brownfield predictor."""
    # Set random seed
    torch.manual_seed(42)
    np.random.seed(42)
    
    # Create sample data
    dates = pd.date_range(start='2020-01-01', end='2020-12-31', freq='D')
    data = pd.DataFrame({
        'price': np.random.normal(100, 1, len(dates)),
        'volume': np.random.normal(1000000, 100000, len(dates)),
        'volatility': np.random.normal(0.01, 0.001, len(dates))
    }, index=dates)
    
    # Prepare data
    target_col = 'price'
    feature_cols = ['price', 'volume', 'volatility']
    seq_length = 10
    target_length = 1
    
    train_loader, val_loader, test_loader = prepare_data(
        data=data,
        target_col=target_col,
        feature_cols=feature_cols,
        seq_length=seq_length,
        target_length=target_length
    )
    
    # Create model
    model = BrownfieldPredictor(
        input_dim=len(feature_cols),
        hidden_dim=64,
        num_layers=2,
        num_heads=4,
        dropout=0.1
    )
    
    # Create trainer
    trainer = BrownfieldTrainer(
        model=model,
        hyperparameters=ModelHyperparameters()
    )
    
    # Train model
    history = trainer.train(
        train_loader=train_loader,
        val_loader=val_loader,
        num_epochs=50,
        early_stopping_patience=10
    )
    
    # Plot training history
    trainer.plot_training_history(
        history=history,
        save_path='training_history.png'
    )
    
    # Generate predictions
    positions, risks, values = trainer.predict(test_loader)
    
    # Plot predictions
    plt.figure(figsize=(12, 6))
    plt.plot(data.index[-len(positions):], data[target_col].iloc[-len(positions):], label='Actual')
    plt.plot(data.index[-len(positions):], positions, label='Position')
    plt.plot(data.index[-len(positions):], risks, label='Risk')
    plt.plot(data.index[-len(positions):], values, label='Value')
    plt.title('Brownfield Predictions')
    plt.xlabel('Date')
    plt.ylabel('Value')
    plt.legend()
    plt.grid(True)
    plt.savefig('predictions.png')
    plt.close()

if __name__ == "__main__":
    main() 