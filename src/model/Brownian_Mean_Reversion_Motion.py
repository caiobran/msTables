# Brownian_Mean_Reversion_Motion.py
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

def generate_brownian_paths(points=1000, paths=50, interval=[0.0, 1.0], mu=0.0, sigma=1.0, seed=42):
    """
    Generate standard Brownian motion paths.

    Parameters
    ----------
    points : int
        Number of points per path
    paths : int
        Number of paths to generate
    interval : list
        Time interval [start, end]
    mu : float
        Mean of the normal distribution
    sigma : float
        Standard deviation of the normal distribution
    seed : int
        Random seed for reproducibility

    Returns
    -------
    tuple
        (t_axis, W) where t_axis is the time axis and W is the array of paths
    """
# Seed the random number generator
    rng = np.random.default_rng(seed)

# Create the initial set of random normal draws
Z = rng.normal(mu, sigma, (paths, points))

# Define the time step size and t-axis
dt = (interval[1] - interval[0]) / (points - 1)
t_axis = np.linspace(interval[0], interval[1], points)

    # Use Equation 3.2 from [Glasserman, 2003] to sample standard brownian motion paths
W = np.zeros((paths, points))
for idx in range(points - 1):
    real_idx = idx + 1
    W[:, real_idx] = W[:, real_idx - 1] + np.sqrt(dt) * Z[:, idx]

    return t_axis, W

def generate_mean_reverting_paths(points=1000, paths=50, interval=[0.0, 1.0], mu=5.0, sigma=2.0, seed=42):
    """
    Generate mean-reverting Brownian motion paths.

    Parameters
    ----------
    points : int
        Number of points per path
    paths : int
        Number of paths to generate
    interval : list
        Time interval [start, end]
    mu : float
        Mean of the process
    sigma : float
        Standard deviation of the process
    seed : int
        Random seed for reproducibility

    Returns
    -------
    tuple
        (t_axis, X) where t_axis is the time axis and X is the array of paths
    """
    # Seed the random number generator
    rng = np.random.default_rng(seed)

    # Create the initial set of random normal draws
    Z = rng.normal(0, 1, (paths, points))

    # Define the time step size and t-axis
    dt = (interval[1] - interval[0]) / (points - 1)
    t_axis = np.linspace(interval[0], interval[1], points)

    # Use Equation 3.3 from [Glasserman, 2003] to sample brownian motion paths
    X = np.zeros((paths, points))
    for idx in range(points - 1):
        real_idx = idx + 1
        X[:, real_idx] = X[:, real_idx - 1] + mu * dt + sigma * np.sqrt(dt) * Z[:, idx]

    return t_axis, X

def plot_paths(t_axis, paths, title="Brownian Motion Paths"):
    """
    Plot the generated paths.

    Parameters
    ----------
    t_axis : numpy.ndarray
        Time axis
    paths : numpy.ndarray
        Array of paths
    title : str
        Plot title

    Returns
    -------
    tuple
        (fig, ax) matplotlib figure and axis objects
    """
fig, ax = plt.subplots(1, 1, figsize=(12, 8))
    for path in range(paths.shape[0]):
        ax.plot(t_axis, paths[path, :])
    ax.set_title(title)
ax.set_xlabel("Time")
ax.set_ylabel("Asset Value")
    return fig, ax

def plot_distribution(final_values, title="Distribution of Final Values"):
    """
    Plot the distribution of final values.

    Parameters
    ----------
    final_values : pandas.DataFrame
        DataFrame containing final values
    title : str
        Plot title

    Returns
    -------
    tuple
        (fig, ax) matplotlib figure and axis objects
    """
fig, ax = plt.subplots(1, 1, figsize=(12, 8))
sns.kdeplot(data=final_values, x='final_values', fill=True, ax=ax)
    ax.set_title(title)
ax.set_ylim(0.0, 0.325)
ax.set_xlabel('Final Values of Asset Paths')
    return fig, ax

if __name__ == "__main__":
    # Example usage
    # Generate and plot standard Brownian motion paths
    t_axis, W = generate_brownian_paths()
    fig, ax = plot_paths(t_axis, W, "Standard Brownian Motion Paths")
plt.show()

    # Plot distribution of final values
    final_values = pd.DataFrame({'final_values': W[:, -1]})
    fig, ax = plot_distribution(final_values)
    plt.show()

    # Generate and plot mean-reverting Brownian motion paths
    t_axis, X = generate_mean_reverting_paths()
    fig, ax = plot_paths(t_axis, X, "Mean-Reverting Brownian Motion Paths")
plt.show()