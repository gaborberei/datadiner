---
name: retention-analysis
description: Interactive retention-analysis companion for any date+user_id activity log. Use when the user asks about retention, churn, cohorts, lifecycle states, engagement frequency, or whether they are growing/shrinking — to pick the right view, run it on the data, and explain how to read it. Works on any event log with a `date` and `user_id` column.
---

# Retention analysis

## Purpose

Answer a retention question with the **right view + a plain-English read** — not a
fixed report. This skill is a router and reading guide on top of the existing
`datadiner.py` helper library. Do not reimplement cohort/heatmap/lifecycle logic;
call the functions below.

## When to use

Any question about keeping users over time on a `date` + `user_id` activity log:
retention, churn, cohorts, lifecycle (new/retained/resurrected/at-risk/churned),
engagement frequency, or "are we growing net?". One-at-a-time, conversational —
answer the question asked, then offer the natural next view.

## Prerequisites

1. **No `dataset_brief.yaml` next to the CSV?** Run the **dataset-onboarding** skill
   first — it profiles the file, asks the user the non-inferable facts, and writes the
   brief. (The shipped `datasets/` all have one.)
2. Run the **data-quality-gate** skill and let it pass before computing anything.
3. Confirm the **grain** from the brief. If the data is weekly-grain, daily
   analyses are off-limits — never build a daily grid or daily retention.
4. Note the brief's `analysis.segment_cols` (cut with `segment_by=`) and its
   `analysis.core_action` (pass as `active_event=` for core-action retention).

## Loading the data

The `datadiner` package lives at the repo root, so run from the repo root (or add
it to the path). Each dataset lives in `datasets/<name>/`. Load the CSV **once per
session** (the activity logs are large) and reuse `df`:

```python
from datadiner.io import load_events
from datadiner.retention import (
    retention_rate_heatmap, retention_counts_heatmap,
    churn_rate_heatmap, churn_counts_heatmap, vs_average_heatmap,
    retention_curve, usage_frequency, lifecycle_states, cohort_matrix,
)

df = load_events("datasets/<name>/<file>.csv")   # e.g. datasets/notion/notion_causal_events.csv
```

`load_events` parses dates, validates the `date` + `user_id` columns, and keeps
any extra columns (event_type, segments) so `segment_by=` works. Pass
`date_col=` / `user_col=` if a dataset names them differently (e.g.
`date_col="event_time"`), and `dtype={...}` to honor a brief's dtype hint (e.g.
`{'app_version': str}`). Heatmaps take `granularity='weekly'` or `'monthly'`. Every
view also takes `active_event=` (count only that event as "active"; see Core action)
and `save=` / `save_prefix=` (per-view PNG saving; the guided exercise instead
bundles a full run folder by default via `AnalysisReport` — see "Saving a run").

## Default workflow — two phases

Always read the **overall** picture before any segment. Don't open with a segmented
chart — segments only mean something against the whole.

**Phase 1 — Overall (un-segmented):**
1. **`usage_frequency(df)`** — the engagement-cadence histogram (avg active days
   per month per user): is this a daily, weekly, or monthly product? Use it to
   frame the core metric *before* charting retention.
2. **`retention_curve(df)`** — the overall decay shape: how fast do we lose users?
3. **`lifecycle_states(df)`** — weekly New / Retained / Resurrected / At-Risk /
   Churned plus the Quick Ratio (>1 growing net, <1 shrinking).
4. **Cohort analysis** — the heatmaps. In the **guided exercise**, emit **all five**
   (rate, counts, churn-rate, churn-counts, vs-average) in one call via
   `cohort_sections(report, df, active_event=…)` — never hand-pick a subset — then
   read whichever localize the signal (typically `retention_rate` + `churn_rate` /
   `vs_average`). For an **ad-hoc single question** (router mode), it's fine to run
   just the one heatmap the question asks for.

