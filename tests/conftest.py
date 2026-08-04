"""Fixtures and the independent reference implementation the sparse core is
checked against."""

import numpy as np
import pandas as pd
import pytest

from retentionkit.matrix import ActivityMatrix, DEFAULT_WEEK_START, _period_start


@pytest.fixture(autouse=True)
def close_figures():
    """Close every figure a test opened.

    ``Run.section`` closes the figures it saves, but a test that calls ``plots``
    directly leaves them open, and matplotlib warns once past 20. Imported lazily
    so ``retentionkit.plots`` has already selected the Agg backend.
    """
    yield
    import matplotlib.pyplot as plt
    plt.close("all")


@pytest.fixture
def small_log():
    """A hand-built log with the awkward cases written in on purpose.

    - ``gap_user`` is active, disappears for two weeks, and comes back
      (resurrection, and a gap that must read as zeros).
    - ``one_shot`` appears once and never returns.
    - week 3 (2024-01-22) has **no activity at all** — the empty calendar period
      that a factorize-based axis would silently delete.
    - ``late_user`` joins in the last week, so its cohort is censored almost
      immediately.
    """
    rows = [
        # user,        dates,                                       platform
        ("steady",     ["2024-01-01", "2024-01-08", "2024-01-15",
                        "2024-01-29", "2024-02-05"],                "mobile"),
        ("gap_user",   ["2024-01-01", "2024-01-08", "2024-02-05"],  "desktop"),
        ("one_shot",   ["2024-01-01"],                              "mobile"),
        ("second_wk",  ["2024-01-08", "2024-01-15", "2024-01-29"],  "desktop"),
        ("late_user",  ["2024-02-05"],                              "mobile"),
    ]
    records = []
    for user, dates, platform in rows:
        for i, date in enumerate(dates):
            records.append({
                "date": date, "user_id": user, "event_type": "core",
                "event_count": i + 1, "platform": platform,
            })
    # A non-core event that must be excluded when active_event='core'.
    records.append({"date": "2024-01-22", "user_id": "steady",
                    "event_type": "noise", "event_count": 9, "platform": "mobile"})
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    return df


@pytest.fixture
def weekly(small_log):
    return ActivityMatrix.build(small_log, grain="week", active_event="core",
                                segment_cols=["platform"])


def naive_cohort_counts(df, grain="week", active_event=None,
                        week_start=DEFAULT_WEEK_START):
    """A plain pandas cohort table, written independently of the sparse path.

    Deliberately slow and obvious: group to (user, period), take each user's
    first period as their cohort, count distinct users per (cohort, age), and
    mark as NaN anything the data could not have observed. If the sparse
    implementation disagrees with this, the sparse one is wrong.

    Returns (DataFrame indexed by cohort period with age columns, sizes Series).
    """
    df = df.copy()
    if active_event is not None:
        df = df[df["event_type"] == active_event]
    df["period"] = _period_start(df["date"], grain, week_start)

    pairs = df[["user_id", "period"]].drop_duplicates()
    first = pairs.groupby("user_id")["period"].min().rename("cohort")
    pairs = pairs.join(first, on="user_id")

    # A complete period axis, built by hand here too, then ages as positions.
    all_periods = sorted(
        pd.date_range(df["period"].min(), df["period"].max(),
                      freq="7D" if grain == "week"
                      else {"day": "D", "month": "MS"}[grain])
    )
    position = {p: i for i, p in enumerate(all_periods)}
    pairs["age"] = pairs["period"].map(position) - pairs["cohort"].map(position)

    counts = (pairs.groupby(["cohort", "age"])["user_id"].nunique()
              .unstack(fill_value=0))
    counts = counts.reindex(columns=range(len(all_periods)), fill_value=0)
    sizes = pairs[pairs["age"] == 0].groupby("cohort")["user_id"].nunique()

    # Censor: a cohort starting at position c can only be observed for
    # len(all_periods) - c ages.
    censored = counts.astype(float)
    for cohort in censored.index:
        observable = len(all_periods) - position[cohort]
        censored.loc[cohort, [a for a in censored.columns if a >= observable]] = np.nan
    return censored, sizes
