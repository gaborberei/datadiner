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

1. Run the **data-quality-gate** skill first and let it pass before computing
   anything — every dataset under `datasets/` ships a `dataset_brief.yaml`.
2. Confirm the **grain** from the brief. If the data is weekly-grain, daily
   analyses are off-limits — never build a daily grid or daily retention.
3. Note the brief's `analysis.segment_cols` — those are the columns you can pass
   to `segment_by=` to cut any view.

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
`{'app_version': str}`). Heatmaps take `granularity='weekly'` or `'monthly'`. All
chart functions accept `save=` / `save_prefix=` (default inline; only save when asked).

## Default workflow

For a fresh dataset, run the views in this order — overall shape first, then
composition, then the cohort grid:

1. **`retention_curve(df)`** — the overall decay shape: how fast do we lose users?
2. **`lifecycle_states(df)`** — weekly New / Retained / Resurrected / At-Risk /
   Churned plus the Quick Ratio (>1 growing net, <1 shrinking).
3. **Cohort analysis** — the heatmaps: lead with `retention_rate_heatmap(df)`, then
   `churn_rate_heatmap` / `vs_average_heatmap` to localize where a cohort broke.

## Interactive guided exercise

This skill *is* the exercise — drive the workflow one step at a time, don't dump
every chart at once:

- **Step 0:** run the **data-quality-gate** and report PASS/FAIL before any chart.
- Then, for each step (curve → lifecycle → cohort): run **one** view, give the
  plain-English read (cite file + columns + date range), then **pause** — ask the
  user for their interpretation and whether to cut it by a segment — and only
  advance on their go-ahead. Offer the natural next view each time.

## Segmentation

Every view takes `segment_by='<column>'` (use a column from the brief's
`analysis.segment_cols`):

```python
retention_curve(df, segment_by='segment')        # overlays one line per segment
res = retention_rate_heatmap(df, segment_by='platform')  # list of (value, fig, ax)
res = lifecycle_states(df, segment_by='acquisition_channel')  # list of (value, states_df, figs)
```

`retention_curve` overlays the segments on one axes (best for comparison); the
heatmaps and `lifecycle_states` render **one figure per segment value** and return
a **list** instead of a single `fig, ax`. Use segmentation to isolate *which*
segment is driving a shift you saw in the overall view.

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
