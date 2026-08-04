"""Rendering. Each function takes a metrics DataFrame and returns a Figure.

Nothing here computes anything — that is ``metrics.py``'s job. The split means
every figure has an exportable data twin (the table view every chart needs).

The figures are the DataDiner course figures, definition for definition, so a
chart produced here and the same chart produced there are the same picture:

- **Cohort heatmaps** — an ``RdYlGn`` scale normalized **within each age column**,
  so a cell's color says how that cohort did *for that age* rather than how big
  the number is. Age 0 is 100% for every cohort, so a global scale would spend
  half its range on a constant. No colorbar: the cells carry their own numbers.
  The leading ``Signups`` column is on that same ramp but scaled only against
  itself, so it reads as relative signup volume down the column — green is a
  bigger cohort — and never as a retention value. A black frame marks it off as
  the one column that is not an age, and the column names repeat along the top
  so a year of cohorts stays readable without the bottom axis in view.
- **Everything else** — seaborn's ``whitegrid`` theme and the ``muted`` palette,
  assigned by fixed slot so a lifecycle state keeps its color across every figure
  and every cut.
"""

from __future__ import annotations

import warnings

import matplotlib


def _in_notebook():
    """True only inside a Jupyter/IPython kernel (an inline canvas exists)."""
    try:
        from IPython import get_ipython
        shell = get_ipython()
        return shell is not None and shell.__class__.__name__ == "ZMQInteractiveShell"
    except Exception:
        return False


# Outside a notebook there is no inline canvas, so a GUI backend would pop a
# blocking window per figure. Pick Agg before pyplot is imported.
if not _in_notebook():
    matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402


# --- palette ---------------------------------------------------------------

# Fixed slot order: assign by index, never by rank. Past the end the palette
# cycles (see `_series_colors`) rather than failing — an overlay with more
# groups than colors is warned about, not refused.
PALETTE = sns.color_palette("muted")
HEATMAP_CMAP = sns.color_palette("RdYlGn", as_cmap=True)

# The histogram's single series color (its bands carry the categorical work).
HIST_BLUE = "#3498db"

# Above this many overlaid groups the lines stop being legible; warn so the
# caller can narrow the cut down.
MAX_SERIES = 30

# Views whose values are signed changes, and so are read either side of zero.
_DIVERGING_KINDS = {"churn_rate", "churn_counts", "vs_average"}


def _period_word(grain):
    """'Weeks' / 'Months' — the plural, for axis labels."""
    return f"{grain.capitalize()}s"


def _period_prefix(grain):
    """The title prefix that names a non-weekly grain ('Monthly ')."""
    return {"week": "", "month": "Monthly ", "day": "Daily "}.get(grain, "")


def _with_label(title, label):
    """Append a segment label to a title the way a cut is announced."""
    return title if label is None else f"{title} — {label}"


def _segment_name(labels):
    """The segment dimension(s) behind a set of ``col=value`` labels."""
    cols = []
    for label in labels:
        for part in str(label).split(","):
            col = part.split("=", 1)[0].strip()
            if col and col not in cols:
                cols.append(col)
    return ", ".join(cols)


def _series_colors(n, what="segments"):
    """One color per series, cycling the palette and warning when it is crowded."""
    if n > MAX_SERIES:
        warnings.warn(
            f"{n} {what} overlaid; this is hard to read — consider fewer groups "
            f"or specific values."
        )
    return [PALETTE[i % len(PALETTE)] for i in range(n)]


# --- cohort heatmaps -------------------------------------------------------

def _heatmap_title(kind, grain):
    """The five heatmap titles, grain-aware."""
    prefix = _period_prefix(grain)
    period = _period_word(grain)[:-1]          # 'Week'
    if kind == "retention_counts":
        return f"Cohort Retention Counts — Active Users per {period}"
    if kind == "retention_rate":
        return (f"{prefix}Cohort Retention Rate — % Still Active "
                f"(colored per column)")
    if kind == "churn_counts":
        return f"{prefix}Cohort Churn Counts — Users Lost per {period}"
    if kind == "churn_rate":
        return (f"{prefix}Cohort Churn Rate — pp Change in Retention "
                f"{period}-over-{period}")
    if kind == "vs_average":
        tail = f" per {period}" if grain == "week" else ""
        return (f"{prefix}Cohort vs Average — Deviation from Average "
                f"Retention{tail}")
    return kind


