"""The cadence read that should pick the retention period."""

import pandas as pd
import pytest

from retentionkit.io import natural_frequency, quality_report


def _log(users):
    """Build a log from {user: [day offsets from 2024-01-01]}."""
    rows = [{"date": pd.Timestamp("2024-01-01") + pd.Timedelta(days=d),
             "user_id": u, "event_type": "core", "event_count": 1}
            for u, days in users.items() for d in days]
    return pd.DataFrame(rows)


def test_daily_habit_reads_daily():
    nf = natural_frequency(_log({f"u{i}": range(0, 40) for i in range(5)}))
    assert nf["cadence"] == "daily"
    assert nf["median_gap_days"] == 1


def test_weekly_rhythm_reads_weekly():
    nf = natural_frequency(_log({f"u{i}": range(0, 70, 7) for i in range(5)}))
    assert nf["cadence"] == "weekly"
    assert nf["median_gap_days"] == 7


def test_monthly_rhythm_reads_monthly():
    nf = natural_frequency(_log({f"u{i}": range(0, 200, 30) for i in range(5)}))
    assert nf["cadence"] == "monthly"
    assert nf["median_gap_days"] == 30


def test_the_population_decides_not_the_heavy_users():
    """Per-user medians first, so a few daily players can't speak for everyone."""
    users = {f"weekly{i}": range(0, 70, 7) for i in range(9)}
    users["addict"] = range(0, 70)          # one very heavy user
    nf = natural_frequency(_log(users))
    assert nf["cadence"] == "weekly"
    assert nf["shares"]["daily"] == pytest.approx(0.1)


def test_single_day_users_have_no_cadence():
    nf = natural_frequency(_log({"once": [3], "weekly": range(0, 70, 7)}))
    assert nf["users_measured"] == 1        # 'once' contributes no gap
    assert nf["cadence"] == "weekly"


def test_active_event_filters_the_cadence():
    df = _log({"u": [0, 1, 2, 3]})
    df.loc[df.index % 2 == 1, "event_type"] = "noise"
    # Core action only on days 0 and 2 -> a 2-day rhythm, not a 1-day one.
    assert natural_frequency(df, active_event="core")["median_gap_days"] == 2
    assert natural_frequency(df)["median_gap_days"] == 1


def test_quality_report_carries_it_and_flags_a_mismatch():
    weekly_log = _log({f"u{i}": range(0, 140, 7) for i in range(10)})

    report = quality_report(weekly_log, grain="month", active_event="core")
    assert report["natural_frequency"]["cadence"] == "weekly"
    assert any("Natural frequency" in f for f in report["flags"])
    # Monthly periods against a weekly rhythm is exactly the case worth warning on.
    assert any("manufactures churn" in f for f in report["flags"])

    matched = quality_report(weekly_log, grain="week", active_event="core")
    assert not any("manufactures churn" in f for f in matched["flags"])


def test_the_sparsity_fixture_reads_monthly(small_log):
    """The gappy fixture is genuinely monthly — worth pinning so it isn't
    mistaken for a bug later. Two of its three measurable users return on a
    17-day and a 10.5-day median gap."""
    nf = natural_frequency(small_log, active_event="core")
    assert nf["users_measured"] == 3          # two users have a single active day
    assert nf["cadence"] == "monthly"
