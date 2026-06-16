"""Shared I/O helpers for DataDiner analytics modules.

Every analytics submodule (retention, engagement, ...) works on an event log
with `date` and `user_id` columns. Load it once, here, so the schema contract
lives in one place.
"""

import pandas as pd


def load_events(path, date_col="date", user_col="user_id"):
    """Load an event-log CSV with parsed dates, validating the core columns.

    Parameters
    ----------
    path : str
        Path to the CSV.
    date_col, user_col : str
        Source column names; renamed to the canonical `date` / `user_id`.

    Returns
    -------
    DataFrame with `date` (datetime64) and `user_id`.

    Raises
    ------
    ValueError if a required column is missing.
    """
    df = pd.read_csv(path)
    missing = {date_col, user_col} - set(df.columns)
    if missing:
        raise ValueError(
            f"{path}: missing required column(s) {sorted(missing)}; "
            f"found {list(df.columns)}"
        )
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.rename(columns={date_col: "date", user_col: "user_id"})
    return df


def summarize_events(df):
    """Return a one-line shape summary of an event log (rows, users, date span)."""
    return {
        "rows": len(df),
        "users": df["user_id"].nunique(),
        "start": df["date"].min(),
        "end": df["date"].max(),
    }