_VALUE_FORMATS = {
    "retention_rate": lambda v: f"{v:.1f}%",
    "retention_counts": lambda v: f"{int(v):,}",
    "churn_rate": lambda v: f"{v:+.1f}pp",
    "churn_counts": lambda v: f"{int(v):+,}",
    "vs_average": lambda v: f"{v:+.1f}pp",
}


def _column_normalized(values):
    """Min-max scale each column into 0..1, keeping NaN where the data is NaN.

    Normalizing per column is what makes the heatmap answer "how did this cohort
    do *at this age*". Age 0 is 100% for every cohort by construction, so a
    single global scale would spend its range on a constant and squash the 20-60%
    band a reader actually compares.
    """
    out = np.zeros_like(values, dtype=float)
    for j in range(values.shape[1]):
        col = values[:, j]
        valid = ~np.isnan(col)
        if valid.any():
            lo, hi = np.nanmin(col), np.nanmax(col)
            out[valid, j] = (col[valid] - lo) / (hi - lo) if hi > lo else 0.5
        out[~valid, j] = np.nan
    return out


def _ink(shade, both_poles=False):
    """Text color for a cell at this point on the ramp.

    Both poles of ``RdYlGn`` are dark and its middle is not, so a column read
    either side of a midpoint needs white ink at each end. A column read only
    low-to-high needs it at the top.
    """
    if both_poles:
        return "white" if shade > 0.85 or shade < 0.15 else "black"
    return "white" if shade > 0.6 else "black"


def cohort_heatmap(table, kind="retention_rate", grain="week", title=None,
                   label=None, annotate=True):
    """Render a cohort x age table as a heatmap.

    Parameters
    ----------
    table : the DataFrame from :func:`metrics.cohort_table` — cohort index, a
        leading ``Signups`` column, then one column per age.
    kind : which view it is; picks the title and the number format.
    grain : ``'week'`` or ``'month'`` — the period one column spans.
    label : a segment label like ``platform=mobile``, appended to the title.

    Color is normalized **within each age column** for all five views, so a cell
    reads as "how this cohort did at this age". The cells are annotated, so the
    figure carries no colorbar.

    The leading ``Signups`` column is on the same ramp, scaled only against its own
    values: it shows which cohorts were big and which were small relative to the
    rest of the file, and says nothing about retention. It is framed in black to
    set it apart from the ages. Every ``kind`` carries the same cohort sizes, so
    that column looks identical across all five views.

    Returns
    -------
    matplotlib Figure.
    """
    values = table.to_numpy(dtype=float)
    colored = _column_normalized(values)
    diverging = kind in _DIVERGING_KINDS
    fmt = _VALUE_FORMATS.get(kind, lambda v: f"{v:.1f}")

    figsize = (13, 8) if grain == "week" else (11, 6)
    fig, ax = plt.subplots(figsize=figsize)

    sns.heatmap(
        colored, cmap=HEATMAP_CMAP, vmin=0, vmax=1,
        linewidths=0.5, linecolor="white", ax=ax,
        cbar=False, mask=np.isnan(values),
        xticklabels=table.columns, yticklabels=table.index,
    )
    # Compact tick labels so a year of cohorts fits a screen without overflowing.
    # The column names repeat along the top: with a year of cohorts the bottom
    # axis is a screen away from the first rows, and the Signups column has to be
    # identifiable without scrolling back down to find its name.
    ax.tick_params(labelsize=6, top=True, labeltop=True)
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0)

    n_rows, n_cols = values.shape

    # A black rule around the Signups column. It is on the same ramp as the ages
    # now, so nothing else marks it as the one column that is not a retention
    # value — the frame is what keeps it from being read as age -1.
    ax.add_patch(plt.Rectangle(
        (0, 0), 1, n_rows, fill=False, edgecolor="black", linewidth=1.6,
        zorder=5, clip_on=False,
    ))

    if annotate:
        for i in range(n_rows):
            for j in range(n_cols):
                v = values[i, j]
                if np.isnan(v):
                    continue
                shade = colored[i, j]
                if j == 0:  # the Signups column
                    # Scaled against itself, so it uses the whole ramp and both
                    # of its dark ends. Bold keeps it legible as context.
                    ax.text(j + 0.5, i + 0.5, f"{int(v):,}", ha="center",
                            va="center", fontsize=5,
                            color=_ink(shade, both_poles=True),
                            fontweight="bold")
                    continue
                ax.text(j + 0.5, i + 0.5, fmt(v), ha="center", va="center",
                        fontsize=5, color=_ink(shade, both_poles=diverging))

    ax.set_title(_with_label(title or _heatmap_title(kind, grain), label),
                 fontsize=13, fontweight="bold")
    period = _period_word(grain)
    ax.set_xlabel(f"{period} Since Signup")
    ax.set_ylabel(f"Cohort {period[:-1]}")

    fig.tight_layout()
    return fig


