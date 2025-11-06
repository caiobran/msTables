"""
Reinforcement Learning Trading Agent

This module implements a PPO-based trading agent with continuous action space
and advanced features like experience replay and prioritized sampling.
"""

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from pathlib import Path
from collections import deque
import random
from src.models.rl_trading_env import TradingEnv

class ActorCritic(nn.Module):
    """
    Actor-Critic network for PPO.
    """
    def __init__(self,
                 input_dim: int,
                 hidden_dim: int,
                 output_dim: int):
        """
        Initialize the Actor-Critic network.
        
        Parameters
        ----------
        input_dim : int
            Dimension of input features
        hidden_dim : int
            Dimension of hidden layers
        output_dim : int
            Dimension of action space
        """
        super().__init__()
        
        # Shared layers
        self.shared = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU()
        )
        
        # Actor (policy) head
        self.actor = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, output_dim),
            nn.Tanh()  # Bound actions to [-1, 1]
        )
        
        # Critic (value) head
        self.critic = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 1)
        )
        
        # Initialize weights
        self._init_weights()
        
    def _init_weights(self):
        """Initialize weights using orthogonal initialization."""
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.orthogonal_(m.weight, gain=np.sqrt(2))
                nn.init.constant_(m.bias, 0.0)
                
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass through the network.
        
        Parameters
        ----------
        x : torch.Tensor
            Input tensor
            
        Returns
        -------
        Tuple[torch.Tensor, torch.Tensor]
            Action and value predictions
        """
        shared_features = self.shared(x)
        return self.actor(shared_features), self.critic(shared_features)

class PPOTrader:
    """
    PPO-based trading agent.
    """
    def __init__(self,
                 env: TradingEnv,
                 hidden_dim: int = 256,
                 learning_rate: float = 3e-4,
                 gamma: float = 0.99,
                 gae_lambda: float = 0.95,
                 clip_ratio: float = 0.2,
                 target_kl: float = 0.01,
                 entropy_coef: float = 0.01,
                 value_coef: float = 0.5,
                 max_grad_norm: float = 0.5,
                 device: Optional[torch.device] = None):
        """
        Initialize the PPO trader.
        
        Parameters
        ----------
        env : TradingEnv
            Trading environment
        hidden_dim : int
            Dimension of hidden layers
        learning_rate : float
            Learning rate for optimizer
        gamma : float
            Discount factor
        gae_lambda : float
            GAE-Lambda parameter
        clip_ratio : float
            PPO clip ratio
        target_kl : float
            Target KL divergence
        entropy_coef : float
            Entropy coefficient
        value_coef : float
            Value loss coefficient
        max_grad_norm : float
            Maximum gradient norm
        device : Optional[torch.device]
            Device to use for training
        """
        self.env = env
        self.device = device or torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Get input dimension from environment
        input_dim = env.observation_space['market_data'].shape[0] * env.observation_space['market_data'].shape[1] + 2  # +2 for position and balance
        
        # Create actor-critic network
        self.actor_critic = ActorCritic(
            input_dim=input_dim,
            hidden_dim=hidden_dim,
            output_dim=env.action_space.shape[0]
        ).to(self.device)
        
        # Initialize optimizer
        self.optimizer = optim.Adam(
            self.actor_critic.parameters(),
            lr=learning_rate
        )
        
        # Hyperparameters
        self.gamma = gamma
        self.gae_lambda = gae_lambda
        self.clip_ratio = clip_ratio
        self.target_kl = target_kl
        self.entropy_coef = entropy_coef
        self.value_coef = value_coef
        self.max_grad_norm = max_grad_norm
        
        # Experience buffer
        self.buffer = deque(maxlen=10000)
        
    def _process_observation(self, obs: Dict) -> torch.Tensor:
        """
        Process observation into network input.
        
        Parameters
        ----------
        obs : Dict
            Observation from environment
            
        Returns
        -------
        torch.Tensor
            Processed observation
        """
        # Flatten market data
        market_data = obs['market_data'].flatten()
        
        # Combine with position and balance
        return torch.FloatTensor(
            np.concatenate([
                market_data,
                obs['position'],
                obs['balance']
            ])
        ).to(self.device)
        
    def _compute_gae(self,
                    rewards: np.ndarray,
                    values: np.ndarray,
                    next_value: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute Generalized Advantage Estimation.
        
        Parameters
        ----------
        rewards : np.ndarray
            Array of rewards
        values : np.ndarray
            Array of value predictions
        next_value : float
            Value prediction for next state
            
        Returns
        -------
        Tuple[np.ndarray, np.ndarray]
            Advantages and returns
        """
        advantages = np.zeros_like(rewards)
        last_gae = 0
        
        for t in reversed(range(len(rewards))):
            if t == len(rewards) - 1:
                next_value_t = next_value
            else:
                next_value_t = values[t + 1]
                
            delta = rewards[t] + self.gamma * next_value_t - values[t]
            advantages[t] = last_gae = delta + self.gamma * self.gae_lambda * last_gae
            
        returns = advantages + values
        return advantages, returns
        
    def _update_policy(self,
                      obs_batch: List[Dict],
                      actions: np.ndarray,
                      old_log_probs: np.ndarray,
                      advantages: np.ndarray,
                      returns: np.ndarray) -> Dict:
        """
        Update policy using PPO.
        
        Parameters
        ----------
        obs_batch : List[Dict]
            Batch of observations
        actions : np.ndarray
            Batch of actions
        old_log_probs : np.ndarray
            Batch of old action log probabilities
        advantages : np.ndarray
            Batch of advantages
        returns : np.ndarray
            Batch of returns
            
        Returns
        -------
        Dict
            Training statistics
        """
        # Convert to tensors
        obs_tensor = torch.stack([self._process_observation(obs) for obs in obs_batch])
        actions_tensor = torch.FloatTensor(actions).to(self.device)
        old_log_probs_tensor = torch.FloatTensor(old_log_probs).to(self.device)
        advantages_tensor = torch.FloatTensor(advantages).to(self.device)
        returns_tensor = torch.FloatTensor(returns).to(self.device)
        
        # Normalize advantages
        advantages_tensor = (advantages_tensor - advantages_tensor.mean()) / (advantages_tensor.std() + 1e-8)
        
        # PPO update
        for _ in range(10):  # Multiple epochs
            # Forward pass
            action_pred, value_pred = self.actor_critic(obs_tensor)
            
            # Calculate new log probabilities
            log_probs = -0.5 * ((actions_tensor - action_pred) ** 2).sum(dim=1)
            
            # Calculate ratios
            ratios = torch.exp(log_probs - old_log_probs_tensor)
            
            # Calculate surrogate losses
            surr1 = ratios * advantages_tensor
            surr2 = torch.clamp(ratios, 1 - self.clip_ratio, 1 + self.clip_ratio) * advantages_tensor
            actor_loss = -torch.min(surr1, surr2).mean()
            
            # Calculate value loss
            value_loss = 0.5 * (returns_tensor - value_pred.squeeze()).pow(2).mean()
            
            # Calculate entropy loss
            entropy_loss = -log_probs.mean()
            
            # Total loss
            loss = actor_loss + self.value_coef * value_loss - self.entropy_coef * entropy_loss
            
            # Optimize
            self.optimizer.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(self.actor_critic.parameters(), self.max_grad_norm)
            self.optimizer.step()
            
            # Calculate KL divergence
            kl = (old_log_probs_tensor - log_probs).mean()
            
            # Early stopping
            if kl > 1.5 * self.target_kl:
                break
                
        return {
            'actor_loss': actor_loss.item(),
            'value_loss': value_loss.item(),
            'entropy_loss': entropy_loss.item(),
            'kl': kl.item()
        }
        
    def train(self,
              num_episodes: int,
              max_steps: int = 1000,
              batch_size: int = 64) -> Dict[str, List[float]]:
        """
        Train the agent.
        
        Parameters
        ----------
        num_episodes : int
            Number of episodes to train
        max_steps : int
            Maximum steps per episode
        batch_size : int
            Batch size for updates
            
        Returns
        -------
        Dict[str, List[float]]
            Training history
        """
        history = {
            'episode_rewards': [],
            'actor_losses': [],
            'value_losses': [],
            'entropy_losses': []
        }
        
        for episode in range(num_episodes):
            obs = self.env.reset()
            episode_reward = 0
            episode_data = []
            
            for step in range(max_steps):
                # Get action
                with torch.no_grad():
                    obs_tensor = self._process_observation(obs)
                    action_pred, value_pred = self.actor_critic(obs_tensor.unsqueeze(0))
                    action = action_pred.squeeze().cpu().numpy()
                    
                # Take action
                next_obs, reward, done, info = self.env.step(action)
                
                # Store transition
                episode_data.append({
                    'obs': obs,
                    'action': action,
                    'reward': reward,
                    'value': value_pred.item(),
                    'log_prob': -0.5 * ((action - action_pred.squeeze().cpu().numpy()) ** 2).sum()
                })
                
                episode_reward += reward
                obs = next_obs
                
                if done:
                    break
                    
            # Process episode data
            rewards = np.array([d['reward'] for d in episode_data])
            values = np.array([d['value'] for d in episode_data])
            actions = np.array([d['action'] for d in episode_data])
            old_log_probs = np.array([d['log_prob'] for d in episode_data])
            
            # Compute advantages
            with torch.no_grad():
                next_value = self.actor_critic(
                    self._process_observation(next_obs).unsqueeze(0)
                )[1].item()
                
            advantages, returns = self._compute_gae(rewards, values, next_value)
            
            # Update policy
            stats = self._update_policy(
                obs_batch=[d['obs'] for d in episode_data],
                actions=actions,
                old_log_probs=old_log_probs,
                advantages=advantages,
                returns=returns
            )
            
            # Update history
            history['episode_rewards'].append(episode_reward)
            history['actor_losses'].append(stats['actor_loss'])
            history['value_losses'].append(stats['value_loss'])
            history['entropy_losses'].append(stats['entropy_loss'])
            
            if episode % 10 == 0:
                print(f"Episode {episode}: Reward = {episode_reward:.2f}")
                
        return history
        
    def save(self, path: str):
        """
        Save the model.
        
        Parameters
        ----------
        path : str
            Path to save the model
        """
        torch.save({
            'actor_critic_state_dict': self.actor_critic.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict()
        }, path)
        
    def load(self, path: str):
        """
        Load the model.
        
        Parameters
        ----------
        path : str
            Path to load the model from
        """
        checkpoint = torch.load(path)
        self.actor_critic.load_state_dict(checkpoint['actor_critic_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])

def main():
    """Example usage of the PPO trader."""
    # Create environment
    env = TradingEnv(
        data=pd.DataFrame(),  # Your market data here
        initial_balance=100000.0,
        transaction_fee=0.001,
        max_position=1.0,
        window_size=20,
        use_lstm=True
    )
    
    # Create agent
    agent = PPOTrader(
        env=env,
        hidden_dim=256,
        learning_rate=3e-4
    )
    
    # Train agent
    history = agent.train(
        num_episodes=1000,
        max_steps=1000,
        batch_size=64
    )
    
    # Save model
    agent.save('data/models/ppo_trader.pth')
    
    # Print final metrics
    final_rewards = history['episode_rewards'][-10:]
    print(f"\nAverage reward over last 10 episodes: {np.mean(final_rewards):.2f}")

if __name__ == "__main__":
    main() 