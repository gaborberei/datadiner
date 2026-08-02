"""
DataDiner — Report module
=========================
Bundle an analysis run into a self-contained, shareable output folder:

    output/<dataset>/<YYYY-MM-DD-HHMM>/
        report.md     title + provenance, one section per view (read + chart + data)
        charts/       PNGs, one subfolder per cut: overall/ for un-segmented
                      views, <segment_col>/ (or <col>_x_<col>/) for segmented
                      ones — one PNG per figure, segmented views one per group
        data/         CSVs (cohort matrices, lifecycle states, usage-per-user)

This is the *packaging* layer — it never reimplements analysis. It saves the
figures and DataFrames the `retention` views already return, plus the cohort
matrices from `retention.cohort_matrix`, and accumulates a Markdown report whose
charts are embedded with **relative** paths so it renders on GitHub and anywhere
the folder is opened.

Two entry points:

- ``AnalysisReport`` — build a run incrementally (one ``.section()`` per view),
  e.g. while driving the interactive retention exercise, then ``.save()``.
- ``overall_report(df, dataset, ...)`` — one shot: run the whole Phase-1 overall
  sequence and write the folder.

Usage:
    from datadiner.io import load_events
    from datadiner.report import overall_report

    df = load_events("datasets/notion/notion_causal_events.csv")
    run = overall_report(df, dataset="notion",
                         source="datasets/notion/notion_causal_events.csv",
                         active_event="page_created")
    print(run)   # -> output/notion/<timestamp>/
"""

import json
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from .io import summarize_events
from .retention import (
    _announce_figure,
    _safe_label,
    no_figure_display,
    cohort_matrix,
    usage_frequency,
    retention_curve,
    lifecycle_states,
    retention_counts_heatmap,
    retention_rate_heatmap,
    churn_counts_heatmap,
    churn_rate_heatmap,
    vs_average_heatmap,
)


# ---------------------------------------------------------------------------
# Internal helpers — normalizing the varied shapes views return
# ---------------------------------------------------------------------------

def _slugify(text):
    """Filesystem/anchor-safe slug from a section title, e.g. 'Churn rate' -> 'churn_rate'."""
    slug = re.sub(r"[^\w]+", "_", text.strip().lower())
    return slug.strip("_") or "section"


def _figures_in(obj):
    """Recursively yield Figure objects out of a view-return fragment."""
    if isinstance(obj, Figure):
        yield obj
    elif isinstance(obj, (tuple, list)):
        for item in obj:
            yield from _figures_in(item)


def _normalize_figs(fig):
    """Normalize a `fig` argument to a list of (label, Figure).

    Handles every shape the retention views return:
      - None                          -> []
      - a single Figure               -> [(None, fig)]
      - (fig, ax)                      -> [(None, fig)]
      - {'bars': fig1, ...}           -> [('bars', fig1), ...]   (named figures)
      - (fig1, fig2)                  -> [('1', fig1), ('2', fig2)]
      - [(label, ...), ...]           -> one (label[, idx], fig) per group
                                          (segmented heatmaps / lifecycle)
    """
    if fig is None:
        return []
    if isinstance(fig, Figure):
        return [(None, fig)]
    if isinstance(fig, dict):
        return [(name, f) for name, f in fig.items() if isinstance(f, Figure)]
    # Segmented return: list of (label, ...) tuples keyed by a string label.
    if (isinstance(fig, list) and fig and isinstance(fig[0], tuple)
            and isinstance(fig[0][0], str)):
        out = []
        for item in fig:
            label, rest = item[0], item[1:]
            figs = list(_figures_in(rest))
            for i, f in enumerate(figs):
                sub = label if len(figs) == 1 else f"{label}_{i + 1}"
                out.append((sub, f))
        return out
    # A bare tuple/list of figures (and maybe axes): (fig, ax) or (fig1, fig2).
    figs = list(_figures_in(fig))
    if len(figs) == 1:
        return [(None, figs[0])]
    return [(str(i + 1), f) for i, f in enumerate(figs)]


