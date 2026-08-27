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

