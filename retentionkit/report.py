"""Bundling a run into a folder someone else can open.

    output/<dataset>/<YYYY-MM-DD-HHMM>/
        report.md      provenance, the data-quality read, one section per view
        run.json       the manifest — what this run already contains
        charts/        PNGs — overall/ for un-segmented, <segment_col>/ for cuts
        data/          the CSV behind every figure (the table view)

This is packaging only: it renders what ``metrics`` computed and ``plots`` drew,
and never does arithmetic of its own. Every figure is written with its data, so
no number in the report is reachable only through a picture.

A run is **resumable**. ``run.json`` records every section written, so passing an
existing ``run_id`` back into :func:`run_report` appends to that folder instead of
starting a new one: the cuts already there are skipped, the new cut is added, and
``report.md`` is rewritten with all of them in order. Adding a segment cut as an
afterthought is the common case, and it should not cost a second copy of the
overall figures.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import metrics, plots
from .io import format_quality_report, quality_report
from .matrix import ActivityMatrix

# The canonical set, in reading order: cadence first (it frames what "active"
# should mean), then the decay shape, then the cohort detail, then the flow.
COHORT_KINDS = ("retention_rate", "retention_counts", "churn_rate",
                "churn_counts", "vs_average")


def _slug(text):
    return re.sub(r"[^\w]+", "_", str(text).strip().lower()).strip("_") or "section"


def _safe(label):
    return str(label).replace("=", "-").replace(", ", "_").replace(" ", "_")


class Run:
    """One analysis run, written incrementally to a folder.

    Passing a ``run_id`` that already exists on disk *resumes* that run: its
    manifest is loaded, so sections written earlier survive into the next
    ``save()`` and :meth:`has_views` can report what is already there.
    """

    MANIFEST = "run.json"

    def __init__(self, dataset, out_dir="output", run_id=None, source=None,
                 header_lines=()):
        self.dataset = dataset
        self.run_id = run_id or datetime.now().strftime("%Y-%m-%d-%H%M")
        self.dir = Path(out_dir) / _slug(dataset) / self.run_id
        (self.dir / "charts").mkdir(parents=True, exist_ok=True)
        (self.dir / "data").mkdir(parents=True, exist_ok=True)
        self.source = source
        self._sections = []
        self._header = list(header_lines)
        self.resumed = self._load_manifest()

    def _load_manifest(self):
        """Adopt an existing run's sections. Returns True if one was found."""
        path = self.dir / self.MANIFEST
        if not path.exists():
            return False
        try:
            saved = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            # A manifest we cannot read is not worth failing a run over; the
            # folder simply behaves like a fresh one and gets rewritten.
            return False
        self._sections = [s for s in saved.get("sections", [])
                          if "slug" in s and "md" in s]
        # An explicit value wins; otherwise keep what the run was opened with.
        self.source = self.source or saved.get("source")
        self._header = self._header or list(saved.get("header", []))
        return True

    def has_views(self, slugs):
        """True when every one of ``slugs`` is already a section in this run."""
        present = {s["slug"] for s in self._sections}
        return bool(slugs) and all(slug in present for slug in slugs)

    def section(self, title, fig=None, data=None, note="", subdir="overall",
                slug=None):
        """Add one view: its read, its chart, and the table behind it.

        Re-adding a slug that is already present replaces it where it stands, so
        resuming a run cannot duplicate a section or shuffle the reading order.
        """
        slug = slug or _slug(title)
        parts = [f"## {title}", ""]
        if note:
            parts += [note.strip(), ""]

        if fig is not None:
            rel = f"charts/{_slug(subdir)}/{slug}.png"
            (self.dir / rel).parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(self.dir / rel, dpi=150, bbox_inches="tight",
                        facecolor=fig.get_facecolor())
            # The PNG is the artifact; holding figures open piles up memory
            # across a run with many segment cuts.
            plt.close(fig)
            print(f"📊 saved {self.dir / rel}")
            parts += [f"![{title}]({rel})", ""]

        if data is not None:
            rel = f"data/{slug}.csv"
            keep_index = not isinstance(data.index, pd.RangeIndex)
            data.to_csv(self.dir / rel, index=keep_index)
            parts += [f"**Data:** [`{Path(rel).name}`]({rel})", ""]

        entry = {"slug": slug, "md": "\n".join(parts).rstrip() + "\n"}
        for i, existing in enumerate(self._sections):
            if existing["slug"] == slug:
                self._sections[i] = entry
                break
        else:
            self._sections.append(entry)
        return self

    def save(self):
        """Write ``report.md`` and the manifest; return the run directory."""
        head = [f"# Retention analysis — {self.dataset}", "",
                f"- **Generated:** {datetime.now():%Y-%m-%d %H:%M}"]
        if self.source:
            head.append(f"- **Source:** `{self.source}`")
        head += list(self._header) + [""]
        body = "\n".join(head) + "\n" + "\n".join(s["md"] for s in self._sections)
        (self.dir / "report.md").write_text(body.rstrip() + "\n")
        (self.dir / self.MANIFEST).write_text(json.dumps({
            "run_id": self.run_id,
            "dataset": self.dataset,
            "source": self.source,
            "header": list(self._header),
            "sections": self._sections,
        }, indent=2) + "\n")
        print(f"Report written to {self.dir}")
        return self.dir