def _charts_subdir(figs):
    """Pick the ``charts/`` subfolder for a section's figures.

    Segmented views label their figures ``col=value`` (or ``col=v, col2=v2``), so
    the segment column(s) can be read straight off the first labelled figure —
    those go to ``charts/<col>/`` (combinations to ``charts/<col>_x_<col2>/``).
    Everything else is an overall view and goes to ``charts/overall/``.
    """
    for label, _ in figs:
        if label is not None and "=" in str(label):
            cols = [part.split("=", 1)[0].strip() for part in str(label).split(",")]
            return _slugify("_x_".join(cols))
    return "overall"


def _normalize_data(data):
    """Normalize a `data` argument to a list of (name, DataFrame).

    Handles: None; a DataFrame; {name: DataFrame}; or a list of (label, DataFrame).
    """
    if data is None:
        return []
    if isinstance(data, pd.DataFrame):
        return [(None, data)]
    if isinstance(data, dict):
        return [(name, d) for name, d in data.items()
                if isinstance(d, pd.DataFrame)]
    out = []
    for item in data:
        if isinstance(item, tuple) and len(item) >= 2 \
                and isinstance(item[1], pd.DataFrame):
            out.append((item[0], item[1]))
    return out


def _keep_index(df):
    """Keep a DataFrame's index in the CSV only when it carries meaning."""
    return not isinstance(df.index, pd.RangeIndex)


def _df_preview_md(df, max_rows=5, max_cols=8):
    """Render the head of a DataFrame as a GitHub-flavored Markdown table."""
    show_index = _keep_index(df)
    truncated_cols = df.shape[1] > max_cols
    view = df.iloc[:max_rows, :max_cols]

    headers = ([df.index.name or ""] if show_index else []) + \
        [str(c) for c in view.columns]
    if truncated_cols:
        headers.append("…")

    def _fmt(v):
        if isinstance(v, float):
            return f"{v:.2f}"
        return str(v)

    lines = ["| " + " | ".join(headers) + " |",
             "| " + " | ".join("---" for _ in headers) + " |"]
    for idx, row in view.iterrows():
        cells = ([str(idx)] if show_index else []) + [_fmt(v) for v in row]
        if truncated_cols:
            cells.append("…")
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API — incremental report builder
# ---------------------------------------------------------------------------

