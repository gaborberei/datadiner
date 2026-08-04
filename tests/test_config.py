"""Column-role inference and the remembered-answers file."""

import pandas as pd
import pytest

from retentionkit import config


def test_infer_picks_the_obvious_roles(small_log, tmp_path):
    csv = tmp_path / "activity.csv"
    small_log.to_csv(csv, index=False)

    guess = config.infer_config(csv)
    assert guess["user_col"] == "user_id"
    assert guess["date_col"] == "date"
    assert guess["event_col"] == "event_type"
    assert guess["count_col"] == "event_count"
    assert guess["segment_cols"] == ["platform"]
    assert guess["core_action"] == "core"          # the highest-volume event
    assert guess["_candidates"]["segments"]["platform"] == ["desktop", "mobile"]


def test_config_round_trips(small_log, tmp_path):
    csv = tmp_path / "activity.csv"
    small_log.to_csv(csv, index=False)
    assert config.load_config(csv) is None         # nothing remembered yet

    saved = config.save_config(csv, {
        **config.infer_config(csv), "grain": "month", "week_start": "SAT",
    })
    assert saved["file"] == "activity.csv"
    assert "_candidates" not in saved              # proposals aren't answers

    loaded = config.load_config(csv)
    assert loaded["grain"] == "month"
    assert loaded["core_action"] == "core"
    assert loaded["file"] == str(csv)              # resolved back to a real path


def test_build_kwargs_feeds_the_matrix(small_log, tmp_path):
    from retentionkit.matrix import ActivityMatrix

    csv = tmp_path / "activity.csv"
    small_log.to_csv(csv, index=False)
    cfg = config.save_config(csv, config.infer_config(csv))

    am = ActivityMatrix.build(small_log, **config.build_kwargs(cfg))
    assert am.grain == "week"
    assert list(am.attrs.columns) == ["platform"]
    assert am.n_users == 5


def test_load_activity_reads_the_written_file(small_log, tmp_path):
    from retentionkit.io import load_activity

    csv = tmp_path / "activity.csv"
    small_log.to_csv(csv, index=False)
    df = load_activity(csv)

    assert pd.api.types.is_datetime64_any_dtype(df["date"])
    assert set(df.columns) == set(small_log.columns)
    assert len(df) == len(small_log)
