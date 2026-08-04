"""Resuming a run: adding a cut must not cost a second copy of the folder.

The failure this guards against is a workflow one rather than an arithmetic one.
Calling ``run_report`` once for the overall figures and again for a segment cut
used to mint two timestamped folders, the second one containing a byte-identical
copy of the first one's ``charts/overall/``. Resuming makes the second call
append instead.
"""

import json

import matplotlib
import pytest

matplotlib.use("Agg")  # no display in tests; figures are saved, never shown

from retentionkit.report import Run, _overlay_slugs, _view_slugs, run_report


def _sections(run_dir):
    return [s["slug"] for s in
            json.loads((run_dir / "run.json").read_text())["sections"]]


def _headings(run_dir):
    return [line for line in (run_dir / "report.md").read_text().splitlines()
            if line.startswith("## ")]


# --- the Run primitive ------------------------------------------------------

def test_new_run_is_not_resumed(tmp_path):
    run = Run("d", out_dir=tmp_path, run_id="r1")
    assert run.resumed is False
    assert run.has_views(["anything"]) is False


def test_resuming_adopts_the_earlier_sections(tmp_path):
    Run("d", out_dir=tmp_path, run_id="r1").section("First").save()

    resumed = Run("d", out_dir=tmp_path, run_id="r1")
    assert resumed.resumed is True
    assert resumed.has_views(["first"])
    resumed.section("Second").save()

    assert _headings(tmp_path / "d" / "r1") == ["## First", "## Second"]


def test_readding_a_slug_replaces_it_in_place(tmp_path):
    run = Run("d", out_dir=tmp_path, run_id="r1")
    run.section("First", note="original").section("Second")
    run.section("First", note="rewritten").save()

    # Replaced where it stood — not duplicated, not moved to the end.
    assert _headings(tmp_path / "d" / "r1") == ["## First", "## Second"]
    assert "rewritten" in (tmp_path / "d" / "r1" / "report.md").read_text()
    assert "original" not in (tmp_path / "d" / "r1" / "report.md").read_text()


def test_unreadable_manifest_does_not_fail_the_run(tmp_path):
    Run("d", out_dir=tmp_path, run_id="r1").section("First").save()
    (tmp_path / "d" / "r1" / "run.json").write_text("{ not json")

    run = Run("d", out_dir=tmp_path, run_id="r1")
    assert run.resumed is False       # falls back to behaving like a fresh run
    run.section("Fresh").save()
    assert _headings(tmp_path / "d" / "r1") == ["## Fresh"]


def test_explicit_header_wins_over_the_saved_one(tmp_path):
    Run("d", out_dir=tmp_path, run_id="r1", header_lines=["- old"]).save()
    run = Run("d", out_dir=tmp_path, run_id="r1", header_lines=["- new"])
    run.save()
    assert "- new" in (tmp_path / "d" / "r1" / "report.md").read_text()


# --- run_report end to end --------------------------------------------------

# A segment is a user attribute, so it must be constant per user — assigning
# by row position would give one user two channels and break the row-mask
# guarantee segmenting relies on.
_CHANNEL = {"steady": "organic", "one_shot": "organic", "late_user": "organic",
            "gap_user": "paid", "second_wk": "paid"}


@pytest.fixture
def run_kwargs(small_log, tmp_path):
    return dict(df=small_log, dataset="d", out_dir=tmp_path,
                active_event="core", segment_cols=["platform"], grain="week")


def test_one_call_per_cut_reuses_the_folder(run_kwargs, tmp_path):
    """The exact two-call sequence that used to produce two run folders."""
    first = run_report(**run_kwargs)
    again = run_report(**run_kwargs, run_id=first.name, segment_by="platform")

    assert again == first
    assert [p.name for p in (tmp_path / "d").iterdir()] == [first.name]

    slugs = _sections(first)
    assert len(slugs) == len(set(slugs)), "a resumed run duplicated a section"
    # Overall still leads; the appended cut follows it.
    for slug in _view_slugs():
        assert slug in slugs
    for slug in _view_slugs("_platform-mobile", overlaid=True):
        assert slug in slugs
    assert slugs.index("retention_curve") < slugs.index(
        "cohort_retention_rate_platform-mobile")


def test_resuming_skips_the_cuts_already_present(run_kwargs, capsys):
    first = run_report(**run_kwargs)
    overall = sorted((first / "charts" / "overall").glob("*.png"))
    stamps = {p.name: p.stat().st_mtime_ns for p in overall}

    run_report(**run_kwargs, run_id=first.name, segment_by="platform")

    assert "already in this run — skipped" in capsys.readouterr().out
    after = {p.name: p.stat().st_mtime_ns
             for p in (first / "charts" / "overall").glob("*.png")}
    assert after == stamps, "overall figures were redrawn on resume"


def test_refresh_redraws_what_was_skipped(run_kwargs):
    first = run_report(**run_kwargs)
    before = (first / "charts" / "overall" / "retention_curve.png").stat().st_mtime_ns

    run_report(**run_kwargs, run_id=first.name, refresh=True)

    after = (first / "charts" / "overall" / "retention_curve.png").stat().st_mtime_ns
    assert after != before
    slugs = _sections(first)
    assert len(slugs) == len(set(slugs))


