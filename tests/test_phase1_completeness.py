"""Phase-1 completeness guarantees for the report module.

A guided run must never be silently missing a canonical Phase-1 view. These
tests cover the one-shot path, the guard, and the idempotent self-heal.

Run from the repo root:  pytest tests/test_phase1_completeness.py
(or: PYTHONPATH=. python tests/test_phase1_completeness.py)
"""
import sys
from pathlib import Path

import matplotlib

# Non-interactive backend: figures are written to PNG, never opened in a window.
# Must be set before anything imports matplotlib.pyplot (datadiner.retention does).
matplotlib.use("Agg")

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datadiner.io import load_events
from datadiner.report import (
    AnalysisReport,
    overall_report,
    overview_sections,
    ensure_phase1,
    assert_phase1_complete,
    IncompleteRunError,
    PHASE1_REQUIRED_SLUGS,
)

CSV = (
    Path(__file__).resolve().parents[1]
    / "datasets/notion_daily_scatter/notion_daily_scatter_analyst_daily.csv"
)
ACTIVE = "page_shared"


@pytest.fixture(scope="module")
def df():
    return load_events(str(CSV), dtype={"app_version": str})


def _slugs(report):
    return [s["slug"] for s in report._sections]


def test_one_shot_is_complete(df, tmp_path):
    run_dir = overall_report(
        df, dataset="notion_daily_scatter", active_event=ACTIVE,
        base_dir=str(tmp_path),
    )
    # All eight canonical sections present, with a chart each.
    charts = {p.stem for p in (run_dir / "charts").rglob("*.png")}
    for slug in PHASE1_REQUIRED_SLUGS:
        assert any(c == slug or c.startswith(slug + "_") for c in charts), slug
    assert (run_dir / "report.md").exists()


def test_guard_fires_on_partial_run(df, tmp_path):
    report = AnalysisReport("notion_daily_scatter", df=df, base_dir=str(tmp_path))
    # Add only the first overview view.
    overview_sections(report, df, active_event=ACTIVE, skip_existing=True)
    # remove the two it added beyond usage_frequency to simulate a partial run
    report._sections = [s for s in report._sections if s["slug"] == "usage_frequency"]

    with pytest.raises(IncompleteRunError) as exc:
        assert_phase1_complete(report)
    msg = str(exc.value)
    # Names the missing slugs (everything but usage_frequency).
    for slug in PHASE1_REQUIRED_SLUGS:
        if slug != "usage_frequency":
            assert slug in msg


def test_ensure_phase1_self_heals_and_is_idempotent(df, tmp_path):
    report = AnalysisReport("notion_daily_scatter", df=df, base_dir=str(tmp_path))
    report.section("Usage frequency", note="the model's own read")
    assert _slugs(report).count("usage_frequency") == 1

    ensure_phase1(report, df, active_event=ACTIVE)
    slugs = _slugs(report)
    assert set(PHASE1_REQUIRED_SLUGS).issubset(set(slugs))
    # the pre-existing section was not duplicated...
    assert slugs.count("usage_frequency") == 1
    # ...nor clobbered (model's read preserved because it already existed)
    uf = next(s for s in report._sections if s["slug"] == "usage_frequency")
    assert "the model's own read" in uf["md"]

    assert_phase1_complete(report)  # now passes

    # Idempotent: a second call changes nothing.
    n = len(report._sections)
    ensure_phase1(report, df, active_event=ACTIVE)
    assert len(report._sections) == n


def test_note_override_is_applied(df, tmp_path):
    report = AnalysisReport("notion_daily_scatter", df=df, base_dir=str(tmp_path))
    ensure_phase1(
        report, df, active_event=ACTIVE,
        notes={"cohort_retention_rate": "MY CUSTOM READ"},
    )
    crr = next(s for s in report._sections if s["slug"] == "cohort_retention_rate")
    assert "MY CUSTOM READ" in crr["md"]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