class AnalysisReport:
    """A single analysis run, written to ``output/<dataset>/<run_id>/``.

    Build it up one view at a time with :meth:`section`, then :meth:`save`.
    Figures are saved from the objects the views return, so it works whether or
    not the view was called with ``save=``.

    A run is **resumable**: each :meth:`save` writes a ``.report_state.json``
    manifest alongside ``report.md``. Re-opening the same run folder (via
    ``resume=True`` or :meth:`open_or_create`) reloads the accumulated sections,
    so a later process can add to the same folder instead of starting a new one.
    """

    MANIFEST_NAME = ".report_state.json"

    def __init__(self, dataset, df=None, source=None, base_dir="output",
                 run_id=None, resume=False):
        self.dataset = dataset
        self.run_id = run_id or datetime.now().strftime("%Y-%m-%d-%H%M")
        self.dir = Path(base_dir) / dataset / self.run_id
        self.charts_dir = self.dir / "charts"
        self.data_dir = self.dir / "data"
        for d in (self.charts_dir, self.data_dir):
            d.mkdir(parents=True, exist_ok=True)

        manifest = self.dir / self.MANIFEST_NAME
        if (resume or manifest.exists()) and manifest.exists():
            state = json.loads(manifest.read_text())
            self._header = state["header"]
            self._sections = state["sections"]
        else:
            self._sections = []
            self._header = self._build_header(df, source)

    @classmethod
    def open_or_create(cls, dataset, df=None, source=None, base_dir="output"):
        """Resume the most recent run folder for ``dataset``, or create one.

        Use this to keep a whole interactive session in a **single** folder:
        every step re-opens the same run and appends its section, instead of
        stamping a new timestamped folder per step.
        """
        parent = Path(base_dir) / dataset
        runs = sorted(p for p in parent.glob("*")
                      if p.is_dir() and (p / cls.MANIFEST_NAME).exists())
        if runs:
            return cls(dataset, df=df, source=source, base_dir=base_dir,
                       run_id=runs[-1].name, resume=True)
        return cls(dataset, df=df, source=source, base_dir=base_dir)

    def _build_header(self, df, source):
        lines = [
            f"# Retention analysis — {self.dataset}",
            "",
            f"- **Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"- **Run:** `{self.run_id}`",
        ]
        if source:
            lines.append(f"- **Source:** `{source}`")
        if df is not None:
            s = summarize_events(df)
            lines.append(
                f"- **Events:** {s['rows']:,} rows · {s['users']:,} users · "
                f"{s['start']:%Y-%m-%d} → {s['end']:%Y-%m-%d}"
            )
        lines.append("")
        return "\n".join(lines)

    def section(self, title, fig=None, data=None, note="", slug=None, subdir=None):
        """Add one view to the report: its read, chart(s), and data table(s).

        Parameters
        ----------
        title : str          section heading.
        fig : optional        a Figure, (fig, ax), (fig1, fig2), a {name: Figure}
                              dict, or the list[(label, ...)] a segmented view
                              returns. Each figure is saved as a PNG.
        data : optional       a DataFrame, {name: DataFrame}, or list of
                              (label, DataFrame); each is written as a CSV.
        note : str            the plain-English read ("what it says / why").
        slug : optional str   filename stem; defaults to a slug of `title`.
        subdir : optional str the ``charts/`` subfolder for the PNGs. Defaults to
                              the segment column(s) read off segmented-view labels
                              (``platform``, ``platform_x_channel``), else
                              ``overall``. Pass it explicitly for segmented views
                              whose figures carry no ``col=value`` label (e.g. a
                              ``retention_curve`` overlay).
        """
        slug = slug or _slugify(title)
        figs = _normalize_figs(fig)
        tables = _normalize_data(data)
        subdir = _slugify(subdir) if subdir else _charts_subdir(figs)
        (self.charts_dir / subdir).mkdir(exist_ok=True)

        chart_md = []
        for label, figure in figs:
            stem = slug if label is None else f"{slug}_{_safe_label(str(label))}"
            rel = f"charts/{subdir}/{stem}.png"
            figure.savefig(self.dir / rel, dpi=150, bbox_inches="tight")
            _announce_figure(self.dir / rel)
            # Release the figure once it's on disk — the PNG is the artifact, and
            # leaving figures open piles up memory across a multi-view run.
            plt.close(figure)
            caption = f" — {label}" if label is not None else ""
            chart_md.append(f"![{title}{caption}]({rel})")

        data_md = []
        for name, df in tables:
            stem = slug if name is None else f"{slug}_{_safe_label(str(name))}"
            rel = f"data/{stem}.csv"
            df.to_csv(self.dir / rel, index=_keep_index(df))
            data_md.append((rel, df))

        parts = [f"## {title}", ""]
        if note:
            parts += [note.strip(), ""]
        parts += chart_md
        if chart_md:
            parts.append("")
        for rel, df in data_md:
            parts.append(f"**Data:** [`{Path(rel).name}`]({rel})")
            parts.append("")
            parts.append(_df_preview_md(df))
            parts.append("")
        block = {"slug": slug, "md": "\n".join(parts).rstrip() + "\n"}

        # Upsert by slug: re-running a view updates its section in place rather
        # than appending a duplicate.
        for i, existing in enumerate(self._sections):
            if existing["slug"] == slug:
                self._sections[i] = block
                break
        else:
            self._sections.append(block)
        return self

    def save(self):
        """Write ``report.md`` + the resume manifest; return the run dir Path."""
        body = self._header + "\n" + "\n".join(s["md"] for s in self._sections)
        report_path = self.dir / "report.md"
        report_path.write_text(body.rstrip() + "\n")
        (self.dir / self.MANIFEST_NAME).write_text(
            json.dumps({"header": self._header, "sections": self._sections},
                       indent=2)
        )
        print(f"Report written to {self.dir}")
        return self.dir

    def assert_phase1_complete(self):
        """Raise ``IncompleteRunError`` if any canonical Phase-1 view is missing.

        Thin instance wrapper around :func:`assert_phase1_complete`; call it at
        the end of the guided exercise (after :func:`ensure_phase1`) so a run can
        never be saved silently missing a canonical view. Returns ``self``.
        """
        assert_phase1_complete(self)
        return self


