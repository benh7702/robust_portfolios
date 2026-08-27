#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from robust_portfolio.backtest import BacktestConfig, run_walk_forward
from robust_portfolio.data import load_returns
from robust_portfolio.metrics import (
    performance_summary,
    moving_block_bootstrap_difference,
    cvar_loss,
    annualized_return,
    annualized_volatility,
    zero_rate_sharpe,
)
from robust_portfolio.plots import (
    plot_average_weights,
    plot_cumulative_wealth,
    plot_drawdowns,
    plot_risk_return,
    plot_rolling_volatility,
    plot_turnover,
)


def regime_summary(net_returns: pd.DataFrame, asset_returns: pd.DataFrame) -> pd.DataFrame:
    proxy = asset_returns.mean(axis=1).reindex(net_returns.index)
    trailing_vol = proxy.rolling(12, min_periods=6).std()
    cutoff = trailing_vol.median()
    regime = pd.Series(np.where(trailing_vol > cutoff, "High volatility", "Lower volatility"), index=net_returns.index)
    records = []
    for name in net_returns.columns:
        for regime_name in ["High volatility", "Lower volatility"]:
            r = net_returns.loc[regime == regime_name, name].dropna()
            records.append({
                "Strategy": name,
                "Regime": regime_name,
                "Months": len(r),
                "Annualized Return": annualized_return(r),
                "Annualized Volatility": annualized_volatility(r),
                "Zero-Rate Sharpe": zero_rate_sharpe(r),
                "95% CVaR Loss": cvar_loss(r),
            })
    return pd.DataFrame(records)


def stress_summary(net_returns: pd.DataFrame) -> pd.DataFrame:
    periods = {
        "COVID sell-off (2020-02 to 2020-03)": ("2020-02-01", "2020-03-01"),
        "COVID rebound (2020-04 to 2020-08)": ("2020-04-01", "2020-08-01"),
        "2022 tightening sell-off (2022-01 to 2022-10)": ("2022-01-01", "2022-10-01"),
    }
    records = []
    for label, (start, end) in periods.items():
        sliced = net_returns.loc[start:end]
        for strategy in net_returns.columns:
            records.append({
                "Period": label,
                "Strategy": strategy,
                "Cumulative Return": float((1.0 + sliced[strategy]).prod() - 1.0),
                "Worst Month": float(sliced[strategy].min()),
            })
    return pd.DataFrame(records)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=ROOT / "data" / "ff12_value_weighted_2010_2025.csv")
    parser.add_argument("--results", type=Path, default=ROOT / "results")
    parser.add_argument("--bootstrap-reps", type=int, default=2000)
    args = parser.parse_args()
    args.results.mkdir(parents=True, exist_ok=True)
    figures = args.results / "figures"
    figures.mkdir(parents=True, exist_ok=True)

    returns = load_returns(args.data)
    config = BacktestConfig()
    result = run_walk_forward(returns, config)
    summary = performance_summary(result.net_returns, result.gross_returns, result.turnover, result.weights, config.alpha)

    result.net_returns.to_csv(args.results / "monthly_net_returns.csv")
    result.gross_returns.to_csv(args.results / "monthly_gross_returns.csv")
    result.turnover.to_csv(args.results / "monthly_turnover.csv")
    result.costs.to_csv(args.results / "monthly_costs.csv")
    summary.to_csv(args.results / "performance_summary.csv")
    result.hyperparameters.to_csv(args.results / "selected_hyperparameters.csv")
    result.optimizer_failures.to_csv(args.results / "optimizer_failures.csv", index=False)
    for strategy, frame in result.weights.items():
        safe = strategy.lower().replace(" ", "_").replace("-", "_")
        frame.to_csv(args.results / f"weights_{safe}.csv")

    bootstrap_records = []
    benchmark = result.net_returns["Equal Weight"]
    for strategy in result.net_returns.columns:
        if strategy == "Equal Weight":
            continue
        record = {"Strategy": strategy}
        record.update(moving_block_bootstrap_difference(
            result.net_returns[strategy], benchmark,
            reps=args.bootstrap_reps, block_length=6, seed=7))
        bootstrap_records.append(record)
    bootstrap = pd.DataFrame(bootstrap_records).set_index("Strategy")
    bootstrap.to_csv(args.results / "bootstrap_vs_equal_weight.csv")

    regimes = regime_summary(result.net_returns, returns)
    regimes.to_csv(args.results / "regime_summary.csv", index=False)
    stress = stress_summary(result.net_returns)
    stress.to_csv(args.results / "stress_period_summary.csv", index=False)

    plot_cumulative_wealth(result.net_returns, figures / "cumulative_wealth.png")
    plot_drawdowns(result.net_returns, figures / "drawdowns.png")
    plot_rolling_volatility(result.net_returns, figures / "rolling_volatility.png")
    plot_risk_return(result.net_returns, figures / "risk_return.png")
    plot_turnover(result.turnover, figures / "turnover.png")
    plot_average_weights(result.weights, figures / "average_weights.png")

    metadata = {
        "data_start": str(returns.index.min().date()),
        "data_end": str(returns.index.max().date()),
        "out_of_sample_start": str(result.net_returns.index.min().date()),
        "out_of_sample_end": str(result.net_returns.index.max().date()),
        "out_of_sample_months": int(len(result.net_returns)),
        "assets": list(returns.columns),
        "config": config.__dict__,
        "optimizer_failures": int(len(result.optimizer_failures)),
    }
    (args.results / "run_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(summary.round(4).to_string())
    print(f"\nWrote results to {args.results}")


if __name__ == "__main__":
    main()
