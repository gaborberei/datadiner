"""Tempo case — reference metric implementation.

Recomputes every ground-truth figure quoted in SOLUTION.md, straight from the
activity log, using the `datadiner` package. Run this before grading a
submission and diff your own numbers against it.

    python case_metrics.py [path/to/chess_dot_com_retention_article_weekly.csv]

With no argument it walks up from this file looking for the repo root, then
searches for the dataset. This prints summary statistics by design — it is a
verification harness, not an analysis notebook.

Grain note: the log is already weekly — one row per player per active week, with
each `date` the Saturday that starts the week. Week 52 starts 2024-12-28 and
covers through 2025-01-03, which is why the max date is not the end of the span.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# instructor/ -> <dataset>/ -> datasets/ -> repo root
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from datadiner.io import load_events                       # noqa: E402
from datadiner.retention import cohort_matrix, weekly_rates  # noqa: E402

EXPECTED = {"rows": 1_059_597, "users": 124_333, "weeks": 52,
            "first": "2024-01-06", "last": "2024-12-28"}

CANDIDATES = [
    "datasets/chess_dot_com_retention_article/"
    "chess_dot_com_retention_article_weekly.csv",
    "**/chess_dot_com_retention_article_weekly.csv",
]

# The case anchors weeks to Saturday 2024-01-06; datadiner buckets on its own
# weekly period. Because consecutive Saturdays fall in consecutive buckets the
# mapping is 1:1, so this only relabels the index back to the case's dates.
WEEK_STARTS = pd.date_range("2024-01-06", "2025-01-03", freq="7D")
_RELABEL = {ts.to_period("W").start_time: ts.strftime("%Y-%m-%d")
            for ts in WEEK_STARTS}


def locate_dataset(explicit=None):
    """Find the activity log relative to the repo this file lives in."""
    if explicit:
        path = Path(explicit).expanduser()
        if not path.exists():
            sys.exit(f"Not found: {path}")
        return path

    for root in [REPO_ROOT, *REPO_ROOT.parents]:
        for pattern in CANDIDATES:
            hits = sorted(root.glob(pattern))
            if hits:
                return hits[0]
    sys.exit(
        "Could not locate chess_dot_com_retention_article.csv.\n"
        "Pass the path explicitly: python case_metrics.py <path>"
    )


def validate(activity_df, path):
    rows, users = len(activity_df), activity_df.user_id.nunique()
    weeks = activity_df.date.nunique()
    first, last = activity_df.date.min().date(), activity_df.date.max().date()
    saturdays = set(activity_df.date.dt.day_name()) == {"Saturday"}
    ok = (rows == EXPECTED["rows"] and users == EXPECTED["users"]
          and weeks == EXPECTED["weeks"] and saturdays
          and str(first) == EXPECTED["first"] and str(last) == EXPECTED["last"])
    print("DATA VALIDATION")
    print(f"  file  : {path}")
    print(f"  rows  : {rows:,} (expected {EXPECTED['rows']:,})")
    print(f"  users : {users:,} (expected {EXPECTED['users']:,})")
    print(f"  weeks : {weeks} (expected {EXPECTED['weeks']}), all Saturday-anchored: {saturdays}")
    print(f"  range : {first} -> {last} (week 52 covers through 2025-01-03)")
    print(f"  status: {'PASS' if ok else 'FAIL - wrong dataset generation, do not grade'}")
    return ok


def relabel(frame):
    """Restore the case's Saturday week labels on a datadiner-indexed frame."""
    frame = frame.copy()
    frame.index = [_RELABEL.get(pd.Timestamp(i), i) for i in frame.index]
    return frame


