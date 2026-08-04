"""The sparse cohort path must agree, cell for cell, with a naive pandas one.

This is the test that licenses throwing the pandas implementation away.
"""

import numpy as np
import pandas as pd
import pytest

from retentionkit.matrix import ActivityMatrix
from retentionkit import metrics

from conftest import naive_cohort_counts


@pytest.mark.parametrize("grain", ["week", "month"])
def test_counts_match_naive(small_log, grain):
    am = ActivityMatrix.build(small_log, grain=grain, active_event="core")
    sparse_counts = metrics.cohort_table(am, kind="retention_counts", max_age=99)
    naive, sizes = naive_cohort_counts(small_log, grain=grain, active_event="core")

    assert list(sparse_counts.index) == [str(c) for c in
                                         (naive.index.strftime("%Y-%m-%d")
                                          if grain == "week"
                                          else naive.index.strftime("%Y-%m"))]
    assert (sparse_counts["Signups"].to_numpy() == sizes.to_numpy()).all()

    ages = [c for c in sparse_counts.columns if c != "Signups"]
    got = sparse_counts[ages].to_numpy(dtype=float)
    want = naive[list(ages)].to_numpy(dtype=float)
    np.testing.assert_array_equal(np.isnan(got), np.isnan(want))
    np.testing.assert_allclose(got[~np.isnan(got)], want[~np.isnan(want)])


@pytest.mark.parametrize("kind", list(metrics.KINDS))
def test_every_kind_derives_from_the_same_counts(weekly, kind):
    """Each view is a transform of one computation — check the arithmetic."""
    counts = metrics.cohort_table(weekly, kind="retention_counts", max_age=99)
    table = metrics.cohort_table(weekly, kind=kind, max_age=99)
    ages = [c for c in counts.columns if c != "Signups"]
    sizes = counts["Signups"].to_numpy(dtype=float)[:, None]
    rate = counts[ages].to_numpy(dtype=float) / sizes * 100

    if kind == "retention_counts":
        want = counts[ages].to_numpy(dtype=float)
    elif kind == "retention_rate":
        want = rate
    elif kind == "churn_counts":
        want = np.diff(counts[ages].to_numpy(dtype=float), axis=1)
    elif kind == "churn_rate":
        want = np.diff(rate, axis=1)
    else:
        want = rate - np.nanmean(rate, axis=0)

    got = table[[c for c in table.columns if c != "Signups"]].to_numpy(dtype=float)
    np.testing.assert_allclose(got, want, equal_nan=True)


def test_rate_starts_at_100_percent(weekly):
    """Age 0 is the cohort itself, so it is 100% by construction."""
    rate = metrics.cohort_table(weekly, kind="retention_rate")
    assert (rate[0] == 100).all()


def test_active_event_filters(small_log):
    """A non-core event must not make a user look active."""
    with_noise = ActivityMatrix.build(small_log, grain="week")
    core_only = ActivityMatrix.build(small_log, grain="week", active_event="core")
    # 'steady' has a noise-only week that must vanish under the core filter.
    assert with_noise.presence.nnz == core_only.presence.nnz + 1


def test_retention_curve_matches_column_means(weekly):
    curve = metrics.retention_curve(weekly, max_age=99)
    rate = metrics.cohort_table(weekly, kind="retention_rate", max_age=99)
    ages = [c for c in rate.columns if c != "Signups"]
    want = np.nanmean(rate[ages].to_numpy(dtype=float), axis=0)
    np.testing.assert_allclose(curve["retention_pct"].to_numpy(), want,
                               equal_nan=True)


def test_weighted_curve_is_pooled_not_averaged(weekly):
    """The weighted read pools users; the default weights every cohort equally."""
    plain = metrics.retention_curve(weekly, max_age=99)
    pooled = metrics.retention_curve(weekly, max_age=99, weighted=True)
    assert plain["retention_pct"][0] == pytest.approx(100)
    assert pooled["retention_pct"][0] == pytest.approx(100)
    # With cohorts of unequal size and unequal quality they must differ somewhere.
    assert not np.allclose(plain["retention_pct"].to_numpy()[1:],
                           pooled["retention_pct"].to_numpy()[1:],
                           equal_nan=True)
