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
    retention_curve, usage_frequency, lifecycle_states,
)

df = load_events("datasets/<name>/<file>.csv")   # e.g. datasets/notion/notion_causal_events.csv
```

`load_events` parses dates, validates the `date` + `user_id` columns, and keeps
any extra columns (event_type, segments) so `segment_by=` works. Pass
`date_col=` / `user_col=` if a dataset names them differently (e.g.
`date_col="event_time"`), and `dtype={...}` to honor a brief's dtype hint (e.g.
`{'app_version': str}`). Heatmaps take `granularity='weekly'` or `'monthly'`. Every
view also takes `active_event=` (count only that event as "active"; see Core action)
and `save=` / `save_prefix=` (default inline; only save when asked).

## Default workflow — two phases

Always read the **overall** picture before any segment. Don't open with a segmented
chart — segments only mean something against the whole.

**Phase 1 — Overall (un-segmented):**
1. **`retention_curve(df)`** — the overall decay shape: how fast do we lose users?
2. **`lifecycle_states(df)`** — weekly New / Retained / Resurrected / At-Risk /
   Churned plus the Quick Ratio (>1 growing net, <1 shrinking).
3. **Cohort analysis** — the heatmaps: lead with `retention_rate_heatmap(df)`, then
   `churn_rate_heatmap` / `vs_average_heatmap` to localize where a cohort broke.

**Phase 2 — Segment drill-down (user's choice):** once the overall picture is read,
**ask the user which segment column(s) or combination** to inspect (offer the brief's
`analysis.segment_cols`), then re-run the relevant view(s) with `segment_by=`. This is
how you find *which* segment owns a shift seen in Phase 1.

## Interactive guided exercise

This skill *is* the exercise — drive the two phases one step at a time, don't dump
every chart at once:

- **Step 0:** run the **data-quality-gate** and report PASS/FAIL before any chart.
- **Phase 1:** for each overall view (curve → lifecycle → cohort): run **one** view,
  give the plain-English read (cite file + columns + date range), then **pause** for
  the user's interpretation before advancing. Offer the natural next view each time.
- **Phase 2:** ask **which segment(s) or combination** they want to drill into, then
  re-run the relevant view segmented and read it against the overall.

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
- **Row read vs diagonal read:** a **row** is one cohort over its lifetime (does
  this cohort retain?). A **diagonal** is one calendar period across all cohorts
  (what happened to everyone in, say, week 12 of 2024 — the signature of a shock).
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
