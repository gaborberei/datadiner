"""The numbers. Every function here returns a DataFrame and draws nothing.

Keeping the arithmetic separate from the rendering means each figure's data is
exportable and testable on its own, and the five cohort heatmaps are five
transforms of a single computation rather than five near-duplicate pipelines.

    from retentionkit.metrics import cohort_table, retention_curve

    cohort_table(am, kind="retention_rate")   # cohorts x age, % still active
    retention_curve(am)               # the average decay shape
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import sparse

# How many age columns a heatmap stays readable at, per grain.
MAX_AGE = {"day": 30, "week": 20, "month": 12}

# The curve is one line, not a grid of annotated cells, so it can run well past
# the heatmap's readable width — and it has to, because where retention flattens
# is often beyond week 20.
CURVE_MAX_AGE = {"day": 60, "week": 40, "month": 12}

KINDS = ("retention_rate", "retention_counts", "churn_rate",
         "churn_counts", "vs_average")

# The cohort-size column every ``cohort_table`` leads with. Named for what it
# counts — users whose *first* active period is that cohort — so the figures and
# their CSV twins agree on one word for it.
SIZE_COL = "Signups"


def _max_age(am, max_age=None, defaults=MAX_AGE):
    return max_age if max_age is not None else defaults.get(am.grain, 20)


def cohort_table(am, kind="retention_rate", max_age=None):
    """A cohort x age matrix — the data behind all five cohort heatmaps.

    Parameters
    ----------
    am : ActivityMatrix
    kind : one of
        ``rate``          % of the cohort still active at that age
        ``counts``        absolute active users
        ``churn_rate``    period-over-period change in rate (pp)
        ``churn_counts``  period-over-period change in users
        ``vs_average``    the cohort's rate minus the average rate at that age
    max_age : age columns to keep (default: readable width for the grain).

    Returns
    -------
    DataFrame indexed by cohort period, with a leading ``Signups`` column (the
    cohort size) followed by one column per age.

    Empty cells mean two different things and stay distinguishable: **0** is
    "observed, nobody active", **NaN** is "this cohort hasn't reached that age
    yet". Only cohorts with at least one member appear.
    """
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}, got {kind!r}")

    aged = am.cohort_age_counts()
    sizes = am.cohort_sizes().astype(float)
    keep = sizes > 0

    width = min(_max_age(am, max_age) + 1, aged.shape[1])
    counts = aged[keep, :width]
    sizes = sizes[keep]

    with np.errstate(invalid="ignore", divide="ignore"):
        rate = counts / sizes[:, None] * 100

    if kind == "retention_counts":
        values, ages = counts, np.arange(width)
    elif kind == "retention_rate":
        values, ages = rate, np.arange(width)
    elif kind == "churn_counts":
        values, ages = np.diff(counts, axis=1), np.arange(1, width)
    elif kind == "churn_rate":
        values, ages = np.diff(rate, axis=1), np.arange(1, width)
    else:  # vs_average
        with np.errstate(invalid="ignore"):
            values = rate - np.nanmean(rate, axis=0)
        ages = np.arange(width)

    labels = [lbl for lbl, k in zip(am.period_labels(), keep) if k]
    out = pd.DataFrame(values, index=pd.Index(labels, name="cohort"),
                       columns=ages)
    out.insert(0, SIZE_COL, sizes.astype(int))
    return out


def retention_curve(am, max_age=None, weighted=False):
    """The average decay shape across cohorts.

    Parameters
    ----------
    weighted : False averages the cohort *rates* (every cohort counts equally,
        which is what "the typical cohort" means); True pools the users first,
        so large cohorts dominate. The unweighted read is the default because a
        single huge acquisition spike otherwise defines the whole curve.
    max_age : ages to draw. Defaults to ``CURVE_MAX_AGE`` for the grain (40
        weeks), which runs past the heatmaps' width — the plateau a curve exists
        to show is usually beyond age 20.

    Returns
    -------
    DataFrame with ``age``, ``retention_pct``, ``cohorts`` (how many cohorts are
    old enough to contribute at that age) and ``users``.
    """
    aged = am.cohort_age_counts()
    sizes = am.cohort_sizes().astype(float)
    keep = sizes > 0
    width = min(_max_age(am, max_age, CURVE_MAX_AGE) + 1, aged.shape[1])
    counts, sizes = aged[keep, :width], sizes[keep]

    with np.errstate(invalid="ignore", divide="ignore"):
        rate = counts / sizes[:, None] * 100

    with np.errstate(invalid="ignore"):
        if weighted:
            pooled = np.nansum(counts, axis=0)
            base = np.where(np.isnan(counts), np.nan, sizes[:, None])
            pct = pooled / np.nansum(base, axis=0) * 100
        else:
            pct = np.nanmean(rate, axis=0)

    return pd.DataFrame({
        "age": np.arange(width),
        "retention_pct": pct,
        "cohorts": (~np.isnan(rate)).sum(axis=0),
        "users": np.nansum(counts, axis=0).astype(int),
    })


# A user absent for one period is At-Risk; a second consecutive absence books
# them as Churned. One skipped period is normal for a weekly-cadence product,
# so the forgiving definition is the one this package uses — everywhere.
CHURN_DEFINITION = (
    "A user is At-Risk after one missed {period}, and Churned after a second "
    "consecutive missed {period}. Churn is not final: a churned user who "
    "returns is counted as Resurrected."
)


def lifecycle_states(am):
    """Per-period New / Retained / Resurrected / At-Risk / Churned, + Quick Ratio.

    Returns
    -------
    DataFrame with one row per period:

    ``period``       period start
    ``New``          first active this period
    ``Retained``     active this period and the previous one
    ``Resurrected``  active now after being At-Risk or Churned
    ``At-Risk``      absent this period after being active last period
    ``Churned``      newly booked as churned (a second consecutive absence)
    ``Quick Ratio``  (New + Resurrected) / Churned. Above 1 the base grows,
                     below 1 it shrinks. NaN where nobody churned.

    The state machine is a loop over periods, but each step is a single sparse
    column operation, so it stays cheap however many users there are.
    """
    presence = am.presence.tocsc()
    n_periods = am.n_periods
    new_counts = am.cohort_sizes()

    def active_set(i):
        col = presence[:, i]
        return set(col.indices.tolist())

    records = []
    churned_pool, at_risk_pool = set(), set()
    cohort_of = am.cohort

    for i in range(n_periods):
        current = active_set(i)
        prev = active_set(i - 1) if i else set()

        new = {u for u in current if cohort_of[u] == i}
        returning = current - new
        resurrected = returning & (churned_pool | at_risk_pool)
        retained = returning - resurrected

        newly_inactive = prev - current
        newly_churned = at_risk_pool - current
        churned_pool = (churned_pool | newly_churned) - current
        at_risk_pool = newly_inactive

        records.append({
            "period": am.periods[i],
            "New": len(new),
            "Retained": len(retained),
            "Resurrected": len(resurrected),
            "At-Risk": len(at_risk_pool),
            "Churned": len(newly_churned),
        })

    out = pd.DataFrame(records)
    assert (out["New"].to_numpy() == new_counts).all(), "cohort/new mismatch"
    out["Quick Ratio"] = (
        (out["New"] + out["Resurrected"]) / out["Churned"].replace(0, np.nan)
    )
    return out


def usage_frequency(daily_am):
    """Average active days per month per user — the engagement cadence.

    Takes a matrix built at ``grain='day'`` and folds its columns into calendar
    months with one sparse product, so no groupby ever touches the raw log. The
    read this supports is what "active" should mean: a mass at 20+ days is a
    daily product, a mass at 4 is a weekly one.

    Returns
    -------
    DataFrame with ``user_id`` and ``avg_active_days_per_month``, one row per
    user. The denominator is the months the user was **active in** — a month
    they sat out entirely does not drag their cadence down, so this reads "how
    often, when they show up at all", which is the question the histogram is
    used to answer. (Dividing by every month since their first would mix cadence
    together with churn and report both as one number.)
    """
    if daily_am.grain != "day":
        raise ValueError(
            f"usage_frequency needs a daily matrix, got grain={daily_am.grain!r}; "
            f"build one with ActivityMatrix.build(df, grain='day')"
        )
    months = pd.DatetimeIndex(daily_am.periods).to_period("M")
    month_codes, month_index = pd.factorize(months, sort=True)

    fold = sparse.csr_matrix(
        (np.ones(len(month_codes)), (np.arange(len(month_codes)), month_codes)),
        shape=(len(month_codes), len(month_index)),
    )
    per_month = np.asarray((daily_am.presence @ fold).todense())

    # Average over the months the user was active in, not every month on the
    # calendar since they joined: a user who joined in December shouldn't average
    # in eleven months of zeros, and one who lapsed in June shouldn't have the
    # months they were gone counted as a slow cadence.
    totals = per_month.sum(axis=1)
    n_months = (per_month > 0).sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        avg = np.where(n_months > 0, totals / np.maximum(n_months, 1), np.nan)

    return pd.DataFrame({
        "user_id": daily_am.users,
        "avg_active_days_per_month": avg,
    })


# Below this many contributing cohorts a diagonal signal is too thin to call
# "simultaneous across cohorts".
_MIN_DIAGONAL_COHORTS = 3


def cohort_patterns(am, top=3):
    """Where the cohort matrix moves — a reading aid, not a conclusion.

    Points at the three signatures an analyst scans a heatmap for. It says
    *where* to look; the cause is still something to go and check.

    - ``horizontal`` — a cohort that beats or lags its peers overall. A small
      cohort retaining well is the "low volume, high quality" acquisition shape.
    - ``diagonal`` — a calendar period where many cohorts move together, the
      signature of a simultaneous event (launch, bug, outage).
    - ``vertical`` — a tenure age with a drop steeper than the smooth decay,
      the signature of a survival moment (trial end, renewal).

    Returns a dict of three lists of dicts, each sorted strongest-first.
    """
    dev = cohort_table(am, "vs_average")
    rate = cohort_table(am, "retention_rate")
    ages = [c for c in dev.columns if c != SIZE_COL]
    labels = list(dev.index)

    # Horizontal: each cohort's mean deviation from its same-age peers.
    row_dev = dev[ages].mean(axis=1)
    centre = row_dev.mean()
    sizes = dev[SIZE_COL]
    size_median = sizes.median()
    horizontal = []
    for label in labels:
        mag = row_dev[label] - centre
        if np.isnan(mag):
            continue
        small = sizes[label] <= size_median
        if mag > 0:
            hint = "retains above its peers"
            if small:
                hint += " despite a small size (low volume, high quality)"
        else:
            hint = "retains below its peers"
        horizontal.append({
            "where": label,
            "magnitude_pp": round(float(mag), 1),
            "size": int(sizes[label]),
            "hint": f"horizontal — this cohort {hint}",
        })
    horizontal.sort(key=lambda d: abs(d["magnitude_pp"]), reverse=True)

    # Diagonal: group deviations by the calendar period they land in.
    buckets = {}
    values = dev[ages].to_numpy()
    for i in range(values.shape[0]):
        for j, age in enumerate(ages):
            v = values[i, j]
            if not np.isnan(v):
                buckets.setdefault(i + int(age), []).append(v)
    diagonal = []
    for cal, vals in buckets.items():
        if len(vals) < _MIN_DIAGONAL_COHORTS:
            continue
        diagonal.append({
            "where": labels[min(cal, len(labels) - 1)],
            "magnitude_pp": round(float(np.mean(vals)), 1),
            "n_cohorts": len(vals),
            "hint": "diagonal — many cohorts move together: a simultaneous "
                    "event (launch, bug, outage)",
        })
    diagonal.sort(key=lambda d: abs(d["magnitude_pp"]), reverse=True)

    # Vertical: ages whose average drop exceeds the typical decay step. The
    # 0 -> 1 step is skipped: age 0 is 100% for every cohort by construction, so
    # that drop is the largest on every dataset ever and would crowd out the
    # tenure moments this scan exists to find.
    avg_by_age = rate[ages].mean(axis=0)
    drops, prev = {}, None
    for age in ages:
        cur = avg_by_age[age]
        if prev is not None and int(age) > 1 and not np.isnan(cur) and not np.isnan(prev):
            drops[age] = prev - cur
        prev = cur
    baseline = float(np.median(list(drops.values()))) if drops else 0.0
    vertical = [{
        "where": f"age {age}",
        "magnitude_pp": round(float(drop), 1),
        "excess_pp": round(float(drop - baseline), 1),
        "n_cohorts": int(rate[age].notna().sum()),
        "hint": "vertical — a drop steeper than the smooth decay: a survival "
                "moment (trial end, renewal)",
    } for age, drop in drops.items()]
    vertical.sort(key=lambda d: d["excess_pp"], reverse=True)

    return {
        "horizontal": horizontal[:top],
        "diagonal": diagonal[:top],
        "vertical": vertical[:top],
    }
