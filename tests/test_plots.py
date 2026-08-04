"""Smoke tests for the rendering layer.

`plots` draws; it does not compute, so there is nothing here about numbers. What
these guard is that every figure the report bundles still builds, and that it
carries the DataDiner title it is supposed to carry — a rendering change that
silently breaks a run, or quietly renames a figure, fails here.
"""

import matplotlib
import numpy as np
import pytest
from matplotlib.figure import Figure

from retentionkit import metrics, plots
from retentionkit.matrix import ActivityMatrix


def _title(fig):
    return fig.axes[0].get_title()


@pytest.mark.parametrize("kind,expected", [
    ("retention_rate", "Cohort Retention Rate — % Still Active (colored per column)"),
    ("retention_counts", "Cohort Retention Counts — Active Users per Week"),
    ("churn_rate", "Cohort Churn Rate — pp Change in Retention Week-over-Week"),
    ("churn_counts", "Cohort Churn Counts — Users Lost per Week"),
    ("vs_average", "Cohort vs Average — Deviation from Average Retention per Week"),
])
def test_cohort_heatmap_titles(weekly, kind, expected):
    fig = plots.cohort_heatmap(metrics.cohort_table(weekly, kind=kind), kind=kind)
    assert isinstance(fig, Figure)
    assert _title(fig) == expected


def test_monthly_heatmap_says_monthly(small_log):
    monthly = ActivityMatrix.build(small_log, grain="month", active_event="core")
    fig = plots.cohort_heatmap(metrics.cohort_table(monthly), grain="month")
    assert _title(fig).startswith("Monthly Cohort Retention Rate")
    assert fig.axes[0].get_ylabel() == "Cohort Month"


def test_segment_label_lands_in_the_title(weekly):
    table = metrics.cohort_table(weekly, kind="retention_rate")
    fig = plots.cohort_heatmap(table, label="platform=mobile")
    assert _title(fig).endswith(" — platform=mobile")


def test_curve_overlay_names_the_segment(weekly):
    curves = [(label, metrics.retention_curve(sub))
              for label, sub in weekly.segments("platform")]
    fig = plots.retention_curve(curves)
    assert _title(fig) == "Overall Retention Curve by platform"
    # One line per segment, plus the legend.
    assert len(fig.axes[0].lines) == len(curves)


def test_single_curve_keeps_the_plain_title(weekly):
    fig = plots.retention_curve(metrics.retention_curve(weekly))
    assert _title(fig) == "Overall Retention Curve"
    assert fig.axes[0].get_ylim() == (0, 105)


def test_lifecycle_and_quick_ratio(weekly):
    states = metrics.lifecycle_states(weekly)
    bars = plots.lifecycle_bars(states)
    ratio = plots.quick_ratio(states)
    assert _title(bars) == "User Lifecycle Buckets — Weekly Breakdown"
    assert _title(ratio) == "Quick Ratio — (New + Resurrected) / Churned"
    # Five stacked series: New / Retained / Resurrected up, At-Risk / Churned down.
    assert len(bars.axes[0].containers) == 5


def test_usage_frequency(small_log):
    daily = ActivityMatrix.build(small_log, grain="day", active_event="core")
    fig = plots.usage_frequency(metrics.usage_frequency(daily))
    assert _title(fig) == (
        "Product Usage Frequency — Avg Days Active per Month per User"
    )
    # The three target bands are always drawn, whatever the data's range.
    labels = [line.get_label() for line in fig.axes[0].lines]
    assert "Daily Target (20+)" in labels


def test_agg_backend_outside_a_notebook():
    """A script/agent run must never try to open a window."""
    assert matplotlib.get_backend().lower() == "agg"


# --- the Signups column ------------------------------------------------------
#
# It shares the RdYlGn ramp with the age columns but is scaled only against its
# own values, so it reads as relative signup volume. What these guard is that
# "only its own values" stays true, and that the numbers stay legible now that
# the column reaches both dark ends of the ramp.

def test_signups_column_is_scaled_against_itself(weekly):
    """Cohort sizes must map to the ramp on their own range, not the table's."""
    table = metrics.cohort_table(weekly).copy()
    table["Signups"] = [100, 200, 300][:len(table)]

    colored = plots._column_normalized(table.to_numpy(dtype=float))

    assert list(colored[:, 0]) == pytest.approx([0.0, 0.5, 1.0][:len(table)])


def test_signups_scaling_ignores_the_age_columns(weekly):
    """Retention values sit on 0-100; sizes must not be squashed against them."""
    table = metrics.cohort_table(weekly).copy()
    sizes = [10, 20, 30][:len(table)]          # far below the age columns' range
    table["Signups"] = sizes

    colored = plots._column_normalized(table.to_numpy(dtype=float))

    # Still spans the full ramp despite being tiny next to the percentages.
    assert colored[:, 0].min() == pytest.approx(0.0)
    assert colored[:, 0].max() == pytest.approx(1.0)