def _usage_table(usage):
    """The histogram's table twin: one row per bin, not per user.

    The per-user frame behind it is 100k+ rows; what a reader needs from the
    chart is the shape, so the CSV carries the same bins the bars show.
    """
    values = usage["avg_active_days_per_month"].dropna()
    bins = values.apply(np.floor).astype(int).value_counts().sort_index()
    table = bins.rename("users").to_frame()
    table.index.name = "active_days_per_month"
    table["share"] = (table["users"] / table["users"].sum()).round(4)
    return table


def _provenance(am, label=None):
    """The cut's one-line source note.

    The figures carry only their title (that is the DataDiner figure definition),
    so the panel this cut was drawn from is stated in ``report.md`` instead —
    every section still says which users, how many periods, and over what span.
    """
    span = f"{am.periods[0]:%Y-%m-%d} → {am.periods[-1]:%Y-%m-%d}"
    base = f"{am.n_users:,} users · {am.n_periods} {am.grain}s · {span}"
    return f"*{label} · {base}*" if label else f"*{base}*"


def _view_slugs(suffix="", with_usage=True, overlaid=False):
    """Every section slug :func:`add_views` writes for one cut, in order.

    With ``overlaid`` the two line charts are left out: a segmented run draws them
    once for the whole cut instead of once per value (see :func:`add_overlays`).
    Keeping this in step with what ``add_views`` actually writes is what makes
    ``skip_existing`` correct on a resumed run.
    """
    slugs = [f"usage_frequency{suffix}"] if with_usage else []
    if not overlaid:
        slugs.append(f"retention_curve{suffix}")
    slugs += [f"cohort_{kind}{suffix}" for kind in COHORT_KINDS]
    slugs.append(f"lifecycle_states{suffix}")
    if not overlaid:
        slugs.append(f"quick_ratio{suffix}")
    return slugs


def _overlay_slugs(subdir):
    """The two combined line charts a segmented cut writes."""
    return [f"retention_curve_by_{_slug(subdir)}",
            f"quick_ratio_by_{_slug(subdir)}"]


