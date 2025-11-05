import unittest
import numpy as np
import pandas as pd
from src.model.Brownian_Mean_Reversion_Motion import (
    generate_brownian_paths,
    generate_mean_reverting_paths,
    plot_paths,
    plot_distribution
)

class TestBrownianMotion(unittest.TestCase):
    def setUp(self):
        """Set up test parameters."""
        self.points = 1000
        self.paths = 50
        self.interval = [0.0, 1.0]
        self.mu = 0.0
        self.sigma = 1.0
        self.mu_c = 5.0
        self.sigma_c = 2.0
        self.seed = 42

    def test_standard_brownian_motion(self):
        """Test standard Brownian motion generation."""
        # Generate paths
        t_axis, W = generate_brownian_paths(
            points=self.points,
            paths=self.paths,
            interval=self.interval,
            mu=self.mu,
            sigma=self.sigma,
            seed=self.seed
        )

        # Check dimensions
        self.assertEqual(W.shape, (self.paths, self.points))
        self.assertEqual(len(t_axis), self.points)

        # Check initial values
        self.assertTrue(np.allclose(W[:, 0], 0))

        # Check mean and variance of final values
        final_values = W[:, -1]
        self.assertAlmostEqual(np.mean(final_values), 0, places=1)
        self.assertAlmostEqual(np.std(final_values), 1, places=1)

    def test_mean_reverting_brownian_motion(self):
        """Test mean-reverting Brownian motion generation."""
        # Generate paths
        t_axis, X = generate_mean_reverting_paths(
            points=self.points,
            paths=self.paths,
            interval=self.interval,
            mu=self.mu_c,
            sigma=self.sigma_c,
            seed=self.seed
        )

        # Check dimensions
        self.assertEqual(X.shape, (self.paths, self.points))
        self.assertEqual(len(t_axis), self.points)

        # Check initial values
        self.assertTrue(np.allclose(X[:, 0], 0))

        # Check mean and variance of final values
        final_values = X[:, -1]
        self.assertAlmostEqual(np.mean(final_values), self.mu_c, places=1)
        self.assertAlmostEqual(np.std(final_values), self.sigma_c, places=1)

    def test_plot_functions(self):
        """Test plotting functions."""
        # Generate test data
        t_axis, W = generate_brownian_paths(
            points=self.points,
            paths=self.paths,
            interval=self.interval,
            mu=self.mu,
            sigma=self.sigma,
            seed=self.seed
        )

        # Test path plotting
        fig, ax = plot_paths(t_axis, W, "Test Brownian Motion Paths")
        self.assertIsNotNone(fig)
        self.assertIsNotNone(ax)

        # Test distribution plotting
        final_values = pd.DataFrame({'final_values': W[:, -1]})
        fig, ax = plot_distribution(final_values, "Test Distribution")
        self.assertIsNotNone(fig)
        self.assertIsNotNone(ax)

if __name__ == '__main__':
    unittest.main() 