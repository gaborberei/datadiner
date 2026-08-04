"""The two ways sparsity bites: a dropped empty period, and 0 read as NaN.

An active-periods-only log has no rows for inactivity. Getting retention right
means putting the zeros back where they belong — and *only* where they belong.
"""

import numpy as np
import pandas as pd
import pytest

from retentionkit.matrix import ActivityMatrix, period_axis
from retentionkit import metrics


def test_empty_period_keeps_its_column(small_log):
    """The week nobody was active still occupies an axis position.

    If the axis came from factorizing observed periods, 2024-01-22 would vanish
    and every cohort's ages past it would shift left by one — dating the entire
    heatmap wrong. This is the single most important invariant in the package.
    """
    am = ActivityMatrix.build(small_log, grain="week", active_event="core")
    labels = am.period_labels()

    assert labels == ["2024-01-01", "2024-01-08", "2024-01-15",
                      "2024-01-22", "2024-01-29", "2024-02-05"]
    empty = labels.index("2024-01-22")
    assert am.active_per_period()[empty] == 0
    # Ages are elapsed time: the first cohort's age 4 must be 2024-01-29, the
    # week *after* the empty one — not the week that filled its slot.
    assert labels[0 + 4] == "2024-01-29"


def test_axis_is_complete_even_with_long_absences():
    df = pd.DataFrame({
        "date": pd.to_datetime(["2024-01-01", "2024-03-04"]),
        "user_id": ["a", "a"],
        "event_type": ["core", "core"],
        "event_count": [1, 1],
    })
    axis = period_axis(df["date"], "week")
    assert len(axis) == 10                      # nine empty weeks in between
    assert (np.diff(axis.values).astype("timedelta64[D]").astype(int) == 7).all()


def test_gap_reads_as_zero_not_missing(small_log):
    """gap_user is absent for two weeks between two active ones.

    Those cells are genuine zeros — the user was observable and did nothing —
    so they must be 0 in the cohort table, never NaN.
    """
    am = ActivityMatrix.build(small_log, grain="week", active_event="core")
    counts = metrics.cohort_table(am, kind="retention_counts", max_age=99)
    # Cohort 2024-01-01 holds steady, gap_user and one_shot.
    first = counts.loc["2024-01-01"]
    assert first["Signups"] == 3
    assert first[2] == 1        # only steady is active at age 2
    assert first[3] == 0        # the empty week: observed, nobody active
    assert not np.isnan(first[3])


def test_censoring_triangle_is_nan_not_zero(small_log):
    """A cohort that hasn't lived that long is NaN — reading it as 0 would drag
    every young cohort's curve to the floor."""
    am = ActivityMatrix.build(small_log, grain="week", active_event="core")
    counts = metrics.cohort_table(am, kind="retention_counts", max_age=99)

    # late_user's cohort is the final week, so only age 0 is observable.
    last = counts.loc["2024-02-05"]
    assert last[0] == 1
    assert np.isnan(last[1])
    assert np.isnan(last[5])

    # And the oldest cohort is observable all the way across.
    assert counts.loc["2024-01-01"].drop("Signups").notna().all()


def test_curve_ignores_censored_cells(small_log):
    """The average at each age is over cohorts that could be observed there."""
    am = ActivityMatrix.build(small_log, grain="week", active_event="core")
    curve = metrics.retention_curve(am, max_age=99)
    assert curve.loc[0, "cohorts"] == 3        # three cohorts have members
    assert curve.loc[5, "cohorts"] == 1        # only the first is that old
    assert curve["retention_pct"].notna().all()


def test_density_counts_true_zeros(weekly):
    """Density is measured against the complete panel, not the observed rows."""
    assert weekly.n_periods == 6
    assert weekly.n_users == 5
    assert weekly.presence.nnz == 13
    assert weekly.density == pytest.approx(13 / 30)


def test_quality_report_flags_the_empty_period(small_log):
    from retentionkit.io import quality_report

    report = quality_report(small_log, grain="week")
    assert report["empty_periods"] == []      # noise row keeps the week non-empty
    assert report["users_with_gaps"] == 2     # steady and gap_user both skip weeks
    assert report["single_period_users"] == 2
    assert 0 < report["density"] < 1