# --- retention curve -------------------------------------------------------

def retention_curve(curves, grain="week", title=None, label=None):
    """Plot one or more average retention curves.

    Parameters
    ----------
    curves : a DataFrame from :func:`metrics.retention_curve`, or a list of
        ``(label, DataFrame)`` to overlay one line per segment.
    label : a segment label for the single-curve case, appended to the title.
    """
    sns.set_theme(style="whitegrid")
    series = curves if isinstance(curves, list) else [(None, curves)]
    colors = _series_colors(len(series))

    fig, ax = plt.subplots(figsize=(12, 6))
    xmax = 0
    for (name, curve), color in zip(series, colors):
        sns.lineplot(data=curve, x="age", y="retention_pct", color=color,
                     linewidth=2.5, ax=ax, label=name)
        if len(series) == 1:
            # Keep the single-curve look: the area reads as the surviving base.
            ax.fill_between(curve["age"], curve["retention_pct"], alpha=0.15,
                            color=color)
        xmax = max(xmax, int(curve["age"].max()))

    heading = title or "Overall Retention Curve"
    if len(series) > 1:
        seg_name = _segment_name(name for name, _ in series)
        heading += f" by {seg_name}"
        ax.legend(title=seg_name)
    else:
        heading = _with_label(heading, label)
    ax.set_title(heading, fontsize=16, fontweight="bold")
    ax.set_xlabel(f"{_period_word(grain)} Since First Activity")
    ax.set_ylabel("% of Cohort Still Active")
    ax.set_ylim(0, 105)
    ax.set_xlim(0, xmax)

    fig.tight_layout()
    return fig


# --- usage frequency -------------------------------------------------------

def usage_frequency(usage, title=None, label=None):
    """Histogram of average active days per month per user.

    The cadence read: mass near 20+ is a daily product, mass near 4 a weekly one,
    mass at 1 a monthly one. The three target lines mark those bands.
    """
    sns.set_theme(style="whitegrid")
    values = usage["avg_active_days_per_month"].dropna()

    fig, ax = plt.subplots(figsize=(12, 7))
    sns.histplot(values, discrete=True, kde=True, color=HIST_BLUE, alpha=0.6,
                 label="Your Users", ax=ax)

    bands = [(20, "#1b5e20", "--", "Daily Target (20+)"),
             (4, "#0d47a1", "--", "Weekly Target (4+)"),
             (1, "#b71c1c", ":", "Monthly Target (1+)")]
    for x, color, style, name in bands:
        ax.axvline(x=x, color=color, linestyle=style, linewidth=2, label=name)

    ax.set_title(
        _with_label(
            title or "Product Usage Frequency — Avg Days Active per Month per User",
            label),
        fontsize=16, fontweight="bold")
    ax.set_xlabel("Average Days Active per Month", fontsize=12)
    ax.set_ylabel("Number of Users", fontsize=12)

    upper = max(float(values.max()) if len(values) else 0.0,
                max(x for x, *_ in bands)) + 2
    ax.set_xlim(0, upper)
    ax.set_xticks(np.arange(0, upper, 2 if upper > 12 else 1))
    ax.legend(loc="upper right")
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    return fig


# --- lifecycle -------------------------------------------------------------

