from __future__ import annotations

import numpy as np
import pandas as pd


def wealth_index(returns: pd.Series) -> pd.Series:
    return (1.0 + returns).cumprod()


def drawdown_series(returns: pd.Series) -> pd.Series:
    wealth = wealth_index(returns)
    return wealth / wealth.cummax() - 1.0


def cvar_loss(returns: pd.Series | np.ndarray, alpha: float = 0.95) -> float:
    x = np.asarray(returns, dtype=float)
    if x.size == 0:
        return float("nan")
    cutoff = np.quantile(x, 1.0 - alpha)
    tail = x[x <= cutoff]
    return float(-tail.mean()) if tail.size else float("nan")


def annualized_return(returns: pd.Series | np.ndarray, periods: int = 12) -> float:
    x = np.asarray(returns, dtype=float)
    if x.size == 0 or np.any(1.0 + x <= 0):
        return float("nan")
    return float(np.prod(1.0 + x) ** (periods / x.size) - 1.0)


def annualized_volatility(returns: pd.Series | np.ndarray, periods: int = 12) -> float:
    x = np.asarray(returns, dtype=float)
    return float(np.std(x, ddof=1) * np.sqrt(periods)) if x.size > 1 else float("nan")


def zero_rate_sharpe(returns: pd.Series | np.ndarray, periods: int = 12) -> float:
    x = np.asarray(returns, dtype=float)
    if x.size < 2 or np.std(x, ddof=1) <= 0:
        return float("nan")
    return float(x.mean() / np.std(x, ddof=1) * np.sqrt(periods))


def sortino_ratio(returns: pd.Series | np.ndarray, periods: int = 12) -> float:
    x = np.asarray(returns, dtype=float)
    downside = x[x < 0]
    if downside.size < 2 or np.std(downside, ddof=1) <= 0:
        return float("nan")
    return float(x.mean() * periods / (np.std(downside, ddof=1) * np.sqrt(periods)))


def performance_summary(
    net_returns: pd.DataFrame,
    gross_returns: pd.DataFrame,
    turnover: pd.DataFrame,
    weights: dict[str, pd.DataFrame],
    alpha: float = 0.95,
) -> pd.DataFrame:
    records: list[dict[str, float | str]] = []
    for strategy in net_returns.columns:
        r = net_returns[strategy].dropna()
        gross = gross_returns[strategy].reindex(r.index)
        t = turnover[strategy].reindex(r.index)
        w = weights[strategy].reindex(r.index)
        dd = drawdown_series(r)
        records.append({
            "Strategy": strategy,
            "Annualized Return": annualized_return(r),
            "Annualized Volatility": annualized_volatility(r),
            "Zero-Rate Sharpe": zero_rate_sharpe(r),
            "Sortino": sortino_ratio(r),
            "Maximum Drawdown": float(dd.min()),
            f"{int(alpha*100)}% CVaR Loss": cvar_loss(r, alpha),
            "Average Monthly Turnover": float(t.mean()),
            "Annualized Cost Drag": float((gross - r).mean() * 12.0),
            "Average Effective N": float((1.0 / (w.pow(2).sum(axis=1))).mean()),
            "Average Maximum Weight": float(w.max(axis=1).mean()),
            "Terminal Wealth": float((1.0 + r).prod()),
        })
    return pd.DataFrame.from_records(records).set_index("Strategy")


def moving_block_bootstrap_difference(
    strategy_returns: pd.Series,
    benchmark_returns: pd.Series,
    reps: int = 2000,
    block_length: int = 6,
    seed: int = 7,
) -> dict[str, float]:
    """Circular moving-block bootstrap for mean and Sharpe differences."""
    aligned = pd.concat([strategy_returns, benchmark_returns], axis=1).dropna()
    a = aligned.iloc[:, 0].to_numpy()
    b = aligned.iloc[:, 1].to_numpy()
    n = len(aligned)
    if n < block_length:
        raise ValueError("Not enough observations for requested block length")
    rng = np.random.default_rng(seed)
    starts = np.arange(n)
    mean_diffs = np.empty(reps)
    sharpe_diffs = np.empty(reps)
    blocks_needed = int(np.ceil(n / block_length))
    for k in range(reps):
        sampled: list[int] = []
        for s in rng.choice(starts, size=blocks_needed, replace=True):
            sampled.extend(((s + np.arange(block_length)) % n).tolist())
        idx = np.asarray(sampled[:n], dtype=int)
        aa, bb = a[idx], b[idx]
        mean_diffs[k] = (aa.mean() - bb.mean()) * 12.0
        sharpe_diffs[k] = zero_rate_sharpe(aa) - zero_rate_sharpe(bb)
    return {
        "Annualized Mean Difference": float((a.mean() - b.mean()) * 12.0),
        "Mean Difference CI Low": float(np.quantile(mean_diffs, 0.025)),
        "Mean Difference CI High": float(np.quantile(mean_diffs, 0.975)),
        "Probability Mean Difference > 0": float((mean_diffs > 0).mean()),
        "Sharpe Difference": float(zero_rate_sharpe(a) - zero_rate_sharpe(b)),
        "Sharpe Difference CI Low": float(np.quantile(sharpe_diffs, 0.025)),
        "Sharpe Difference CI High": float(np.quantile(sharpe_diffs, 0.975)),
        "Probability Sharpe Difference > 0": float((sharpe_diffs > 0).mean()),
    }
