from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.covariance import LedoitWolf


def sample_estimates(returns: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Sample mean and covariance using monthly decimal returns."""
    x = returns.to_numpy(dtype=float)
    return x.mean(axis=0), np.cov(x, rowvar=False, ddof=1)


def empirical_bayes_mean(returns: pd.DataFrame) -> np.ndarray:
    """Shrink asset means toward a common empirical-Bayes prior."""
    x = returns.to_numpy(dtype=float)
    t = x.shape[0]
    sample_mean = x.mean(axis=0)
    sample_var = x.var(axis=0, ddof=1)
    sampling_var = sample_var / max(t, 1)
    prior_mean = float(sample_mean.mean())
    observed_between = float(sample_mean.var(ddof=1))
    prior_var = max(observed_between - float(sampling_var.mean()), 1e-10)
    reliability = prior_var / (prior_var + sampling_var)
    return reliability * sample_mean + (1.0 - reliability) * prior_mean


def ledoit_wolf_covariance(returns: pd.DataFrame) -> np.ndarray:
    """Ledoit-Wolf linear shrinkage covariance estimate."""
    estimator = LedoitWolf(assume_centered=False).fit(returns.to_numpy(dtype=float))
    sigma = estimator.covariance_
    return 0.5 * (sigma + sigma.T)


def regularized_estimates(returns: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    return empirical_bayes_mean(returns), ledoit_wolf_covariance(returns)
