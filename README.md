# Estimation Error in Portfolio Optimisation


## Headline result

Across the January 2015-September 2025 out-of-sample period, the equal-weight portfolio produced the highest compound return (11.43% annualised). The Wasserstein-robust CVaR portfolio had the highest zero-rate Sharpe ratio among the four optimisation methods (0.766), just below equal weight at 0.773; its difference from equal weight was not statistically distinguishable in the moving-block bootstrap. Historical CVaR and shrinkage MVO substantially reduced estimated tail loss, volatility and drawdown relative to sample MVO. Sample MVO had the highest turnover and the weakest overall performance.

Regularisation and tail-risk objectives stabilised the optimiser, but the simple 1/N benchmark remained difficult to beat on compound return.

## Strategies

1. **Equal Weight** - monthly 1/N rebalancing.
2. **Sample MVO** - sample mean and covariance in a long-only Markowitz programme.
3. **Shrinkage MVO** - empirical-Bayes mean shrinkage and Ledoit-Wolf covariance.
4. **Historical Mean-CVaR** - empirical 95% CVaR minimisation, subject to an estimated-return floor equal to the empirical-Bayes expected return of the 1/N portfolio.
5. **Wasserstein Robust CVaR** - the same return floor, with a 1-Wasserstein ambiguity penalty under an L1 ground metric.

All strategies are long-only, fully invested, capped at 35% per industry and evaluated after 10 basis points of one-way turnover cost.

## Design

- **Assets:** 12 value-weighted US industry portfolios.
- **Bundled data:** January 2010-September 2025 monthly returns.
- **Out-of-sample test:** January 2015-September 2025 (129 months).
- **Estimation window:** rolling 60 months.
- **Internal validation:** final 12 months of each estimation window.
- **Selection:** MVO risk aversion and Wasserstein radius are selected only with internal validation data.
- **Inference:** 2,000-draw circular moving-block bootstrap with six-month blocks.
- **Risk-free convention:** reported Sharpe ratios use a zero monthly risk-free rate and are labelled accordingly.

## Reproduce

```bash
cd robust_portfolio_project
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
PYTHONPATH=src pytest -q
PYTHONPATH=src python scripts/run_research.py
python report/build_empirical_report.py
```

The run writes all result tables to `results/` and all figures to `results/figures/`.

To refresh the official dataset in an internet-connected environment:

```bash
python scripts/download_french_data.py \
  --output data/ff12_value_weighted_current.csv \
  --start 2010-01
PYTHONPATH=src python scripts/run_research.py \
  --data data/ff12_value_weighted_current.csv
```

The downloader uses the Kenneth R. French Data Library ZIP endpoint. The report uses the bundled September 2025 snapshot because historical returns may change when the underlying CRSP database is revised. Treat a refreshed run as a new data vintage.

## Repository layout

```text
robust_portfolio_project/
├── data/
│   └── ff12_value_weighted_2010_2025.csv
├── report/
│   ├── Ben_Heskin_Robust_Portfolio_Empirical_Report.docx
│   └── Ben_Heskin_Robust_Portfolio_Empirical_Report.pdf
├── results/
│   ├── figures/
│   ├── performance_summary.csv
│   ├── bootstrap_vs_equal_weight.csv
│   ├── regime_summary.csv
│   ├── stress_period_summary.csv
│   ├── monthly_net_returns.csv
│   ├── monthly_turnover.csv
│   └── weights_*.csv
├── scripts/
│   ├── download_french_data.py
│   └── run_research.py
├── src/robust_portfolio/
│   ├── data.py
│   ├── estimators.py
│   ├── optimizers.py
│   ├── backtest.py
│   ├── metrics.py
│   └── plots.py
└── tests/test_core.py
```

## Important interpretation limits

- These are research portfolios, not directly investable securities.
- The universe is industry-only and does not include bonds, cash or international assets.
- Monthly data provide a limited number of observations for 95% CVaR estimation.
- The Wasserstein radius is selected empirically; it is not claimed to be a formal finite-sample confidence radius.
- A zero risk-free rate is used for the labelled reward-to-risk statistic.
- Backtested results are not investment advice and do not imply future performance.

## References

- DeMiguel, V., Garlappi, L. and Uppal, R. (2009). “Optimal Versus Naive Diversification: How Inefficient Is the 1/N Portfolio Strategy?” *Review of Financial Studies*, 22(5), 1915-1953.
- Ledoit, O. and Wolf, M. (2004). “A Well-Conditioned Estimator for Large-Dimensional Covariance Matrices.” *Journal of Multivariate Analysis*, 88(2), 365-411.
- Markowitz, H. (1952). “Portfolio Selection.” *Journal of Finance*, 7(1), 77-91.
- Mohajerin Esfahani, P. and Kuhn, D. (2018). “Data-Driven Distributionally Robust Optimization Using the Wasserstein Metric.” *Mathematical Programming*, 171, 115-166.
- Rockafellar, R. T. and Uryasev, S. (2000). “Optimization of Conditional Value-at-Risk.” *Journal of Risk*, 2(3), 21-41.
