# Data provenance

`ff12_value_weighted_2010_2025.csv` is the fixed research snapshot used by the report.

- **Source:** Kenneth R. French Data Library, *12 Industry Portfolios*.
- **Series:** average value-weighted monthly returns, including dividends.
- **Coverage retained here:** January 2010 through September 2025.
- **Units in this CSV:** percentage points; `robust_portfolio.data.load_returns` converts them to decimal returns.
- **Columns:** NoDur, Durbl, Manuf, Enrgy, Chems, BusEq, Telcm, Utils, Shops, Hlth, Money and Other.

The repository versions the report's input. Because the French library revises historical portfolios when CRSP data change, a later download may differ. To create a new vintage, run `scripts/download_french_data.py` and rerun the research pipeline.

The loader checks for missing months, duplicate dates and missing returns.
