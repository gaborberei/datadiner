"""Contract tests for `retention.weekly_rates`.

Runs on a small hand-built frame so the expected buckets can be counted by hand,
with no dataset dependency.

Run from the repo root:  pytest tests/test_weekly_rates.py
"""
import sys
from pathlib import Path

import matplotlib

# Non-interactive backend: figures are written to PNG, never opened in a window.
# Must be set before anything imports matplotlib.pyplot (datadiner.retention does).
matplotlib.use("Agg")

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datadiner.retention import lifecycle_states, weekly_rates, no_figure_display

# Four consecutive Mondays, so each date lands in its own weekly bucket.
W = ["2024-01-01", "2024-01-08", "2024-01-15", "2024-01-22"]


def _events(pairs):
    """Build an event log from (week_index, user_id) pairs."""
    return pd.DataFrame(
        [{"date": pd.Timestamp(W[i]), "user_id": u} for i, u in pairs]
    )


@pytest.fixture(scope="module")
def rates():
    # a: every week.           b: weeks 0,1 then gone.
    # c: joins week 1, gone week 2, returns week 3 (resurrection).
    # d: joins week 2 only.
    return weekly_rates(_events([
        (0, "a"), (0, "b"),
        (1, "a"), (1, "b"), (1, "c"),
        (2, "a"), (2, "d"),
        (3, "a"), (3, "c"),
    ])).set_index("week")


def test_buckets_partition_wau(rates):
    """new / retained / resurrected are disjoint and account for every active user."""
    assert (rates.wau == rates.new + rates.retained + rates.resurrected).all()


def test_bucket_counts(rates):
    assert list(rates.new) == [2, 1, 1, 0]           # a,b | c | d | -
    assert list(rates.retained) == [0, 2, 1, 1]      # - | a,b | a | a
    assert list(rates.resurrected) == [0, 0, 0, 1]   # - | - | - | c


def test_churned_is_one_missed_week(rates):
    """churned(w) = active in w-1, absent in w — booked immediately."""
    # week 2 loses b and c; week 3 loses d.
    assert list(rates.churned) == [0, 0, 2, 1]


def test_churned_equals_lifecycle_at_risk(rates):
    """The stricter model here is exactly lifecycle_states' At-Risk column."""
    with no_figure_display():
        states, _ = lifecycle_states(_events([
            (0, "a"), (0, "b"),
            (1, "a"), (1, "b"), (1, "c"),
            (2, "a"), (2, "d"),
            (3, "a"), (3, "c"),
        ]))
    assert list(states["At-Risk"]) == list(rates.churned)


def test_nurr_is_next_week_return_rate(rates):
    """Of the cohort signing up in w, the share active in w+1."""
    assert rates.nurr.iloc[0] == pytest.approx(100.0)  # a,b both active again in w1
    assert rates.nurr.iloc[1] == pytest.approx(0.0)    # c -> absent in w2
    assert rates.nurr.iloc[2] == pytest.approx(0.0)    # d -> absent in w3
    assert pd.isna(rates.nurr.iloc[-1])                # undefined for the final week


def test_curr_excludes_previous_weeks_new_users(rates):
    """CURR's denominator is last week's established actives, not all of them."""
    assert pd.isna(rates.curr.iloc[0])                 # undefined for the first week

    # Week 1: everyone active in week 0 (a, b) was new that week, so there are no
    # established players to measure and CURR is undefined. A naive definition
    # using all of week 0's actives would wrongly report 100%.
    assert pd.isna(rates.curr.iloc[1])

    # Week 2: week 1's established actives are a and b (c was new). Only a returns.
    assert rates.curr.iloc[2] == pytest.approx(50.0)


def test_quick_ratio(rates):
    """(new + resurrected) / churned, NaN when nobody churned."""
    assert pd.isna(rates.quick_ratio.iloc[0])
    assert rates.quick_ratio.iloc[2] == pytest.approx(0.5)   # 1 new / 2 churned
    assert rates.quick_ratio.iloc[3] == pytest.approx(1.0)   # 1 resurrected / 1 churned


def test_segment_by_returns_one_frame_per_value():
    events = _events([(0, "a"), (1, "a"), (0, "b"), (1, "b")])
    events["plan"] = ["free", "free", "paid", "paid"]
    out = weekly_rates(events, segment_by="plan")
    assert [label for label, _ in out] == ["plan=free", "plan=paid"]
    assert all(isinstance(frame, pd.DataFrame) for _, frame in out)
