from __future__ import annotations

from dataclasses import dataclass
import numpy as np
from scipy.optimize import linprog, minimize


@dataclass(frozen=True)
class OptimizerResult:
    weights: np.ndarray
    success: bool
    message: str
    objective: float | None = None


def _validate_weights(weights: np.ndarray, max_weight: float, tol: float = 1e-6) -> np.ndarray:
    w = np.asarray(weights, dtype=float)
    w[np.abs(w) < 1e-10] = 0.0
    if not np.isfinite(w).all():
        raise ValueError("Optimizer returned non-finite weights")
    if abs(w.sum() - 1.0) > 5e-5:
        raise ValueError(f"Weights do not sum to one: {w.sum()}")
    if w.min() < -tol or w.max() > max_weight + tol:
        raise ValueError(f"Weight bounds violated: min={w.min()}, max={w.max()}")
    w = np.clip(w, 0.0, max_weight)
    return w / w.sum()


def equal_weight(n_assets: int) -> OptimizerResult:
    w = np.full(n_assets, 1.0 / n_assets)
    return OptimizerResult(w, True, "closed form", 0.0)


def mean_variance(
    mean: np.ndarray,
    covariance: np.ndarray,
    risk_aversion: float,
    max_weight: float = 0.35,
) -> OptimizerResult:
    """Solve a fully invested, long-only mean-variance portfolio."""
    mean = np.asarray(mean, dtype=float)
    covariance = np.asarray(covariance, dtype=float)
    n = mean.size
    if max_weight * n < 1.0 - 1e-12:
        raise ValueError("max_weight makes full investment infeasible")
    covariance = 0.5 * (covariance + covariance.T) + np.eye(n) * 1e-10

    def objective(w: np.ndarray) -> float:
        return 0.5 * risk_aversion * float(w @ covariance @ w) - float(mean @ w)

    def gradient(w: np.ndarray) -> np.ndarray:
        return risk_aversion * covariance @ w - mean

    result = minimize(
        objective,
        x0=np.full(n, 1.0 / n),
        jac=gradient,
        method="SLSQP",
        bounds=[(0.0, max_weight)] * n,
        constraints=[{"type": "eq", "fun": lambda w: float(w.sum() - 1.0),
                      "jac": lambda w: np.ones_like(w)}],
        options={"ftol": 1e-12, "maxiter": 1000, "disp": False},
    )
    if not result.success:
        return OptimizerResult(np.full(n, 1.0 / n), False, result.message, None)
    w = _validate_weights(result.x, max_weight)
    return OptimizerResult(w, True, result.message, float(result.fun))


def historical_mean_cvar(
    scenarios: np.ndarray,
    expected_mean: np.ndarray,
    alpha: float = 0.95,
    max_weight: float = 0.35,
    target_return: float | None = None,
) -> OptimizerResult:
    """Minimise empirical CVaR subject to an estimated-return floor."""
    r = np.asarray(scenarios, dtype=float)
    mu = np.asarray(expected_mean, dtype=float)
    t, n = r.shape
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be in (0, 1)")
    if target_return is None:
        target_return = float(mu.mean())

    dim = n + 1 + t
    c = np.zeros(dim)
    c[n] = 1.0
    c[n + 1:] = 1.0 / ((1.0 - alpha) * t)

    a_ub = np.zeros((t + 1, dim))
    a_ub[:t, :n] = -r
    a_ub[:t, n] = -1.0
    a_ub[np.arange(t), n + 1 + np.arange(t)] = -1.0
    a_ub[t, :n] = -mu
    b_ub = np.zeros(t + 1)
    b_ub[t] = -target_return

    a_eq = np.zeros((1, dim))
    a_eq[0, :n] = 1.0
    b_eq = np.array([1.0])

    bounds = [(0.0, max_weight)] * n + [(None, None)] + [(0.0, None)] * t
    result = linprog(c, A_ub=a_ub, b_ub=b_ub, A_eq=a_eq, b_eq=b_eq,
                     bounds=bounds, method="highs")
    if not result.success:
        return OptimizerResult(np.full(n, 1.0 / n), False, result.message, None)
    w = _validate_weights(result.x[:n], max_weight)
    return OptimizerResult(w, True, result.message, float(result.fun))


def wasserstein_robust_mean_cvar(
    scenarios: np.ndarray,
    expected_mean: np.ndarray,
    epsilon: float,
    alpha: float = 0.95,
    max_weight: float = 0.35,
    target_return: float | None = None,
) -> OptimizerResult:
    """Minimise Wasserstein-robust CVaR with an estimated-return floor."""
    r = np.asarray(scenarios, dtype=float)
    mu = np.asarray(expected_mean, dtype=float)
    t, n = r.shape
    if epsilon < 0:
        raise ValueError("epsilon must be non-negative")
    if target_return is None:
        target_return = float(mu.mean())

    dim = n + 1 + t + 1
    eta_idx = n
    u_start = n + 1
    m_idx = dim - 1
    c = np.zeros(dim)
    c[eta_idx] = 1.0
    c[u_start:u_start + t] = 1.0 / ((1.0 - alpha) * t)
    c[m_idx] = epsilon / (1.0 - alpha)

    a_ub = np.zeros((t + n + 1, dim))
    a_ub[:t, :n] = -r
    a_ub[:t, eta_idx] = -1.0
    a_ub[np.arange(t), u_start + np.arange(t)] = -1.0
    for j in range(n):
        a_ub[t + j, j] = 1.0
        a_ub[t + j, m_idx] = -1.0
    a_ub[t + n, :n] = -mu
    b_ub = np.zeros(t + n + 1)
    b_ub[t + n] = -target_return

    a_eq = np.zeros((1, dim))
    a_eq[0, :n] = 1.0
    b_eq = np.array([1.0])

    bounds = ([(0.0, max_weight)] * n + [(None, None)] +
              [(0.0, None)] * t + [(0.0, max_weight)])
    result = linprog(c, A_ub=a_ub, b_ub=b_ub, A_eq=a_eq, b_eq=b_eq,
                     bounds=bounds, method="highs")
    if not result.success:
        return OptimizerResult(np.full(n, 1.0 / n), False, result.message, None)
    w = _validate_weights(result.x[:n], max_weight)
    return OptimizerResult(w, True, result.message, float(result.fun))
