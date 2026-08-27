from pathlib import Path
import sys
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from robust_portfolio.data import load_returns
from robust_portfolio.estimators import regularized_estimates
from robust_portfolio.optimizers import mean_variance, historical_mean_cvar, wasserstein_robust_mean_cvar

DATA = ROOT / "data" / "ff12_value_weighted_2010_2025.csv"


def test_data_is_contiguous_and_decimal():
    returns = load_returns(DATA)
    assert returns.shape == (189, 12)
    assert returns.index[0] == pd.Timestamp("2010-01-01")
    assert returns.index[-1] == pd.Timestamp("2025-09-01")
    assert returns.abs().max().max() < 0.5


def test_regularized_covariance_is_psd():
    returns = load_returns(DATA).iloc[:60]
    _, covariance = regularized_estimates(returns)
    assert np.linalg.eigvalsh(covariance).min() > -1e-10


def _assert_valid(weights):
    assert np.isclose(weights.sum(), 1.0, atol=1e-6)
    assert weights.min() >= -1e-7
    assert weights.max() <= 0.350001


def test_optimizers_produce_feasible_weights():
    returns = load_returns(DATA).iloc[:60]
    mu, covariance = regularized_estimates(returns)
    _assert_valid(mean_variance(mu, covariance, 10.0).weights)
    _assert_valid(historical_mean_cvar(returns.to_numpy(), mu).weights)
    _assert_valid(wasserstein_robust_mean_cvar(returns.to_numpy(), mu, 0.001).weights)


def test_robust_objective_penalizes_concentration():
    returns = load_returns(DATA).iloc[:60]
    mu, _ = regularized_estimates(returns)
    plain = historical_mean_cvar(returns.to_numpy(), mu).weights
    robust = wasserstein_robust_mean_cvar(returns.to_numpy(), mu, 0.004).weights
    assert robust.max() <= plain.max() + 1e-6

from robust_portfolio.backtest import BacktestConfig, run_walk_forward


def _small_config() -> BacktestConfig:
    return BacktestConfig(
        estimation_window=18,
        validation_window=6,
        max_weight=0.35,
        transaction_cost_bps=10.0,
        gamma_grid=(2.0,),
        epsilon_grid=(0.001,),
    )


def test_walk_forward_outputs_are_complete_and_costs_are_consistent():
    returns = load_returns(DATA).iloc[:30]
    config = _small_config()
    result = run_walk_forward(returns, config)
    assert result.net_returns.shape == (12, 5)
    assert result.net_returns.notna().all().all()
    assert result.optimizer_failures.empty
    expected_costs = result.turnover * config.transaction_cost_bps / 10000.0
    assert np.allclose(result.costs.to_numpy(), expected_costs.to_numpy())
    assert np.allclose(
        result.net_returns.to_numpy(),
        result.gross_returns.to_numpy() - result.costs.to_numpy(),
    )


def test_final_test_return_does_not_change_preselected_weights():
    returns = load_returns(DATA).iloc[:30].copy()
    altered = returns.copy()
    altered.iloc[-1] = altered.iloc[-1] + np.linspace(-0.20, 0.20, altered.shape[1])
    config = _small_config()
    baseline = run_walk_forward(returns, config)
    changed = run_walk_forward(altered, config)

    for strategy in baseline.weights:
        assert np.allclose(
            baseline.weights[strategy].iloc[-1].to_numpy(),
            changed.weights[strategy].iloc[-1].to_numpy(),
        )
    assert baseline.hyperparameters.iloc[-1].equals(changed.hyperparameters.iloc[-1])
    assert not np.allclose(
        baseline.net_returns.iloc[-1].to_numpy(),
        changed.net_returns.iloc[-1].to_numpy(),
    )