def add_views(run, am, daily_am=None, label=None, subdir="overall",
              skip_existing=False, overlaid=False):
    """Add the four figure groups for one cut of the data.

    Parameters
    ----------
    run : the :class:`Run` to append to.
    am : the period-grain matrix (weekly or monthly) — cohorts, curve, lifecycle.
    daily_am : the day-grain matrix, for the usage-frequency cadence view. Skipped
        when absent (a log that is already coarser than daily has no days to count).
    label : segment label like ``platform=mobile``, or None for the overall cut.
    subdir : the ``charts/`` subfolder these figures belong in.
    skip_existing : when this cut is already complete in ``run``, leave it alone.
        This is what makes resuming a run cheap — appending a segment cut should
        not redraw the overall figures that are already sitting in the folder.
    overlaid : omit the retention curve and Quick Ratio, because they are being
        drawn once for every segment together by :func:`add_overlays`. The two
        line charts are the ones worth comparing on a shared axis; the histogram,
        the heatmaps and the stacked lifecycle bars are not, so they stay here.
    """
    suffix = f"_{_safe(label)}" if label else ""
    if skip_existing and run.has_views(
            _view_slugs(suffix, daily_am is not None, overlaid)):
        print(f"↩︎  {label or 'overall'} already in this run — skipped")
        return run

    sub = _provenance(am, label)
    grain = am.grain

    if daily_am is not None:
        usage = metrics.usage_frequency(daily_am)
        run.section(
            f"Usage frequency{f' — {label}' if label else ''}",
            fig=plots.usage_frequency(usage, label=label),
            data=_usage_table(usage),
            note=f"{sub}\n\nHow often a user shows up in a month, averaged over "
                 "the months they were active. This frames what 'active' should "
                 "mean: a mass at 20+ days is a daily product, a mass at 4 a "
                 "weekly one. Read it before trusting any retention number "
                 "computed on a shorter period.",
            subdir=subdir, slug=f"usage_frequency{suffix}",
        )

    if not overlaid:
        curve = metrics.retention_curve(am)
        run.section(
            f"Retention curve{f' — {label}' if label else ''}",
            fig=plots.retention_curve(curve, grain=grain, label=label),
            data=curve,
            note=f"{sub}\n\nThe average cohort's decay. The `cohorts` column says "
                 f"how many cohorts are old enough to contribute at each age — the "
                 f"tail is built on fewer cohorts than the head, so read it with "
                 f"that in mind.",
            subdir=subdir, slug=f"retention_curve{suffix}",
        )

    notes = {
        "retention_rate": "Each cohort's % still active by age. Color is normalized within "
                "each age column — a cell says how this cohort did *for that "
                "age*, not how big the number is. Check the Signups column "
                "before reading anything into a small cohort's rate.",
        "retention_counts": "The absolute size of the surviving base — how many users, "
                  "not how good the retention is. Read it beside the rate view.",
        "churn_rate": "Period-over-period change in retention: **negative is "
                      "retention lost**, positive a net gain from returning "
                      "users. A stripe running diagonally means many cohorts "
                      "moved at the same calendar moment — worth investigating, "
                      "not a proven cause.",
        "churn_counts": "The absolute users behind the churn-rate view, colored "
                        "the same way — negative is users lost.",
        "vs_average": "Each cohort against the average at the same age: positive "
                      "beat its peers, negative lagged. The fastest way to spot "
                      "which cohort broke.",
    }
    for kind in COHORT_KINDS:
        table = metrics.cohort_table(am, kind=kind)
        run.section(
            f"Cohort {kind.replace('_', ' ')}{f' — {label}' if label else ''}",
            fig=plots.cohort_heatmap(table, kind=kind, grain=grain, label=label),
            data=table, note=f"{sub}\n\n{notes[kind]}",
            subdir=subdir, slug=f"cohort_{kind}{suffix}",
        )

    states = metrics.lifecycle_states(am)
    run.section(
        f"Lifecycle states{f' — {label}' if label else ''}",
        fig=plots.lifecycle_bars(states, grain=grain, label=label),
        data=states,
        note=f"{sub}\n\nGains above the line, losses below. "
             + metrics.CHURN_DEFINITION.format(period=grain),
        subdir=subdir, slug=f"lifecycle_states{suffix}",
    )
    if not overlaid:
        run.section(
            f"Quick Ratio{f' — {label}' if label else ''}",
            fig=plots.quick_ratio(states, grain=grain, label=label),
            note=f"{sub}\n\n(New + Resurrected) / Churned. Above 1 the user base "
                 "grows on net, below 1 it shrinks — regardless of what the "
                 "headline count does.",
            subdir=subdir, slug=f"quick_ratio{suffix}",
        )
    return run


def _by_segment(frames):
    """Stack per-segment frames into one table with a leading ``segment`` column.

    The overlay is one picture over several cuts, so its data twin has to name
    which line each row belongs to — otherwise the numbers behind the figure are
    only reachable by re-running the segmentation.
    """
    stacked = []
    for name, frame in frames:
        part = frame.copy()
        part.insert(0, "segment", name)
        stacked.append(part)
    return pd.concat(stacked, ignore_index=True)


