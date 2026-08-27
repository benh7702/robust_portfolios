from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable
import numpy as np
import pandas as pd

from .estimators import sample_estimates, regularized_estimates, empirical_bayes_mean
from .metrics import zero_rate_sharpe
from .optimizers import (
    OptimizerResult,
    equal_weight,
    historical_mean_cvar,
    mean_variance,
    wasserstein_robust_mean_cvar,
)


@dataclass(frozen=True)
class BacktestConfig:
    estimation_window: int = 60
    validation_window: int = 12
    max_weight: float = 0.35
    alpha: float = 0.95
    transaction_cost_bps: float = 10.0
    gamma_grid: tuple[float, ...] = (1.0, 2.0, 5.0, 10.0, 20.0, 50.0)
    epsilon_grid: tuple[float, ...] = (0.0005, 0.001, 0.002, 0.004)


@dataclass
class BacktestResult:
    net_returns: pd.DataFrame
    gross_returns: pd.DataFrame
    turnover: pd.DataFrame
    costs: pd.DataFrame
    weights: dict[str, pd.DataFrame]
    hyperparameters: pd.DataFrame
    optimizer_failures: pd.DataFrame


STRATEGIES = [
    "Equal Weight",
    "Sample MVO",
    "Shrinkage MVO",
    "Historical Mean-CVaR",
    "Wasserstein Robust CVaR",
]


def _validation_score(weights: np.ndarray, validation_returns: pd.DataFrame) -> float:
    r = validation_returns.to_numpy() @ weights
    score = zero_rate_sharpe(r)
    return -1e12 if not np.isfinite(score) else float(score)


def _choose_best(
    candidates: list[tuple[tuple[float, ...], Callable[[], OptimizerResult]]],
    validation_returns: pd.DataFrame,
) -> tuple[tuple[float, ...], bool]:
    best_params: tuple[float, ...] | None = None
    best_score = -np.inf
    any_success = False
    for params, solver in candidates:
        result = solver()
        if not result.success:
            continue
        any_success = True
        score = _validation_score(result.weights, validation_returns)
        if score > best_score + 1e-12:
            best_score = score
            best_params = params
    if best_params is None:
        return candidates[0][0], False
    return best_params, any_success


def _drift_weights(weights: np.ndarray, asset_return: np.ndarray) -> np.ndarray:
    values = weights * (1.0 + asset_return)
    total = values.sum()
    if total <= 0:
        return np.full_like(weights, 1.0 / len(weights))
    return values / total


def run_walk_forward(returns: pd.DataFrame, config: BacktestConfig) -> BacktestResult:
    """Run a nested monthly walk-forward study without look-ahead."""
    if config.validation_window >= config.estimation_window:
        raise ValueError("validation_window must be shorter than estimation_window")
    if len(returns) <= config.estimation_window:
        raise ValueError("Insufficient observations for walk-forward study")

    n = returns.shape[1]
    test_index = returns.index[config.estimation_window:]
    net = pd.DataFrame(index=test_index, columns=STRATEGIES, dtype=float)
    gross = net.copy()
    turnover = net.copy()
    costs = net.copy()
    weight_records = {s: [] for s in STRATEGIES}
    hp_records: list[dict[str, object]] = []
    failure_records: list[dict[str, object]] = []
    pretrade = {s: np.full(n, 1.0 / n) for s in STRATEGIES}

    for test_position in range(config.estimation_window, len(returns)):
        date = returns.index[test_position]
        window = returns.iloc[test_position - config.estimation_window:test_position]
        fit = window.iloc[:-config.validation_window]
        validation = window.iloc[-config.validation_window:]

        gamma_sample, ok_sample_tune = _choose_best(
            [((g,), lambda g=g: mean_variance(*sample_estimates(fit), g, config.max_weight))
             for g in config.gamma_grid], validation)
        gamma_shrink, ok_shrink_tune = _choose_best(
            [((g,), lambda g=g: mean_variance(*regularized_estimates(fit), g, config.max_weight))
             for g in config.gamma_grid], validation)
        epsilon_robust, ok_robust_tune = _choose_best(
            [((eps,), lambda eps=eps: wasserstein_robust_mean_cvar(
                fit.to_numpy(), empirical_bayes_mean(fit), eps,
                config.alpha, config.max_weight))
             for eps in config.epsilon_grid], validation)

        sample_mu, sample_cov = sample_estimates(window)
        shrink_mu, shrink_cov = regularized_estimates(window)
        results: dict[str, OptimizerResult] = {
            "Equal Weight": equal_weight(n),
            "Sample MVO": mean_variance(sample_mu, sample_cov, gamma_sample[0], config.max_weight),
            "Shrinkage MVO": mean_variance(shrink_mu, shrink_cov, gamma_shrink[0], config.max_weight),
            "Historical Mean-CVaR": historical_mean_cvar(
                window.to_numpy(), empirical_bayes_mean(window),
                config.alpha, config.max_weight),
            "Wasserstein Robust CVaR": wasserstein_robust_mean_cvar(
                window.to_numpy(), empirical_bayes_mean(window), epsilon_robust[0],
                config.alpha, config.max_weight),
        }

        hp_records.append({
            "date": date,
            "sample_mvo_gamma": gamma_sample[0],
            "shrinkage_mvo_gamma": gamma_shrink[0],
            "robust_epsilon": epsilon_robust[0],
            "sample_tuning_success": ok_sample_tune,
            "shrinkage_tuning_success": ok_shrink_tune,
            "robust_tuning_success": ok_robust_tune,
        })

        asset_return = returns.iloc[test_position].to_numpy(dtype=float)
        for strategy, result in results.items():
            if not result.success:
                failure_records.append({"date": date, "strategy": strategy, "message": result.message})
            w = result.weights if result.success else np.full(n, 1.0 / n)
            one_way_turnover = 0.5 * float(np.abs(w - pretrade[strategy]).sum())
            cost = config.transaction_cost_bps / 10000.0 * one_way_turnover
            gross_return = float(w @ asset_return)
            net_return = gross_return - cost

            weight_records[strategy].append(pd.Series(w, index=returns.columns, name=date))
            turnover.loc[date, strategy] = one_way_turnover
            costs.loc[date, strategy] = cost
            gross.loc[date, strategy] = gross_return
            net.loc[date, strategy] = net_return
            pretrade[strategy] = _drift_weights(w, asset_return)

    weight_frames = {s: pd.DataFrame(rows) for s, rows in weight_records.items()}
    hyperparameters = pd.DataFrame(hp_records).set_index("date")
    failures = pd.DataFrame(failure_records, columns=["date", "strategy", "message"])
    return BacktestResult(net, gross, turnover, costs, weight_frames, hyperparameters, failures)
