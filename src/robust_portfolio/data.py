from __future__ import annotations

from pathlib import Path
import pandas as pd

ASSET_COLUMNS = [
    "NoDur", "Durbl", "Manuf", "Enrgy", "Chems", "BusEq",
    "Telcm", "Utils", "Shops", "Hlth", "Money", "Other",
]


def load_returns(path: str | Path) -> pd.DataFrame:
    """Load and validate monthly industry returns, converting percent to decimal."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Return file not found: {path}")

    df = pd.read_csv(path, parse_dates=["date"])
    missing_columns = set(["date", *ASSET_COLUMNS]) - set(df.columns)
    if missing_columns:
        raise ValueError(f"Missing columns: {sorted(missing_columns)}")
    if df["date"].duplicated().any():
        raise ValueError("Duplicate dates found in return data")

    df = df.set_index("date").sort_index()[ASSET_COLUMNS]
    expected = pd.date_range(df.index.min(), df.index.max(), freq="MS")
    if not df.index.equals(expected):
        missing = expected.difference(df.index)
        raise ValueError(f"Monthly series is not contiguous; missing: {missing.tolist()}")
    if df.isna().any().any():
        raise ValueError("Missing return observations found")
    if (df.abs() > 100).any().any():
        raise ValueError("Return values appear malformed")

    return df.astype(float) / 100.0