def test_without_run_id_each_call_still_gets_its_own_folder(run_kwargs, tmp_path):
    """Resuming is opt-in — run history is a feature, not the bug we fixed."""
    first = run_report(**run_kwargs)
    other = run_report(**run_kwargs, run_id="deliberately-separate")
    assert other != first
    assert len(list((tmp_path / "d").iterdir())) == 2


def test_a_list_segment_by_crosses_the_columns(small_log, tmp_path):
    """A list is an interaction cut, not two cuts — one set per combination.

    Worth pinning down because the two readings differ by a lot of figures: two
    independent cuts are two calls sharing a ``run_id``, and reaching for a list
    instead silently produces the cross product.
    """
    small_log = small_log.assign(channel=small_log["user_id"].map(_CHANNEL))
    out = run_report(small_log, dataset="d", out_dir=tmp_path, active_event="core",
                     segment_cols=["platform", "channel"], grain="week",
                     segment_by=["platform", "channel"])

    slugs = _sections(out)
    assert len(slugs) == len(set(slugs))
    # Crossed labels, not one cut per column.
    assert "cohort_retention_rate_platform-mobile_channel-organic" in slugs
    assert "cohort_retention_rate_platform-mobile" not in slugs
    # The two line charts are drawn once for the whole crossed cut.
    assert _overlay_slugs("platform_x_channel") == [
        s for s in slugs if s.startswith(("retention_curve_", "quick_ratio_"))]
    # All of it lands in one subfolder named for the interaction.
    assert (out / "charts" / "platform_x_channel").is_dir()


def test_two_independent_cuts_share_one_run(small_log, tmp_path):
    """The supported way to get two separate cuts into a single folder."""
    small_log = small_log.assign(channel=small_log["user_id"].map(_CHANNEL))
    kwargs = dict(dataset="d", out_dir=tmp_path, active_event="core",
                  segment_cols=["platform", "channel"], grain="week")

    first = run_report(small_log, **kwargs, segment_by="platform")
    again = run_report(small_log, **kwargs, run_id=first.name,
                       segment_by="channel")

    assert again == first
    slugs = _sections(first)
    assert len(slugs) == len(set(slugs))
    assert "cohort_retention_rate_platform-mobile" in slugs
    assert "cohort_retention_rate_channel-organic" in slugs
    # Each cut brought its own pair of overlays.
    assert "retention_curve_by_platform" in slugs
    assert "retention_curve_by_channel" in slugs
    assert sorted(p.name for p in (first / "charts").iterdir()) == [
        "channel", "overall", "platform"]


# --- segment overlays --------------------------------------------------------
#
# The retention curve and Quick Ratio are drawn once per cut with one line per
# segment, not once per segment value. Three separate Quick Ratio images is
# exactly the comparison a reader cannot make by flipping between them.

def test_segmented_run_draws_the_line_charts_once(run_kwargs):
    out = run_report(**run_kwargs, segment_by="platform")
    slugs = _sections(out)

    assert "retention_curve_by_platform" in slugs
    assert "quick_ratio_by_platform" in slugs
    # ...and not once per value.
    per_segment = [s for s in slugs
                   if s.startswith(("retention_curve_platform-",
                                    "quick_ratio_platform-"))]
    assert per_segment == []


def test_the_overall_cut_keeps_its_own_single_line_charts(run_kwargs):
    """Only the segmented cut overlays; the un-segmented run is unchanged."""
    out = run_report(**run_kwargs, segment_by="platform")
    slugs = _sections(out)

    assert "retention_curve" in slugs and "quick_ratio" in slugs
    assert (out / "charts" / "overall" / "retention_curve.png").exists()
    assert (out / "charts" / "overall" / "quick_ratio.png").exists()


def test_each_segment_still_gets_its_own_detail_views(run_kwargs):
    """Only the two line charts moved — heatmaps and bars stay per segment."""
    out = run_report(**run_kwargs, segment_by="platform")
    slugs = _sections(out)

    for value in ("mobile", "desktop"):
        assert f"cohort_retention_rate_platform-{value}" in slugs
        assert f"lifecycle_states_platform-{value}" in slugs
        assert f"usage_frequency_platform-{value}" in slugs


def test_the_overlay_csv_names_every_line(run_kwargs):
    """The data twin has to say which line each row belongs to."""
    import pandas as pd
    out = run_report(**run_kwargs, segment_by="platform")

    for slug in ("retention_curve_by_platform", "quick_ratio_by_platform"):
        table = pd.read_csv(out / "data" / f"{slug}.csv")
        assert table.columns[0] == "segment"
        assert set(table["segment"]) == {"platform=mobile", "platform=desktop"}


def test_overlays_are_skipped_on_resume(run_kwargs, capsys):
    first = run_report(**run_kwargs, segment_by="platform")
    stamp = (first / "charts" / "platform"
             / "retention_curve_by_platform.png").stat().st_mtime_ns

    run_report(**run_kwargs, run_id=first.name, segment_by="platform")

    assert "overlays already in this run — skipped" in capsys.readouterr().out
    after = (first / "charts" / "platform"
             / "retention_curve_by_platform.png").stat().st_mtime_ns
    assert after == stamp
