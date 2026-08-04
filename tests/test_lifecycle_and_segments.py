"""Lifecycle state transitions, and segmenting as a row mask."""

import numpy as np
import pandas as pd
import pytest

from retentionkit.matrix import ActivityMatrix
from retentionkit import metrics


def test_at_risk_then_churned(small_log):
    """One missed period is At-Risk; a second consecutive one books Churned."""
    am = ActivityMatrix.build(small_log, grain="week", active_event="core")
    states = metrics.lifecycle_states(am).set_index(
        am.periods.strftime("%Y-%m-%d"))

    # one_shot is active only in week 1.
    assert states.loc["2024-01-01", "New"] == 3
    assert states.loc["2024-01-08", "At-Risk"] == 1     # one_shot goes quiet
    assert states.loc["2024-01-15", "Churned"] == 1     # ...and stays quiet

    # gap_user is absent in weeks 3-4 and returns in week 6.
    assert states.loc["2024-02-05", "Resurrected"] >= 1


def test_new_column_equals_cohort_sizes(weekly):
    states = metrics.lifecycle_states(weekly)
    np.testing.assert_array_equal(states["New"].to_numpy(),
                                  weekly.cohort_sizes())


def test_quick_ratio_definition(weekly):
    states = metrics.lifecycle_states(weekly)
    churned = states["Churned"].replace(0, np.nan)
    want = (states["New"] + states["Resurrected"]) / churned
    pd.testing.assert_series_equal(states["Quick Ratio"], want,
                                   check_names=False)


def test_nobody_is_counted_twice(weekly):
    """New + Retained + Resurrected is exactly the active users that period."""
    states = metrics.lifecycle_states(weekly)
    active = states[["New", "Retained", "Resurrected"]].sum(axis=1).to_numpy()
    np.testing.assert_array_equal(active, weekly.active_per_period())


def test_segment_mask_equals_rebuilding_from_filtered_rows(small_log):
    """Cutting the matrix must give the same numbers as filtering the log first.

    This is what makes segmenting a row slice rather than a rebuild: a user's
    cohort is their own first active period and doesn't depend on who else is
    in the frame.
    """
    am = ActivityMatrix.build(small_log, grain="week", active_event="core",
                              segment_cols=["platform"])
    sliced = dict(am.segments("platform"))["platform=mobile"]

    rebuilt = ActivityMatrix.build(
        small_log[small_log["platform"] == "mobile"],
        grain="week", active_event="core", segment_cols=["platform"],
    )

    # The rebuilt matrix only spans the periods its own users appear in, so
    # compare on the shared prefix of the axis.
    assert list(rebuilt.periods) == list(am.periods)
    np.testing.assert_array_equal(sliced.active_per_period(),
                                  rebuilt.active_per_period())
    pd.testing.assert_frame_equal(
        metrics.cohort_table(sliced, kind="retention_rate"),
        metrics.cohort_table(rebuilt, kind="retention_rate"),
    )
    pd.testing.assert_frame_equal(metrics.lifecycle_states(sliced),
                                  metrics.lifecycle_states(rebuilt))


def test_segments_partition_the_users(weekly):
    total = sum(seg.n_users for _, seg in weekly.segments("platform"))
    assert total == weekly.n_users


def test_segment_column_must_be_carried(small_log):
    am = ActivityMatrix.build(small_log, grain="week", active_event="core")
    with pytest.raises(ValueError, match="segment_cols"):
        am.segments("platform")


def test_usage_frequency_needs_a_daily_matrix(weekly, small_log):
    with pytest.raises(ValueError, match="daily matrix"):
        metrics.usage_frequency(weekly)

    daily = ActivityMatrix.build(small_log, grain="day", active_event="core")
    usage = metrics.usage_frequency(daily)
    assert len(usage) == 5
    # one_shot: one active day in the one month it was active in. February, which
    # it sat out entirely, is not in the denominator — the cadence read is "how
    # often when they show up at all".
    by_user = usage.set_index("user_id")
    assert by_user.loc["one_shot", "avg_active_days_per_month"] == pytest.approx(1)
    # steady: 4 active days in January, 1 in February -> (4 + 1) / 2 months.
    assert by_user.loc["steady", "avg_active_days_per_month"] == pytest.approx(2.5)