**Phase 2 — Segment drill-down (user's choice):** once the overall picture is read,
**ask the user which segment column(s) or combination** to inspect (offer the brief's
`analysis.segment_cols`), then re-run the relevant view(s) with `segment_by=`. This is
how you find *which* segment owns a shift seen in Phase 1.

## Interactive guided exercise

This skill *is* the exercise — drive the two phases one step at a time, don't dump
every chart at once:

- **Step 0:** run the **data-quality-gate** and report PASS/FAIL before any chart.
- **Phase 1:** for each overall view (frequency → curve → lifecycle → cohort): run
  **one** view, give the plain-English read (cite file + columns + date range), then
  **pause** for the user's interpretation before advancing. Offer the next view each
  time. As each chart renders, **announce the figure** with the standard block
  (`📊 <View name> — figure generated and saved to:` then the path — see "Saving a
  run"). (Frequency comes first because it sets what "active" should mean.) The cohort
  step produces all five heatmaps (`cohort_sections`). **Close Phase 1** with
  `ensure_phase1(report, df, …)` + `report.assert_phase1_complete()` before the final
  `save()` so the run can't be silently incomplete (see "Saving a run").
- **Phase 2:** ask **which segment(s) or combination** they want to drill into, then
  re-run the relevant view segmented and read it against the overall.

**Generate the run folder by default, incrementally as you go.** Open an
`AnalysisReport` at Step 0 / first view and add one `.section()` per step right
after you give its read — so the saved `report.md` carries the *same* reads the
user saw, in order (see "Saving a run" for the calls). Don't wait until the end
and don't make the user ask. The only time you skip it is when the user opts out
("don't save", "just a quick look") — then stay inline. This auto-save is for the
**direct analysis exercise only**; the Socratic `retention-tutor` saves lesson
**figures only** to `output/<dataset>/retention_lesson/`, never the answer-bearing
`report.md` (which would hand the learner the answers).

## Segmentation

Every view takes `segment_by=` — a single column **or a list of columns** (cross-tab
of the combination). Use columns from the brief's `analysis.segment_cols`:

```python
retention_curve(df, segment_by='segment')                 # overlays one line per segment
retention_curve(df, segment_by=['country', 'platform'])   # one line per combination
res = retention_rate_heatmap(df, segment_by='platform')   # list of (label, fig, ax)
res = lifecycle_states(df, segment_by=['segment','platform'])  # list of (label, states_df, figs)
```

`retention_curve` overlays the groups on one axes (best for comparison); the heatmaps
and `lifecycle_states` render **one figure per group** and return a **list** instead
of a single `fig, ax`. Combinations multiply fast — past ~30 groups it warns; steer the
user to a couple of columns or specific values.

## Saving a run (output folder)

**A run folder is generated by default** as you work through the views — the user
doesn't have to ask. (Charts still render inline too; saving is additive.) Skip it
only when the user opts out ("don't save", "just a quick look"). A run is bundled
into `output/<dataset>/<YYYY-MM-DD-HHMM>/`: a `report.md` (provenance + one section
per view with the read, the embedded chart, and a link to the data) alongside
`charts/` PNGs and `data/` CSVs. The folder is git-ignored.

📊 **Announce every figure as it renders.** Post a standard block — `📊 <View name> —
figure generated and saved to:` on one line, the PNG path on the next — so the user
can open the chart alongside the read. Point at the run folder's `charts/` PNG so the
announced path matches where `AnalysisReport` actually writes:

```
📊 Usage-frequency histogram — figure generated and saved to:
output/<dataset>/<YYYY-MM-DD-HHMM>/charts/usage_frequency.png
```

**Incremental — the default path during the guided exercise** (so the report carries
the same reads you gave the user, one section per step): open the report once, then
add a section right after each view's read, and `save()` after each step so the
folder is always current.

```python
from datadiner.report import AnalysisReport, cohort_sections, ensure_phase1

report = AnalysisReport("notion", df=df, source="datasets/notion/notion_causal_events.csv")
fig, ax, avg = usage_frequency(df)
report.section("Usage frequency", fig=fig, data=avg, note="<your plain-English read>")
# the cohort step emits ALL FIVE views at once (use the canonical titles):
cohort_sections(report, df, active_event='page_created',
                notes={"cohort_retention_rate": "<your read>"})  # optional per-view reads
report.save()   # writes report.md, returns the run dir
```

`section()` takes whatever a view returns — a single `fig`, a `(fig1, fig2)` pair, a
`{name: fig}` dict, or the `list[(label, …)]` a segmented view returns — plus a
DataFrame (or per-segment list) for the CSV. Use `cohort_matrix(df, kind=…)` to get a
heatmap's numbers as data (the heatmaps return only `fig, ax`).

**Close Phase 1 with the completeness guard.** Before the final `save()`, run the two
helpers so no canonical view is silently missing — `ensure_phase1` generates any of
the eight Phase-1 views you didn't hand-build (idempotent; won't duplicate or clobber
your reads), and `assert_phase1_complete` raises if any is still absent:

```python
ensure_phase1(report, df, active_event='page_created')  # fills the gaps
report.assert_phase1_complete()                          # guard: raises IncompleteRunError if not
report.save()
```

Use the **canonical section titles** for the eight Phase-1 views ("Usage frequency",
"Retention curve", "Lifecycle states", "Cohort retention rate/counts", "Cohort
churn rate/counts", "Cohort vs average") so slugs match and `ensure_phase1` skips the
ones you already added instead of adding a near-duplicate.

**One-shot** — build the whole Phase-1 overall folder in workflow order:

```python
from datadiner.report import overall_report
overall_report(df, dataset="notion",
               source="datasets/notion/notion_causal_events.csv",
               active_event="page_created")
```

## Core action — what counts as "active"

By default a user is "active" in a period if they have **any** row. When the brief
declares `analysis.core_action` (e.g. notion `page_created`), pass
`active_event='<core_action>'` to count only that event as active — so retention
reflects meaningful use, not an incidental `page_view`:

```python
retention_curve(df, active_event='page_created')
retention_rate_heatmap(df, segment_by='segment', active_event='page_created')
```

Presence-only logs (just `date` + `user_id`, no `event_type`) have no core action —
leave `active_event` unset. `usage_frequency` always counts any active row (it's the
exploratory view used to *pick* the metric).

## Question → view router

| The user is asking… | Call | Returns |
|---|---|---|
| "show / measure retention", "are we keeping users" (as %) | `retention_rate_heatmap(df, granularity)` | fig, ax |
| same, but in absolute user counts | `retention_counts_heatmap(df, granularity)` | fig, ax |
| "how fast do we lose users", "what's the decay shape" | `retention_curve(df, max_periods=40)` | fig, ax |
| "how many / what % are we churning" | `churn_counts_heatmap(df, g)` / `churn_rate_heatmap(df, g)` | fig, ax |
| "which cohorts are better/worse", "did a cohort break" | `vs_average_heatmap(df, granularity)` | fig, ax |
| "how often do users engage", "daily vs weekly product" | `usage_frequency(df)` | fig, ax, per-user df |
| "growth quality", "new vs churned", "are we growing net" | `lifecycle_states(df)` | states_df, (fig1, fig2) |
| "what's our core metric / is retention defined right" | start with `usage_frequency(df)` to find the natural cadence, then frame the metric **before** charting | — |
| "...broken down by segment / channel / platform / version" | add `segment_by='<col>'` to any call above | curve: fig, ax · others: list of per-value results |

## How to read each view

- **Counts vs rates:** counts heatmaps show absolute users (size of the problem);
  rate heatmaps show % still active (quality of retention). Lead with rates unless
  asked about absolute volume.
- **Three lenses — read the heatmap by direction:**
  - **Horizontal (row) = cohort-specific effects.** One cohort over its lifetime —
    does *this* intake retain? Reflects acquisition campaigns or market expansion. A
    *small* cohort with *strong* retention = low volume but high quality (e.g. reduced
    spend, better-fit users); a large-but-weak row is the opposite.
  - **Diagonal = simultaneous, all-cohort events.** One calendar period across every
    cohort regardless of age — the signature of a shock that hits everyone at once
    (feature launch, bug, an outage-style drop).
  - **Vertical (column) = tenure milestones.** One age across all cohorts — the
    "survival" moments common in trial/subscription products: drop-off after a 30-day
    trial ends, churn spikes at annual renewal.
  - `cohort_patterns(df, active_event=...)` surfaces the strongest signal of each
    lens (where it is, magnitude, how many cohorts) to point you at what to drill —
    it points, it doesn't conclude a cause.
- **Coloring is column-normalized:** color compares cells *within the same
  period-since-signup*, not across columns. A green cell means "good *for that
  age*", not "high absolute retention".
- **Grey "Users" column:** the leftmost column is each cohort's starting size —
  read it before trusting a rate (a great rate on 12 users is noise).
- **`vs_average_heatmap`:** diverging — positive = this cohort beat the average for
  its age, negative = lagged. Best for spotting which cohort/period broke.
- **`lifecycle_states` Quick Ratio** = (New + Resurrected) / Churned. **> 1 = growing
  net, < 1 = shrinking.** The stacked bars show the composition behind it.

## Granularity

Default to **weekly** for a few months to ~1 year of data. Use **monthly** for long
horizons or when weekly cohorts get too small to read. Never pick daily on
weekly-grain data.

## Interaction rules

- If the metric is ambiguous, **define/confirm it before charting** (active = at
  least one row that period? which window?).
- **Cite the source** every time: CSV/table, columns used, and the date range.
- **Explain the read in business terms**, not just "here's a chart" — what it says
  about the product.
- **Flag, don't conclude:** call an anomaly "worth investigating", not a proven
  cause, until it's been drilled into. A sharp **diagonal** in `vs_average_heatmap`
  or `churn_rate_heatmap` is the tell of a calendar-period shock; segment the view
  (`segment_by=`) to find which segment owns it.
- **Offer the next view:** e.g. "want the churn view to see exactly where the drop
  is?"
