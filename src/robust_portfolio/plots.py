from __future__ import annotations

from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .metrics import drawdown_series, wealth_index, annualized_return, annualized_volatility


def _save(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_cumulative_wealth(net_returns: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5.5))
    for column in net_returns.columns:
        ax.plot(net_returns.index, wealth_index(net_returns[column]), label=column, linewidth=1.7)
    ax.set_title("Out-of-Sample Growth of $1 after Transaction Costs")
    ax.set_ylabel("Wealth index")
    ax.set_xlabel("")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8, ncol=2)
    _save(fig, path)


def plot_drawdowns(net_returns: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5.3))
    for column in net_returns.columns:
        ax.plot(net_returns.index, drawdown_series(net_returns[column]), label=column, linewidth=1.5)
    ax.set_title("Out-of-Sample Drawdowns")
    ax.set_ylabel("Drawdown")
    ax.set_xlabel("")
    ax.yaxis.set_major_formatter(lambda y, _: f"{y:.0%}")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8, ncol=2)
    _save(fig, path)


def plot_rolling_volatility(net_returns: pd.DataFrame, path: Path) -> None:
    rolling = net_returns.rolling(12).std() * np.sqrt(12)
    fig, ax = plt.subplots(figsize=(10, 5.3))
    for column in rolling.columns:
        ax.plot(rolling.index, rolling[column], label=column, linewidth=1.5)
    ax.set_title("Rolling 12-Month Annualized Volatility")
    ax.set_ylabel("Volatility")
    ax.set_xlabel("")
    ax.yaxis.set_major_formatter(lambda y, _: f"{y:.0%}")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8, ncol=2)
    _save(fig, path)


def plot_risk_return(net_returns: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.8, 5.4))
    for strategy in net_returns.columns:
        x = annualized_volatility(net_returns[strategy])
        y = annualized_return(net_returns[strategy])
        ax.scatter(x, y, s=55)
        ax.annotate(strategy, (x, y), xytext=(5, 4), textcoords="offset points", fontsize=8)
    ax.set_title("Out-of-Sample Risk and Compound Return")
    ax.set_xlabel("Annualized volatility")
    ax.set_ylabel("Annualized compound return")
    ax.xaxis.set_major_formatter(lambda x, _: f"{x:.0%}")
    ax.yaxis.set_major_formatter(lambda y, _: f"{y:.0%}")
    ax.grid(alpha=0.25)
    _save(fig, path)


def plot_turnover(turnover: pd.DataFrame, path: Path) -> None:
    means = turnover.mean().sort_values()
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    ax.barh(means.index, means.values)
    ax.set_title("Average Monthly One-Way Turnover")
    ax.set_xlabel("Turnover")
    ax.xaxis.set_major_formatter(lambda x, _: f"{x:.0%}")
    ax.grid(axis="x", alpha=0.25)
    _save(fig, path)


def plot_average_weights(weights: dict[str, pd.DataFrame], path: Path) -> None:
    strategies = list(weights)
    assets = list(next(iter(weights.values())).columns)
    matrix = np.vstack([weights[s].mean().to_numpy() for s in strategies])
    fig, ax = plt.subplots(figsize=(10, 4.6))
    image = ax.imshow(matrix, aspect="auto")
    ax.set_xticks(np.arange(len(assets)), labels=assets, rotation=45, ha="right")
    ax.set_yticks(np.arange(len(strategies)), labels=strategies)
    ax.set_title("Average Out-of-Sample Portfolio Weights")
    cbar = fig.colorbar(image, ax=ax)
    cbar.set_label("Average weight")
    _save(fig, path)
