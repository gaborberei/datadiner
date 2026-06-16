"""Shared I/O helpers for DataDiner analytics modules.

Every analytics submodule (retention, engagement, ...) works on an event log
with `date` and `user_id` columns. Load it once, here, so the schema contract
lives in one place.
"""

import pandas as pd


def load_events(path, date_col="date", user_col="user_id", dtype=None):
    """Load an event-log CSV with parsed dates, validating the core columns.

    Parameters
    ----------
    path : str
        Path to the CSV.
    date_col, user_col : str
        Source column names; renamed to the canonical `date` / `user_id`.
    dtype : dict, optional
        Column dtype hints passed to `pd.read_csv` — use to honor a dataset
        brief's `schema.dtypes` (e.g. `{'app_version': str}`).

    Returns
    -------
    DataFrame with `date` (datetime64), `user_id`, and any other columns in the
    CSV preserved (event_type, segment dimensions, ...) so `segment_by=` works.

    Raises
    ------
    ValueError if a required column is missing.
    """
    df = pd.read_csv(path, dtype=dtype)
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