def report(rates, rate_matrix, curve):
    weeks = rates.index

    print("\nQ1 - PRODUCT HEALTH")
    print("  retention curve  " + "  ".join(
        f"w{n}={curve[n]:.1f}%" for n in (1, 4, 8, 12, 20, 30, 40) if n in curve))
    print(f"  plateau (w30-40) : {curve.loc[30:40].mean():.1f}%")
    retained_share = rates.retained / rates.wau * 100
    print(f"  retained share of WAU  first={retained_share.iloc[1]:.1f}%"
          f"  last={retained_share.iloc[-1]:.1f}%")
    quick = rates.quick_ratio.dropna()
    print(f"  quick ratio  median={quick.median():.2f}  min={quick.min():.2f}"
          f"  max={quick.max():.2f}")
    below = quick[quick < 1.0]
    print("  weeks below 1.0  : " + ", ".join(f"{w} ({v:.2f})" for w, v in below.items()))
    observed_at_40 = rate_matrix[40].notna().sum()
    print(f"  cohorts observed at w40 : {observed_at_40}  (thin right edge - caveat the plateau)")

    march = rates.loc["2024-03-02":"2024-03-30"]
    baseline_nurr = rates.nurr.drop(march.index).loc[:"2024-05-18"].mean()
    print("\nQ2 - MARCH")
    print("  NURR by cohort   : " + ", ".join(f"{v:.1f}%" for v in march.nurr))
    print(f"  mean={march.nurr.mean():.1f}%   baseline={baseline_nurr:.1f}%"
          f"   delta={march.nurr.mean() - baseline_nurr:.1f}pp"
          f"   relative={(march.nurr.mean() / baseline_nurr - 1) * 100:.1f}%")
    print(f"  cohort sizes     : {list(march.new)}  (normal - not a volume event)")
    print(f"  CURR in window   : {march.curr.min():.1f}%-{march.curr.max():.1f}% (undisturbed)")

    april = rates.loc["2024-04-06":"2024-04-27"]
    non_april = rates.new.drop(april.index)
    print("\nQ3 - APRIL")
    print(f"  weekly signups   : {list(april.new)}")
    print(f"  april mean={april.new.mean():.0f}  baseline mean={non_april.mean():.0f}"
          f"  drop={(april.new.mean() / non_april.mean() - 1) * 100:.1f}%")
    print(f"  two trough weeks : {(april.new.iloc[:2].mean() / non_april.mean() - 1) * 100:.1f}%")
    print(f"  NURR in window   : {april.nurr.min():.1f}%-{april.nurr.max():.1f}% (normal)")
    print(f"  CURR in window   : {april.curr.min():.1f}%-{april.curr.max():.1f}% (normal)")

    good = rates.loc["2024-05-25":"2024-08-03"]
    after = rates.loc["2024-08-10":"2024-08-17"]
    print("\nQ4 - LATE MAY TO EARLY AUGUST")
    print(f"  cohorts          : {len(good)} ({good.index[0]} -> {good.index[-1]})")
    print(f"  NURR range={good.nurr.min():.1f}%-{good.nurr.max():.1f}%"
          f"  mean={good.nurr.mean():.1f}%  uplift={good.nurr.mean() - baseline_nurr:.1f}pp"
          f"  relative={(good.nurr.mean() / baseline_nurr - 1) * 100:.0f}%")
    print("  after revert     : " + ", ".join(f"{w}={v:.1f}%" for w, v in after.nurr.items()))
    w4, w8 = rate_matrix[4].loc[good.index], rate_matrix[8].loc[good.index]
    print(f"  persistence      : w4={w4.min():.1f}-{w4.max():.1f}%"
          f"   w8={w8.min():.1f}-{w8.max():.1f}%")
    print(f"  baseline persistence : w4={rate_matrix[4].drop(good.index).mean():.1f}%"
          f"  w8={rate_matrix[8].drop(good.index).mean():.1f}%")
    print("  w8 outage overlap: " + ", ".join(
        f"{c}={rate_matrix[8].loc[c]:.1f}%" for c in ("2024-07-27", "2024-08-03")))

    outage = "2024-09-21"
    i = list(weeks).index(outage)
    print("\nQ5 - MID-SEPTEMBER")
    print(f"  WAU {rates.wau.iloc[i-1]:,} -> {rates.wau.iloc[i]:,}"
          f"  ({(rates.wau.iloc[i] / rates.wau.iloc[i-1] - 1) * 100:.1f}%)")
    print(f"  CURR {rates.curr.iloc[i-1]:.1f}% -> {rates.curr.iloc[i]:.1f}%"
          f" -> {rates.curr.iloc[i+1]:.1f}%")
    print(f"  quick ratio      : {rates.quick_ratio.iloc[i]:.2f}")
    print(f"  churned          : {rates.churned.iloc[i]:,} vs {rates.churned.iloc[i-1]:,} prior week")
    print(f"  signups          : {rates.new.iloc[i]:,} vs {non_april.mean():.0f} baseline"
          f"  ({(rates.new.iloc[i] / non_april.mean() - 1) * 100:.0f}%)")
    print(f"  cohort NURR      : {rates.nurr.iloc[i-1]:.1f}% (09-14) vs {rates.nurr.iloc[i-2]:.1f}% prior")
    recovery = rates.wau.iloc[i:]
    back = recovery[recovery >= rates.wau.iloc[i - 1]]
    print(f"  recovery         : " + " -> ".join(f"{v:,}" for v in recovery.iloc[:6]))
    print(f"  regains pre-outage WAU : {back.index[0]}"
          f"  ({list(recovery.index).index(back.index[0])} weeks)")

    curr = rates.curr.dropna().drop(outage, errors="ignore")
    slope = np.polyfit(np.arange(len(curr)), curr.values, 1)[0]
    print("\nQ6 - WHOLE YEAR")
    print(f"  CURR first4={curr.head(4).mean():.1f}%  last4={curr.tail(4).mean():.1f}%"
          f"  delta={curr.tail(4).mean() - curr.head(4).mean():.1f}pp")
    print(f"  slope={slope:.3f}pp/week  ({slope * 52:.1f}pp/year, outage week excluded)")
    print(f"  monotonic-ish    : first values {', '.join(f'{v:.1f}' for v in curr.head(3))}"
          f" ... last {', '.join(f'{v:.1f}' for v in curr.tail(3))}")

    print("\nARTEFACT - MARCH COHORTS FOLLOWED FORWARD (should NOT behave like churn)")
    print(f"  {'cohort':<12}{'W1':>7}{'W4':>7}{'W12':>7}{'W20':>7}")
    for cohort in ["2024-03-02", "2024-03-09", "2024-03-16", "2024-03-23",
                   "2024-03-30", "2024-02-24"]:
        row = rate_matrix.loc[cohort]
        tag = f"{cohort} *" if cohort == "2024-02-24" else cohort
        print(f"  {tag:<12}" + "".join(f"{row[n]:>7.1f}" for n in (1, 4, 12, 20)))
    print("  * baseline cohort. March converges to baseline by W12 - implausible for real churn.")


def main():
    path = locate_dataset(sys.argv[1] if len(sys.argv) > 1 else None)
    activity_df = load_events(path)
    if not validate(activity_df, path):
        sys.exit(1)

    rates = relabel(weekly_rates(activity_df).set_index("week"))
    rate_matrix = relabel(cohort_matrix(activity_df, kind="rate", max_periods=52))
    curve = rate_matrix.drop(columns="Users").mean()

    report(rates, rate_matrix, curve)


if __name__ == "__main__":
    main()
