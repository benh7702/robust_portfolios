#!/usr/bin/env python3
"""Download and parse Kenneth French's current 12-industry dataset."""
from __future__ import annotations

import argparse
from io import BytesIO, StringIO
from pathlib import Path
import re
import urllib.request
import zipfile
import pandas as pd

URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/12_Industry_Portfolios_CSV.zip"
COLUMNS = ["NoDur", "Durbl", "Manuf", "Enrgy", "Chems", "BusEq", "Telcm", "Utils", "Shops", "Hlth", "Money", "Other"]


def parse_monthly_value_weighted(text: str) -> pd.DataFrame:
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if "Average Value Weighted Returns -- Monthly" in line)
    rows = []
    for line in lines[start + 1:]:
        if "Average Equal Weighted Returns -- Monthly" in line:
            break
        fields = [field.strip() for field in line.split(",")]
        if fields and re.fullmatch(r"\d{6}", fields[0]) and len(fields) >= 13:
            rows.append(fields[:13])
    if not rows:
        raise ValueError("Could not locate monthly value-weighted return rows")
    frame = pd.DataFrame(rows, columns=["date", *COLUMNS])
    frame["date"] = pd.to_datetime(frame["date"], format="%Y%m")
    for column in COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    return frame


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("data/ff12_value_weighted_current.csv"))
    parser.add_argument("--start", default="2010-01")
    args = parser.parse_args()
    with urllib.request.urlopen(URL, timeout=60) as response:
        payload = response.read()
    with zipfile.ZipFile(BytesIO(payload)) as archive:
        name = next(n for n in archive.namelist() if n.lower().endswith(".csv"))
        text = archive.read(name).decode("utf-8", errors="replace")
    frame = parse_monthly_value_weighted(text)
    frame = frame.loc[frame["date"] >= pd.Timestamp(args.start)].copy()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.output, index=False, date_format="%Y-%m")
    print(f"Wrote {len(frame)} rows to {args.output}")


if __name__ == "__main__":
    main()