def test_equal_cohort_sizes_stay_neutral(weekly):
    """A flat column has no high or low end, so it must not pick a pole."""
    table = metrics.cohort_table(weekly).copy()
    table["Signups"] = 500

    colored = plots._column_normalized(table.to_numpy(dtype=float))

    assert list(colored[:, 0]) == pytest.approx([0.5] * len(table))


def test_no_fill_is_painted_over_the_signups_column(weekly):
    """Regressing to the flat grey would show up as a *filled* patch over it.

    The column carries an unfilled frame by design, so this checks the fill
    specifically rather than the presence of a patch.
    """
    fig = plots.cohort_heatmap(metrics.cohort_table(weekly))
    over_column = [p for p in fig.axes[0].patches if p.get_x() == 0]
    assert over_column, "the Signups column lost its frame"
    assert not any(p.get_fill() for p in over_column)


def test_signups_column_is_framed_in_black(weekly):
    """The frame is what marks it as the one column that is not a retention age."""
    table = metrics.cohort_table(weekly)
    fig = plots.cohort_heatmap(table)

    frame = next(p for p in fig.axes[0].patches if p.get_x() == 0)
    assert frame.get_edgecolor()[:3] == (0.0, 0.0, 0.0)
    assert frame.get_width() == 1              # exactly the Signups column
    assert frame.get_height() == len(table)    # its full depth


def test_column_names_repeat_along_the_top(weekly):
    """A year of cohorts puts the bottom axis a screen away from the first rows."""
    fig = plots.cohort_heatmap(metrics.cohort_table(weekly))
    fig.canvas.draw()
    # label2 is the top-side x label; it is hidden unless labeltop was asked for.
    tops = [t.label2.get_visible() for t in fig.axes[0].xaxis.get_major_ticks()]
    assert tops and all(tops)


@pytest.mark.parametrize("kind", list(metrics.KINDS))
def test_every_view_colors_the_signups_column_the_same(weekly, kind):
    """All five kinds carry the same cohort sizes, so the column must agree."""
    reference = plots._column_normalized(
        metrics.cohort_table(weekly, kind="retention_rate").to_numpy(dtype=float))[:, 0]
    colored = plots._column_normalized(
        metrics.cohort_table(weekly, kind=kind).to_numpy(dtype=float))[:, 0]
    assert list(colored) == pytest.approx(list(reference))


def _rendered(fig):
    """The 0..1 shades seaborn actually drew, as a 2-D array."""
    return np.asarray(fig.axes[0].collections[0].get_array(), dtype=float)


@pytest.mark.parametrize("kind", list(metrics.KINDS))
def test_every_view_renders_column_normalized(weekly, kind):
    """One scale for all five views: min-max within each age column.

    Checked against what seaborn actually drew, not against the helper's return
    value, so a change to which scale `cohort_heatmap` picks fails here.
    """
    table = metrics.cohort_table(weekly, kind=kind)
    drawn = _rendered(plots.cohort_heatmap(table, kind=kind))

    expected = plots._column_normalized(table.to_numpy(dtype=float))
    assert np.allclose(drawn, expected, equal_nan=True)


@pytest.mark.parametrize("shade,expected", [
    (0.0, "white"),    # darkest red — the smallest cohort
    (0.1, "white"),
    (0.5, "black"),    # pale yellow middle
    (0.9, "white"),
    (1.0, "white"),    # darkest green — the biggest cohort
])
def test_ink_whitens_at_both_poles(shade, expected):
    assert plots._ink(shade, both_poles=True) == expected


@pytest.mark.parametrize("shade,expected", [
    (0.0, "black"),
    (0.5, "black"),
    (1.0, "white"),
])
def test_ink_low_to_high_only_whitens_at_the_top(shade, expected):
    """The age columns' existing rule, unchanged by the Signups column work."""
    assert plots._ink(shade, both_poles=False) == expected


# --- overlays ----------------------------------------------------------------
#
# Both line charts take either one frame or a list of (label, frame). The list
# form is what a segmented run uses, so the segments land on one shared axis.

def test_quick_ratio_overlay_draws_one_line_per_segment(weekly):
    series = [(label, metrics.lifecycle_states(sub))
              for label, sub in weekly.segments("platform")]
    fig = plots.quick_ratio(series)

    ax = fig.axes[0]
    assert _title(fig) == "Quick Ratio — (New + Resurrected) / Churned by platform"
    # One line per segment, plus the 1.0 break-even rule drawn once.
    assert len(ax.lines) == len(series) + 1
    assert ax.get_legend().get_title().get_text() == "platform"


def test_single_quick_ratio_keeps_the_plain_title(weekly):
    fig = plots.quick_ratio(metrics.lifecycle_states(weekly))
    assert _title(fig) == "Quick Ratio — (New + Resurrected) / Churned"
    assert fig.axes[0].get_legend() is None


def test_quick_ratio_overlay_shares_one_axis(weekly):
    """Segments are row masks on one panel, so the period axis must be shared."""
    series = [(label, metrics.lifecycle_states(sub))
              for label, sub in weekly.segments("platform")]
    fig = plots.quick_ratio(series)
    assert len(fig.axes) == 1