# ---------------------------------------------------------------------------
# Public API — the cohort heatmap block (all five views)
# ---------------------------------------------------------------------------

# The five cohort heatmaps, in reading order: (title, view_fn, matrix kind, note).
# Single source of truth so no caller can silently emit a subset.
_COHORT_VIEWS = [
    ("Cohort retention rate", retention_rate_heatmap, "rate",
     "Each cohort's % still active by age. Color is column-normalized "
     "(good *for that age*); read the grey Users column before trusting a rate."),
    ("Cohort retention counts", retention_counts_heatmap, "counts",
     "Absolute users still active per cohort/age — the size of the base, not its "
     "quality. Read alongside the rate view."),
    ("Cohort churn rate", churn_rate_heatmap, "churn_rate",
     "Period-over-period change in retention (pp). A sharp diagonal is the "
     "signature of a calendar-period shock — worth investigating, not a proven cause."),
    ("Cohort churn counts", churn_counts_heatmap, "churn_counts",
     "Absolute users lost per cohort/age — the magnitude behind the churn-rate view."),
    ("Cohort vs average", vs_average_heatmap, "vs_average",
     "Deviation from the average retention for each age: positive = this cohort "
     "beat its peers, negative = lagged. Best for spotting which cohort broke."),
]


def cohort_sections(report, df, granularity="weekly", active_event=None,
                    notes=None, skip_existing=False):
    """Add all **five** cohort heatmaps (+ their matrices) to ``report``.

    Renders rate, counts, churn-rate, churn-counts and vs-average in reading
    order, each with its chart and the matching ``cohort_matrix`` CSV. This is
    the single place that defines "the cohort block", so the guided exercise and
    :func:`overall_report` always emit the complete set.

    ``notes`` (slug -> str) overrides the default read for a view — so the guided
    exercise can carry its own live read. ``skip_existing`` leaves any view whose
    slug is already in ``report`` untouched (used by :func:`ensure_phase1` to fill
    only the gaps without re-rendering or clobbering the model's notes).
    """
    notes = notes or {}
    present = {s["slug"] for s in report._sections}
    with no_figure_display():
        for title, view_fn, kind, note in _COHORT_VIEWS:
            if skip_existing and _slugify(title) in present:
                continue
            fig, _ax = view_fn(df, granularity=granularity,
                               active_event=active_event)
            report.section(
                title, fig=fig,
                data=cohort_matrix(df, granularity=granularity, kind=kind,
                                   active_event=active_event),
                note=notes.get(_slugify(title), note),
            )
    return report


# ---------------------------------------------------------------------------
# Public API — the three overview views + the canonical Phase-1 checklist
# ---------------------------------------------------------------------------

# Builders wrap each overview view's differing return shape into the
# (fig, data) pair ``section`` expects.
def _usage_frequency_section(df, active_event=None):
    fig, _ax, avg_days = usage_frequency(df, active_event=active_event)
    return fig, avg_days


def _retention_curve_section(df, active_event=None):
    fig, _ax = retention_curve(df, active_event=active_event)
    return fig, None


def _lifecycle_section(df, active_event=None):
    states_df, (fig_bars, fig_qr) = lifecycle_states(df, active_event=active_event)
    return {"bars": fig_bars, "quick_ratio": fig_qr}, states_df


