"""
PPO-based Trading Agent

This module implements a Proximal Policy Optimization (PPO) agent for trading,
featuring:
- Continuous action space for position sizing
- Experience replay with prioritized sampling
- Generalized Advantage Estimation (GAE)
- Value function clipping
- Entropy regularization
- Comprehensive training and evaluation tools
"""

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
import gym
from gym import spaces
import pandas as pd
from collections import deque
import random
import logging
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from src.models.deep_learning.brownfield_predictor import BrownfieldPredictor, BrownfieldTrainer
from src.models.paper_trading.brownfield_trader import BrownfieldTrader

@dataclass
class PPOHyperparameters:
    """Hyperparameters for PPO training."""
    learning_rate: float = 3e-4
    gamma: float = 0.99
    gae_lambda: float = 0.95
    clip_ratio: float = 0.2
    value_clip: float = 0.2
    entropy_coef: float = 0.01
    max_grad_norm: float = 0.5
    batch_size: int = 64
    num_epochs: int = 10
    buffer_size: int = 10000
    min_buffer_size: int = 1000
    target_kl: float = 0.015
    device: str = 'cuda' if torch.cuda.is_available() else 'cpu'

class ActorCritic(nn.Module):
    """
    Actor-Critic network for PPO.
    """
    def __init__(self,
                 state_dim: int,
                 action_dim: int,
                 hidden_dim: int = 256):
        """
        Initialize the Actor-Critic network.
        
        Parameters
        ----------
        state_dim : int
            Dimension of state space
        action_dim : int
            Dimension of action space
        hidden_dim : int
            Dimension of hidden layers
        """
        super().__init__()
        
        # Shared layers
        self.shared = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU()
        )
        
        # Actor (policy) head
        self.actor = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, action_dim)
        )
        
        # Critic (value) head
        self.critic = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 1)
        )
        
        # Initialize weights
        self.apply(self._init_weights)
        
    def _init_weights(self, module):
        """Initialize network weights."""
        if isinstance(module, nn.Linear):
            nn.init.orthogonal_(module.weight, gain=np.sqrt(2))
            module.bias.data.zero_()
            
    def forward(self, state: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass through the network.
        
        Parameters
        ----------
        state : torch.Tensor
            State tensor
            
        Returns
        -------
        Tuple[torch.Tensor, torch.Tensor]
            Action logits and state value
        """
        shared_features = self.shared(state)
        action_logits = self.actor(shared_features)
        value = self.critic(shared_features)
        
        return action_logits, value
        
    def get_action(self,
                  state: torch.Tensor,
                  deterministic: bool = False) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Get action from the policy.
        
        Parameters
        ----------
        state : torch.Tensor
            State tensor
        deterministic : bool
            Whether to use deterministic policy
            
        Returns
        -------
        Tuple[torch.Tensor, torch.Tensor, torch.Tensor]
            Action, log probability, and value
        """
        action_logits, value = self.forward(state)
        
        # Convert logits to action distribution
        action_dist = torch.distributions.Normal(
            loc=action_logits[:, 0],
            scale=torch.exp(action_logits[:, 1])
        )
        
        if deterministic:
            action = action_dist.mean
        else:
            action = action_dist.sample()
            
        log_prob = action_dist.log_prob(action)
        
        return action, log_prob, value

class PPOTrader:
    """
    PPO-based trading agent.
    """
    def __init__(self,
                 state_dim: int,
                 action_dim: int,
                 hyperparameters: Optional[PPOHyperparameters] = None):
        """
        Initialize the PPO trader.
        
        Parameters
        ----------
        state_dim : int
            Dimension of state space
        action_dim : int
            Dimension of action space
        hyperparameters : Optional[PPOHyperparameters]
            PPO hyperparameters
        """
        self.hp = hyperparameters or PPOHyperparameters()
        
        # Create networks
        self.actor_critic = ActorCritic(state_dim, action_dim).to(self.hp.device)
        self.optimizer = optim.Adam(self.actor_critic.parameters(), lr=self.hp.learning_rate)
        
        # Initialize buffer
        self.buffer = deque(maxlen=self.hp.buffer_size)
        
    def process_observation(self,
                          observation: np.ndarray) -> torch.Tensor:
        """
        Process observation for the network.
        
        Parameters
        ----------
        observation : np.ndarray
            Raw observation
            
        Returns
        -------
        torch.Tensor
            Processed observation tensor
        """
        return torch.FloatTensor(observation).to(self.hp.device)
        
    def compute_gae(self,
                   rewards: List[float],
                   values: List[float],
                   next_value: float,
                   dones: List[bool]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute Generalized Advantage Estimation.
        
        Parameters
        ----------
        rewards : List[float]
            List of rewards
        values : List[float]
            List of value estimates
        next_value : float
            Value estimate for next state
        dones : List[bool]
            List of done flags
            
        Returns
        -------
        Tuple[np.ndarray, np.ndarray]
            Advantages and returns
        """
        advantages = []
        returns = []
        gae = 0
        
        for t in reversed(range(len(rewards))):
            if t == len(rewards) - 1:
                next_value_t = next_value
            else:
                next_value_t = values[t + 1]
                
            delta = rewards[t] + self.hp.gamma * next_value_t * (1 - dones[t]) - values[t]
            gae = delta + self.hp.gamma * self.hp.gae_lambda * (1 - dones[t]) * gae
            
            advantages.insert(0, gae)
            returns.insert(0, gae + values[t])
            
        return np.array(advantages), np.array(returns)
        
    def update_policy(self,
                     states: torch.Tensor,
                     actions: torch.Tensor,
                     old_log_probs: torch.Tensor,
                     advantages: torch.Tensor,
                     returns: torch.Tensor) -> Dict[str, float]:
        """
        Update policy using PPO.
        
        Parameters
        ----------
        states : torch.Tensor
            Batch of states
        actions : torch.Tensor
            Batch of actions
        old_log_probs : torch.Tensor
            Batch of old log probabilities
        advantages : torch.Tensor
            Batch of advantages
        returns : torch.Tensor
            Batch of returns
            
        Returns
        -------
        Dict[str, float]
            Training metrics
        """
        # Normalize advantages
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
        
        total_policy_loss = 0
        total_value_loss = 0
        total_entropy = 0
        
        for _ in range(self.hp.num_epochs):
            # Get action distribution and value
            action_logits, values = self.actor_critic(states)
            action_dist = torch.distributions.Normal(
                loc=action_logits[:, 0],
                scale=torch.exp(action_logits[:, 1])
            )
            
            # Calculate new log probabilities
            new_log_probs = action_dist.log_prob(actions)
            
            # Calculate policy loss
            ratio = torch.exp(new_log_probs - old_log_probs)
            policy_loss1 = -ratio * advantages
            policy_loss2 = -torch.clamp(ratio, 1 - self.hp.clip_ratio, 1 + self.hp.clip_ratio) * advantages
            policy_loss = torch.max(policy_loss1, policy_loss2).mean()
            
            # Calculate value loss
            value_loss = 0.5 * ((returns - values.squeeze()) ** 2).mean()
            
            # Calculate entropy
            entropy = action_dist.entropy().mean()
            
            # Total loss
            loss = policy_loss + value_loss - self.hp.entropy_coef * entropy
            
            # Optimize
            self.optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.actor_critic.parameters(), self.hp.max_grad_norm)
            self.optimizer.step()
            
            total_policy_loss += policy_loss.item()
            total_value_loss += value_loss.item()
            total_entropy += entropy.item()
            
        return {
            'policy_loss': total_policy_loss / self.hp.num_epochs,
            'value_loss': total_value_loss / self.hp.num_epochs,
            'entropy': total_entropy / self.hp.num_epochs
        }
        
    def train(self,
             env: gym.Env,
             num_episodes: int,
             max_steps: int = 1000,
             save_path: Optional[str] = None) -> Dict[str, List[float]]:
        """
        Train the agent.
        
        Parameters
        ----------
        env : gym.Env
            Trading environment
        num_episodes : int
            Number of episodes to train
        max_steps : int
            Maximum steps per episode
        save_path : Optional[str]
            Path to save model
            
        Returns
        -------
        Dict[str, List[float]]
            Training history
        """
        history = {
            'episode_rewards': [],
            'policy_loss': [],
            'value_loss': [],
            'entropy': []
        }
        
        for episode in range(num_episodes):
            state = env.reset()
            episode_reward = 0
            states = []
            actions = []
            rewards = []
            values = []
            log_probs = []
            dones = []
            
            for step in range(max_steps):
                # Get action
                state_tensor = self.process_observation(state)
                action, log_prob, value = self.actor_critic.get_action(state_tensor)
                
                # Take action
                next_state, reward, done, _ = env.step(action.cpu().numpy())
                
                # Store transition
                states.append(state)
                actions.append(action.cpu().numpy())
                rewards.append(reward)
                values.append(value.item())
                log_probs.append(log_prob.item())
                dones.append(done)
                
                state = next_state
                episode_reward += reward
                
                if done:
                    break
                    
            # Compute advantages and returns
            next_value = self.actor_critic.get_action(
                self.process_observation(next_state),
                deterministic=True
            )[2].item()
            
            advantages, returns = self.compute_gae(
                rewards=rewards,
                values=values,
                next_value=next_value,
                dones=dones
            )
            
            # Update policy
            metrics = self.update_policy(
                states=torch.FloatTensor(np.array(states)).to(self.hp.device),
                actions=torch.FloatTensor(np.array(actions)).to(self.hp.device),
                old_log_probs=torch.FloatTensor(np.array(log_probs)).to(self.hp.device),
                advantages=torch.FloatTensor(advantages).to(self.hp.device),
                returns=torch.FloatTensor(returns).to(self.hp.device)
            )
            
            # Record history
            history['episode_rewards'].append(episode_reward)
            history['policy_loss'].append(metrics['policy_loss'])
            history['value_loss'].append(metrics['value_loss'])
            history['entropy'].append(metrics['entropy'])
            
            print(f'Episode {episode+1}/{num_episodes}:')
            print(f'Reward: {episode_reward:.2f}')
            print(f'Policy Loss: {metrics["policy_loss"]:.4f}')
            print(f'Value Loss: {metrics["value_loss"]:.4f}')
            print(f'Entropy: {metrics["entropy"]:.4f}')
            
            # Save model
            if save_path and (episode + 1) % 100 == 0:
                self.save(save_path)
                
        return history
        
    def save(self, path: str):
        """
        Save model.
        
        Parameters
        ----------
        path : str
            Path to save model
        """
        torch.save({
            'actor_critic_state_dict': self.actor_critic.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict()
        }, path)
        
    def load(self, path: str):
        """
        Load model.
        
        Parameters
        ----------
        path : str
            Path to load model from
        """
        checkpoint = torch.load(path)
        self.actor_critic.load_state_dict(checkpoint['actor_critic_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        
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
        
        # Plot episode rewards
        axes[0, 0].plot(history['episode_rewards'])
        axes[0, 0].set_title('Episode Rewards')
        axes[0, 0].set_xlabel('Episode')
        axes[0, 0].set_ylabel('Reward')
        axes[0, 0].grid(True)
        
        # Plot policy loss
        axes[0, 1].plot(history['policy_loss'])
        axes[0, 1].set_title('Policy Loss')
        axes[0, 1].set_xlabel('Episode')
        axes[0, 1].set_ylabel('Loss')
        axes[0, 1].grid(True)
        
        # Plot value loss
        axes[1, 0].plot(history['value_loss'])
        axes[1, 0].set_title('Value Loss')
        axes[1, 0].set_xlabel('Episode')
        axes[1, 0].set_ylabel('Loss')
        axes[1, 0].grid(True)
        
        # Plot entropy
        axes[1, 1].plot(history['entropy'])
        axes[1, 1].set_title('Entropy')
        axes[1, 1].set_xlabel('Episode')
        axes[1, 1].set_ylabel('Entropy')
        axes[1, 1].grid(True)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path)
        plt.close()

def main():
    """Example usage of the PPO trader."""
    # Create environment
    env = gym.make('TradingEnv-v0')
    
    # Create agent
    state_dim = env.observation_space.shape[0]
    action_dim = env.action_space.shape[0]
    
    agent = PPOTrader(
        state_dim=state_dim,
        action_dim=action_dim,
        hyperparameters=PPOHyperparameters(
            learning_rate=3e-4,
            gamma=0.99,
            gae_lambda=0.95,
            clip_ratio=0.2,
            value_clip=0.2,
            entropy_coef=0.01,
            max_grad_norm=0.5,
            batch_size=64,
            num_epochs=10
        )
    )
    
    # Train agent
    history = agent.train(
        env=env,
        num_episodes=1000,
        max_steps=1000,
        save_path='ppo_trader.pth'
    )
    
    # Plot training history
    agent.plot_training_history(
        history=history,
        save_path='training_history.png'
    )

    # Create trader
    trader = BrownfieldTrader(
        model=model,
        initial_capital=100000.0,
        max_position_size=0.1,
        max_drawdown=0.15,
        risk_reward_ratio=3.0
    )

    # Process market data
    for bar in market_data:
        trader.process_bar('SPY', bar)

    # Analyze results
    metrics = trader.get_performance_metrics()
    trader.plot_performance(save_path='performance.png')
    trader.save_results('trading_results.json')

if __name__ == "__main__":
    main() 