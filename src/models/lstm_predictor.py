"""
LSTM-based Market Predictor

This module implements a GPU-accelerated LSTM model for market prediction,
with support for multiple features, attention mechanisms, and advanced training options.
"""

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import logging
from pathlib import Path
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import seaborn as sns

class AttentionLayer(nn.Module):
    """Attention mechanism for focusing on important time steps."""
    def __init__(self, hidden_dim: int):
        super().__init__()
        self.attention = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, 1)
        )
        
    def forward(self, lstm_output: torch.Tensor) -> torch.Tensor:
        attention_weights = self.attention(lstm_output)
        attention_weights = torch.softmax(attention_weights, dim=1)
        return torch.sum(attention_weights * lstm_output, dim=1)

class LSTMPredictor(nn.Module):
    """
    LSTM-based market predictor with attention mechanism and multiple features.
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
            Number of hidden units in LSTM
        num_layers : int
            Number of LSTM layers
        output_dim : int
            Number of output features (predictions)
        dropout : float
            Dropout rate for regularization
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
            self.fc = nn.Linear(hidden_dim, output_dim)
        else:
            self.fc = nn.Linear(hidden_dim, output_dim)
            
        # Initialize weights
        self._init_weights()
        
    def _init_weights(self):
        """Initialize weights using Xavier initialization."""
        for name, param in self.named_parameters():
            if 'weight' in name:
                nn.init.xavier_uniform_(param)
            elif 'bias' in name:
                nn.init.constant_(param, 0.0)
                
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
        
        # Apply attention if enabled
        if self.use_attention:
            out = self.attention(lstm_out)
        else:
            out = lstm_out[:, -1, :]  # Take last time step
            
        # Final fully connected layer
        out = self.fc(out)
        return out

class MarketLSTMTrainer:
    """
    Trainer class for the LSTM market predictor.
    """
    def __init__(self,
                 model: LSTMPredictor,
                 device: torch.device,
                 learning_rate: float = 0.001,
                 weight_decay: float = 1e-5):
        """
        Initialize the trainer.
        
        Parameters
        ----------
        model : LSTMPredictor
            The LSTM model to train
        device : torch.device
            Device to use for training (CPU/GPU)
        learning_rate : float
            Learning rate for optimizer
        weight_decay : float
            Weight decay for regularization
        """
        self.model = model.to(device)
        self.device = device
        self.criterion = nn.MSELoss()
        self.optimizer = optim.Adam(
            model.parameters(),
            lr=learning_rate,
            weight_decay=weight_decay
        )
        self.scaler = StandardScaler()
        
    def prepare_data(self,
                    data: pd.DataFrame,
                    sequence_length: int,
                    train_split: float = 0.8) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Prepare data for training.
        
        Parameters
        ----------
        data : pd.DataFrame
            Input data with features
        sequence_length : int
            Length of input sequences
        train_split : float
            Proportion of data to use for training
            
        Returns
        -------
        Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]
            Training and validation data
        """
        # Scale features
        scaled_data = self.scaler.fit_transform(data)
        
        # Create sequences
        X, y = [], []
        for i in range(len(scaled_data) - sequence_length):
            X.append(scaled_data[i:(i + sequence_length)])
            y.append(scaled_data[i + sequence_length, 0])  # Predict first feature
            
        X = np.array(X)
        y = np.array(y)
        
        # Split into train and validation
        train_size = int(len(X) * train_split)
        X_train, X_val = X[:train_size], X[train_size:]
        y_train, y_val = y[:train_size], y[train_size:]
        
        # Convert to tensors
        X_train = torch.FloatTensor(X_train).to(self.device)
        y_train = torch.FloatTensor(y_train).to(self.device)
        X_val = torch.FloatTensor(X_val).to(self.device)
        y_val = torch.FloatTensor(y_val).to(self.device)
        
        return X_train, y_train, X_val, y_val
        
    def train(self,
              X_train: torch.Tensor,
              y_train: torch.Tensor,
              X_val: torch.Tensor,
              y_val: torch.Tensor,
              epochs: int,
              batch_size: int,
              early_stopping_patience: int = 10) -> Dict[str, List[float]]:
        """
        Train the model.
        
        Parameters
        ----------
        X_train : torch.Tensor
            Training features
        y_train : torch.Tensor
            Training targets
        X_val : torch.Tensor
            Validation features
        y_val : torch.Tensor
            Validation targets
        epochs : int
            Number of epochs to train
        batch_size : int
            Batch size for training
        early_stopping_patience : int
            Number of epochs to wait for improvement before stopping
            
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
        
        for epoch in range(epochs):
            # Training
            self.model.train()
            train_loss = 0
            for i in range(0, len(X_train), batch_size):
                batch_X = X_train[i:i + batch_size]
                batch_y = y_train[i:i + batch_size]
                
                self.optimizer.zero_grad()
                outputs = self.model(batch_X)
                loss = self.criterion(outputs.squeeze(), batch_y)
                loss.backward()
                self.optimizer.step()
                
                train_loss += loss.item()
                
            train_loss /= len(X_train)
            history['train_loss'].append(train_loss)
            
            # Validation
            self.model.eval()
            with torch.no_grad():
                val_outputs = self.model(X_val)
                val_loss = self.criterion(val_outputs.squeeze(), y_val)
                history['val_loss'].append(val_loss.item())
                
            # Early stopping
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                # Save best model
                torch.save(self.model.state_dict(), 'data/models/best_lstm_model.pth')
            else:
                patience_counter += 1
                
            if patience_counter >= early_stopping_patience:
                print(f"Early stopping at epoch {epoch}")
                break
                
            if epoch % 10 == 0:
                print(f"Epoch {epoch}: Train Loss = {train_loss:.4f}, Val Loss = {val_loss:.4f}")
                
        return history
        
    def predict(self, X: torch.Tensor) -> np.ndarray:
        """
        Generate predictions.
        
        Parameters
        ----------
        X : torch.Tensor
            Input features
            
        Returns
        -------
        np.ndarray
            Predictions
        """
        self.model.eval()
        with torch.no_grad():
            predictions = self.model(X)
        return predictions.cpu().numpy()
        
    def plot_training_history(self, history: Dict[str, List[float]]):
        """
        Plot training history.
        
        Parameters
        ----------
        history : Dict[str, List[float]]
            Training history
        """
        plt.figure(figsize=(10, 6))
        plt.plot(history['train_loss'], label='Training Loss')
        plt.plot(history['val_loss'], label='Validation Loss')
        plt.title('Training History')
        plt.xlabel('Epoch')
        plt.ylabel('Loss')
        plt.legend()
        plt.savefig('data/plots/lstm_training_history.png')
        plt.close()

def main():
    """Example usage of the LSTM predictor."""
    # Set up device
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    
    # Create model
    model = LSTMPredictor(
        input_dim=10,  # Number of features
        hidden_dim=64,
        num_layers=2,
        output_dim=1,
        dropout=0.2,
        use_attention=True
    )
    
    # Create trainer
    trainer = MarketLSTMTrainer(
        model=model,
        device=device,
        learning_rate=0.001
    )
    
    # Load and prepare data
    # This is a placeholder - you'll need to implement data loading
    data = pd.DataFrame()  # Your market data here
    
    # Train model
    X_train, y_train, X_val, y_val = trainer.prepare_data(
        data=data,
        sequence_length=20,
        train_split=0.8
    )
    
    history = trainer.train(
        X_train=X_train,
        y_train=y_train,
        X_val=X_val,
        y_val=y_val,
        epochs=100,
        batch_size=32
    )
    
    # Plot training history
    trainer.plot_training_history(history)

if __name__ == "__main__":
    main() 