# The three overview views, in workflow order: (title, builder, note).
# Single source of truth, mirroring `_COHORT_VIEWS`, so the guided exercise and
# `overall_report` share one definition.
_OVERVIEW_VIEWS = [
    ("Usage frequency", _usage_frequency_section,
     "Average active days per month per user (active weeks where the grain is "
     "weekly and no day count is carried) — the engagement cadence that frames "
     "what 'active' should mean (daily vs weekly vs monthly)."),
    ("Retention curve", _retention_curve_section,
     "The overall decay shape: how fast the average cohort loses users "
     "over the weeks since first activity."),
    ("Lifecycle states", _lifecycle_section,
     "Weekly New / Retained / Resurrected / At-Risk / Churned, and the "
     "Quick Ratio = (New + Resurrected) / Churned (>1 growing net, <1 shrinking)."),
]

# The canonical Phase-1 section slugs (overview, then cohort), in workflow order.
PHASE1_REQUIRED_SLUGS = (
    [_slugify(title) for title, *_ in _OVERVIEW_VIEWS]
    + [_slugify(title) for title, *_ in _COHORT_VIEWS]
)


class IncompleteRunError(ValueError):
    """A guided run is missing one or more canonical Phase-1 views."""


def overview_sections(report, df, active_event=None, notes=None,
                      skip_existing=False):
    """Add the three overview views (usage frequency, retention curve, lifecycle).

    Counterpart to :func:`cohort_sections` for the non-cohort Phase-1 views. See
    that function for ``notes`` / ``skip_existing`` semantics.
    """
    notes = notes or {}
    present = {s["slug"] for s in report._sections}
    with no_figure_display():
        for title, builder, note in _OVERVIEW_VIEWS:
            if skip_existing and _slugify(title) in present:
                continue
            fig, data = builder(df, active_event)
            report.section(title, fig=fig, data=data,
                           note=notes.get(_slugify(title), note))
    return report


def ensure_phase1(report, df, active_event=None, granularity="weekly", notes=None):
    """Generate any canonical Phase-1 view ``report`` is still missing.

    Idempotent: views already added (by slug) are left untouched, so the guided
    exercise can hand-build sections with its own reads and then call this to fill
    the gaps without duplicating or clobbering them. ``notes`` (slug -> str)
    supplies a read for views generated here. Returns ``report``.
    """
    overview_sections(report, df, active_event=active_event, notes=notes,
                      skip_existing=True)
    cohort_sections(report, df, granularity=granularity, active_event=active_event,
                    notes=notes, skip_existing=True)
    return report


def assert_phase1_complete(report):
    """Raise :class:`IncompleteRunError` if a canonical Phase-1 view is missing.

    The completeness **guard** — call it at the end of the guided exercise (after
    :func:`ensure_phase1`) before the final ``save()``. Names the missing slugs.
    """
    present = {s["slug"] for s in report._sections}
    missing = [s for s in PHASE1_REQUIRED_SLUGS if s not in present]
    if missing:
        raise IncompleteRunError(
            "run is missing canonical Phase-1 view(s): "
            + ", ".join(missing)
            + " — call ensure_phase1(report, df, active_event=...) to generate them."
        )
    return report


# ---------------------------------------------------------------------------
# Public API — one-shot overall report
# ---------------------------------------------------------------------------

def overall_report(df, dataset, source=None, active_event=None,
                   granularity="weekly", base_dir="output"):
    """Run the Phase-1 overall sequence and write a full output folder.

    Mirrors the default workflow order: usage frequency → retention curve →
    lifecycle → all five cohort heatmaps (rate, counts, churn-rate,
    churn-counts, vs-average), un-segmented. Returns the run directory Path.

    `active_event` (e.g. the brief's core_action) is applied to every view that
    supports it, so retention means "did the core action".
    """
    report = AnalysisReport(dataset, df=df, source=source, base_dir=base_dir)

    overview_sections(report, df, active_event=active_event)
    cohort_sections(report, df, granularity=granularity,
                    active_event=active_event)

    assert_phase1_complete(report)
    return report.save()
