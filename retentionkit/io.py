"""Loading a daily activity log, and reading its shape honestly.

The expected input is one row per user per active day:

    date, user_id, event_type, event_count, <segment columns...>

Only `date` and `user_id` are required. Everything here is about getting that
file into memory cheaply and then saying what is actually in it — above all how
*sparse* it is, since that governs whether weekly or monthly is the honest
period to compute retention on.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .matrix import DEFAULT_WEEK_START, _period_start, period_axis


def load_activity(path, date_col="date", user_col="user_id", dtype=None,
                  usecols=None):
    """Load an activity CSV with parsed dates and memory-frugal dtypes.

    Low-cardinality string columns (event_type, segments) are read as
    ``category`` and counts as unsigned ints, which is what keeps a
    multi-million-row log to a few hundred MB instead of several GB.

    Parameters
    ----------
    path : str | Path            the CSV.
    date_col, user_col : str     source names, renamed to canonical
                                 ``date`` / ``user_id``.
    dtype : dict, optional       overrides for the inferred dtypes.
    usecols : list, optional     read only these columns.

    Returns
    -------
    DataFrame with ``date`` (datetime64), ``user_id``, and every other column
    the file carried.
    """
    path = Path(path)
    header = pd.read_csv(path, nrows=0, usecols=usecols)
    cols = list(header.columns)
    for required in (date_col, user_col):
        if required not in cols:
            raise ValueError(
                f"{path}: missing required column {required!r}; found {cols}"
            )

    # Sample the head to decide which string columns are worth categorizing.
    sample = pd.read_csv(path, nrows=50_000, usecols=usecols)
    # user_id is high-cardinality but massively repeated — category turns a
    # per-row Python string into a 4-byte code, which is most of the memory win.
    inferred = {user_col: "category"}
    for col in cols:
        if col in (date_col, user_col):
            continue
        series = sample[col]
        if pd.api.types.is_numeric_dtype(series):
            if (series.dropna() >= 0).all() and (series.dropna() % 1 == 0).all():
                inferred[col] = "uint32"
        elif series.nunique(dropna=True) <= 50:
            inferred[col] = "category"
    inferred.update(dtype or {})

    df = pd.read_csv(path, dtype=inferred, usecols=usecols,
                     parse_dates=[date_col])
    df = df.rename(columns={date_col: "date", user_col: "user_id"})
    if not pd.api.types.is_datetime64_any_dtype(df["date"]):
        df["date"] = pd.to_datetime(df["date"])
    return df


# Where a typical return gap puts a product. The bands are deliberately wide:
# the question is which period retention should be measured on, and that answer
# is robust to a day either way.
_CADENCE_BANDS = ((2, "daily"), (10, "weekly"), (35, "monthly"))


def natural_frequency(df, active_event=None):
    """How often users actually come back, from the gaps between active days.

    This is the fact that should decide the retention period. Measuring weekly
    retention on a product people open twice a year manufactures churn; measuring
    monthly retention on a daily habit hides it.

    Each user's *median* gap is taken first, then users are binned — so a handful
    of heavy players can't drag the population read toward "daily". Users with a
    single active day contribute no gap and are excluded (they have no cadence).

    Returns
    -------
    dict with ``cadence`` ('daily' | 'weekly' | 'monthly' | 'rarer'), the modal
    band; ``median_gap_days``; ``shares`` per band; and ``users_measured``.
    """
    if active_event is not None and "event_type" in df.columns:
        df = df[df["event_type"] == active_event]

    days = df[["user_id", "date"]].drop_duplicates().sort_values(["user_id", "date"])
    gaps = days.groupby("user_id", observed=True)["date"].diff().dt.days
    per_user = gaps.groupby(days["user_id"], observed=True).median().dropna()

    if per_user.empty:
        return {"cadence": None, "median_gap_days": None, "shares": {},
                "users_measured": 0}

    edges = [0] + [edge for edge, _ in _CADENCE_BANDS] + [np.inf]
    labels = [name for _, name in _CADENCE_BANDS] + ["rarer"]
    banded = pd.cut(per_user, edges, labels=labels)
    shares = banded.value_counts(normalize=True).reindex(labels).fillna(0)

    return {
        "cadence": str(shares.idxmax()),
        "median_gap_days": float(per_user.median()),
        "shares": {k: round(float(v), 3) for k, v in shares.items()},
        "users_measured": int(len(per_user)),
    }


def quality_report(df, grain="week", week_start=DEFAULT_WEEK_START,
                   count_col="event_count", active_event=None):
    """Describe the log's shape, leading with sparsity.

    Returns a dict of measurements plus a ``flags`` list of plain-English
    observations. Nothing here fails or blocks — these are things for an analyst
    to weigh, not a gate to pass.

    Keys
    ----
    rows, users, first_day, last_day, days_spanned
    grain, periods            the period axis the retention views will use
    density                   share of (user, period) cells carrying activity
    users_with_gaps           users inactive for >=1 period between their own
                              first and last activity (the resurrection base)
    empty_periods             calendar periods where nobody was active at all
    median_active_periods     typical periods-active per user
    single_period_users       users seen in exactly one period (never retained)
    duplicate_rows            exact duplicates on (date, user_id, event_type)
    natural_frequency         :func:`natural_frequency` — the cadence users
                              actually keep, which is what should pick ``grain``
    """
    out = {
        "rows": int(len(df)),
        "users": int(df["user_id"].nunique()),
        "first_day": df["date"].min(),
        "last_day": df["date"].max(),
        "grain": grain,
    }
    out["days_spanned"] = int((out["last_day"] - out["first_day"]).days) + 1

    periods = period_axis(df["date"], grain, week_start)
    starts = _period_start(df["date"], grain, week_start)
    codes = periods.get_indexer(starts)
    user_codes, _ = pd.factorize(df["user_id"], sort=True)

    out["periods"] = int(len(periods))

    pairs = pd.DataFrame({"u": user_codes, "p": codes}).drop_duplicates()
    cells = out["users"] * out["periods"]
    out["density"] = float(len(pairs) / cells) if cells else float("nan")

    span = pairs.groupby("u")["p"].agg(["min", "max", "count"])
    lifetime = span["max"] - span["min"] + 1
    out["users_with_gaps"] = int((lifetime > span["count"]).sum())
    out["median_active_periods"] = float(span["count"].median())
    out["single_period_users"] = int((span["count"] == 1).sum())

    seen = np.zeros(len(periods), dtype=bool)
    seen[np.unique(codes)] = True
    out["empty_periods"] = [str(p.date()) for p in periods[~seen]]

    out["natural_frequency"] = natural_frequency(df, active_event=active_event)

    key = [c for c in ("date", "user_id", "event_type") if c in df.columns]
    out["duplicate_rows"] = int(df.duplicated(key).sum())

    out["flags"] = _flags(out, df, count_col)
    return out


def _flags(m, df, count_col):
    """Turn the measurements into things worth saying out loud."""
    flags = []
    period = m["grain"]

    flags.append(
        f"Panel is {m['density']:.1%} dense — of {m['users']:,} users x "
        f"{m['periods']} {period}s, activity lands in {m['density']:.1%} of "
        f"cells. Everything else is a real zero, not missing data."
    )

    nf = m.get("natural_frequency") or {}
    cadence = nf.get("cadence")
    if cadence:
        share = nf["shares"].get(cadence, 0)
        flags.append(
            f"Natural frequency looks **{cadence}**: the median user returns "
            f"every {nf['median_gap_days']:.0f} days, and {share:.0%} of the "
            f"{nf['users_measured']:,} users with a measurable cadence fall in "
            f"that band. This is what should pick the retention period."
        )
        expected = {"daily": "day", "weekly": "week", "monthly": "month"}.get(cadence)
        if expected and expected != period:
            flags.append(
                f"⚠️ Retention is being computed on {period}s while users return "
                f"on a {cadence} rhythm. A period shorter than the rhythm "
                f"manufactures churn; a longer one hides it. Consider "
                f"grain='{expected}'."
            )

    if m["density"] < 0.05 and period == "week":
        flags.append(
            f"Very sparse at {period} grain: the median user is active in only "
            f"{m['median_active_periods']:.0f} of {m['periods']} {period}s. "
            f"Worth checking whether monthly is the honest retention period."
        )
    if m["empty_periods"]:
        flags.append(
            f"{len(m['empty_periods'])} calendar {period}(s) with zero activity "
            f"({', '.join(m['empty_periods'][:3])}"
            f"{'...' if len(m['empty_periods']) > 3 else ''}). They keep their "
            f"column so cohort ages stay aligned — worth investigating whether "
            f"this is a real outage or a collection gap."
        )
    share_single = m["single_period_users"] / m["users"] if m["users"] else 0
    if share_single > 0.2:
        flags.append(
            f"{share_single:.0%} of users appear in exactly one {period} and can "
            f"never be retained — they set a ceiling on every retention number."
        )
    if m["users_with_gaps"]:
        flags.append(
            f"{m['users_with_gaps']:,} users go inactive and come back — "
            f"resurrection is real here, so churn should not be read as final."
        )
    if m["duplicate_rows"]:
        flags.append(
            f"{m['duplicate_rows']:,} duplicate rows on (date, user_id, "
            f"event_type) — confirm they are benign before trusting volume."
        )
    if count_col in df.columns:
        negative = int((pd.to_numeric(df[count_col], errors="coerce") < 0).sum())
        if negative:
            flags.append(f"{negative:,} rows with a negative {count_col}.")
    nulls = int(df["user_id"].isna().sum())
    if nulls:
        flags.append(f"{nulls:,} rows with a null user_id — they are dropped.")
    return flags


def format_quality_report(m):
    """Render :func:`quality_report` output as a short Markdown block."""
    lines = [
        f"- **Rows:** {m['rows']:,} · **Users:** {m['users']:,}",
        f"- **Span:** {m['first_day']:%Y-%m-%d} → {m['last_day']:%Y-%m-%d} "
        f"({m['days_spanned']:,} days, {m['periods']} {m['grain']}s)",
        f"- **Panel density:** {m['density']:.1%} · median "
        f"{m['median_active_periods']:.0f} active {m['grain']}s per user",
    ]
    nf = m.get("natural_frequency") or {}
    if nf.get("cadence"):
        lines.append(
            f"- **Natural frequency:** {nf['cadence']} "
            f"(median return gap {nf['median_gap_days']:.0f} days)"
        )
    lines.append("")
    lines += [f"- {flag}" for flag in m["flags"]]
    return "\n".join(lines)