# One `muted` slot per state, fixed, so a state keeps its color across every
# figure and every cut. Gains take slots 0/2/4, losses 1/3 at 70% opacity, which
# is what pushes the two halves of the bridge apart visually.
_LIFECYCLE_COLORS = {
    "New": PALETTE[0],
    "Retained": PALETTE[2],
    "Resurrected": PALETTE[4],
    "At-Risk": PALETTE[1],
    "Churned": PALETTE[3],
}
_LOSS_ALPHA = 0.7


def lifecycle_bars(states, grain="week", title=None, label=None):
    """Stacked bars of the lifecycle states, gains up and losses down."""
    sns.set_theme(style="whitegrid")
    fig, ax = plt.subplots(figsize=(14, 6))
    x = range(len(states))
    width = 0.8

    ax.bar(x, states["New"], width, label="New",
           color=_LIFECYCLE_COLORS["New"])
    ax.bar(x, states["Retained"], width, bottom=states["New"],
           label="Retained", color=_LIFECYCLE_COLORS["Retained"])
    ax.bar(x, states["Resurrected"], width,
           bottom=states["New"] + states["Retained"],
           label="Resurrected", color=_LIFECYCLE_COLORS["Resurrected"])
    ax.bar(x, -states["At-Risk"], width, label="At-Risk",
           color=_LIFECYCLE_COLORS["At-Risk"], alpha=_LOSS_ALPHA)
    ax.bar(x, -states["Churned"], width, bottom=-states["At-Risk"],
           label="Churned", color=_LIFECYCLE_COLORS["Churned"],
           alpha=_LOSS_ALPHA)
    ax.axhline(y=0, color="grey", linewidth=0.8)

    period = _period_word(grain)[:-1]
    cadence = {"week": "Weekly", "month": "Monthly", "day": "Daily"}.get(
        grain, f"{period}ly")
    ax.set_title(
        _with_label(title or f"User Lifecycle Buckets — {cadence} Breakdown",
                    label),
        fontsize=16, fontweight="bold")
    ax.set_xlabel(period)
    ax.set_ylabel("Users")
    ax.legend(loc="lower left")
    _period_ticks(ax, states["period"], x)

    fig.tight_layout()
    return fig


def quick_ratio(states, grain="week", title=None, label=None):
    """The Quick Ratio line: (New + Resurrected) / Churned, against the 1.0 line.

    Parameters
    ----------
    states : a DataFrame from :func:`metrics.lifecycle_states`, or a list of
        ``(label, DataFrame)`` to overlay one line per segment. Segments share the
        panel's period axis, so their lines are directly comparable — which is the
        whole point of putting them on one figure rather than one each.
    label : a segment label for the single-line case, appended to the title.
    """
    sns.set_theme(style="whitegrid")
    series = states if isinstance(states, list) else [(None, states)]
    colors = _series_colors(len(series))

    fig, ax = plt.subplots(figsize=(14, 6))
    for (name, frame), color in zip(series, colors):
        sns.lineplot(data=frame, x="period", y="Quick Ratio", color=color,
                     linewidth=2.5, ax=ax, label=name)
    # Break-even, drawn once however many lines share the axis.
    ax.axhline(y=1, color="grey", linewidth=1, linestyle="--")

    heading = title or "Quick Ratio — (New + Resurrected) / Churned"
    if len(series) > 1:
        seg_name = _segment_name(name for name, _ in series)
        heading += f" by {seg_name}"
        ax.legend(title=seg_name)
    else:
        heading = _with_label(heading, label)
    ax.set_title(heading, fontsize=16, fontweight="bold")
    ax.set_xlabel(_period_word(grain)[:-1])
    ax.set_ylabel("Quick Ratio")
    ax.tick_params(axis="x", rotation=45)

    fig.tight_layout()
    return fig


def _period_ticks(ax, periods, x, step=4):
    """Label every `step`-th period, rotated, so the dates stay readable."""
    x = list(x)
    positions = list(range(0, len(periods), step))
    ax.set_xticks([x[i] for i in positions])
    ax.set_xticklabels(
        [pd.Timestamp(periods.iloc[i]).strftime("%Y-%m-%d") for i in positions],
        rotation=45,
    )