def add_overlays(run, am, masks, subdir, skip_existing=False):
    """Draw the retention curve and Quick Ratio once, one line per segment.

    Reading three Quick Ratio charts side by side is exactly the comparison a
    reader cannot make by flipping between images, so the segmented run puts the
    lines on a shared axis instead. Every segment is a row mask on the same panel,
    so the period axis is identical across lines by construction.
    """
    slugs = _overlay_slugs(subdir)
    if skip_existing and run.has_views(slugs):
        print(f"↩︎  {_slug(subdir)} overlays already in this run — skipped")
        return run

    grain = am.grain
    cuts = [(label, am.where(mask)) for label, mask in masks]
    seg_name = plots._segment_name(label for label, _ in cuts)
    sub = _provenance(am, f"{len(cuts)} {seg_name} segments")
    curve_slug, ratio_slug = slugs

    curves = [(label, metrics.retention_curve(cut)) for label, cut in cuts]
    run.section(
        f"Retention curve by {seg_name}",
        fig=plots.retention_curve(curves, grain=grain),
        data=_by_segment(curves),
        note=f"{sub}\n\nOne line per segment, on a shared axis so the decay shapes "
             f"can be compared directly. Where the lines separate matters more "
             f"than the gap itself: a gap that opens at age 1 and stays flat is an "
             f"onboarding difference, one that keeps widening is an engagement "
             f"difference.",
        subdir=subdir, slug=curve_slug,
    )

    states = [(label, metrics.lifecycle_states(cut)) for label, cut in cuts]
    run.section(
        f"Quick Ratio by {seg_name}",
        fig=plots.quick_ratio(states, grain=grain),
        data=_by_segment(states),
        note=f"{sub}\n\n(New + Resurrected) / Churned, one line per segment "
             f"against the shared 1.0 break-even line. A segment below 1 is "
             f"shrinking even while the overall base grows.",
        subdir=subdir, slug=ratio_slug,
    )
    return run


def run_report(df, dataset, config=None, out_dir="output", source=None,
               segment_by=None, grain=None, active_event=None,
               segment_cols=None, count_col="event_count", week_start=None,
               run_id=None, refresh=False):
    """Run every view and write the folder. Returns the run directory.

    Pass either a ``config`` dict (from ``retentionkit.config``) or the
    individual keyword arguments. With ``segment_by`` set, the overall cut is
    written first and then one set of figures per segment value — overall before
    segments, because a segment difference only means something against the
    overall shape.

    The retention curve and Quick Ratio are the exception: a segmented run draws
    each of them **once**, with one line per segment on a shared axis, rather than
    one chart per value. Those two are the views worth comparing directly.

    A list ``segment_by`` **crosses** the columns rather than cutting by each in
    turn: ``["platform", "channel"]`` yields one set of figures per
    *platform × channel* combination. For two independent cuts, call twice with
    the same ``run_id``.

    Parameters
    ----------
    run_id : reuse an existing run folder instead of opening a new timestamped
        one. Cuts already in that run are skipped and the new ones appended, so
        adding a segment cut after the fact costs only that cut's figures. This
        is how several independent cuts share one run.
    refresh : redraw cuts that are already present rather than skipping them.
        This is what you want after changing ``plots`` or ``metrics``.
    """
    cfg = dict(config or {})
    grain = grain or cfg.get("grain", "week")
    active_event = active_event if active_event is not None else cfg.get("core_action")
    segment_cols = segment_cols if segment_cols is not None else (
        cfg.get("segment_cols") or [])
    count_col = cfg.get("count_col", count_col)
    week_start = week_start or cfg.get("week_start")

    build = {"active_event": active_event, "segment_cols": segment_cols,
             "count_col": count_col}
    if week_start:
        build["week_start"] = week_start

    quality = quality_report(df, grain=grain, active_event=active_event,
                             **({"week_start": week_start} if week_start else {}))
    am = ActivityMatrix.build(df, grain=grain, **build)
    daily_am = ActivityMatrix.build(df, grain="day", **build)

    run = Run(dataset, out_dir=out_dir, run_id=run_id, source=source, header_lines=[
        f"- **Active =** {active_event or 'any logged event'} · "
        f"**period:** {grain}",
        f"- **Panel:** {am.n_users:,} users × {am.n_periods} {grain}s, "
        f"{am.density:.1%} dense (every other cell is a true zero)",
    ])
    if run.resumed:
        print(f"↻  resuming {run.dir}")
    skip = run.resumed and not refresh

    run.section("Data quality", note=format_quality_report(quality))

    add_views(run, am, daily_am=daily_am, subdir="overall", skip_existing=skip)

    if segment_by:
        cols = [segment_by] if isinstance(segment_by, str) else list(segment_by)
        subdir = "_x_".join(cols)
        # One mask, applied to both panels: they were built from the same log and
        # therefore share a user axis, so a segment cut stays a row slice.
        masks = list(am.segment_masks(cols))
        # The cross-segment comparison first — it frames the per-segment detail
        # the same way the overall cut frames the segments.
        add_overlays(run, am, masks, subdir=subdir, skip_existing=skip)
        for label, mask in masks:
            add_views(run, am.where(mask), daily_am=daily_am.where(mask),
                      label=label, subdir=subdir, skip_existing=skip,
                      overlaid=True)

    return run.save()
