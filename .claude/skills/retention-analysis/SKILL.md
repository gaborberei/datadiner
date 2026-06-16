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

1. If the dataset ships a `dataset_brief.yaml`, run the **data-quality-gate** skill
   first and let it pass before computing anything.
2. Confirm the **grain**. If the data is weekly-grain, daily analyses are
   off-limits — never build a daily grid or daily retention.

## Loading the data

The `datadiner` package lives at the repo root, so run from the repo root (or add
it to the path). Load the CSV **once per session** (~82 MB / 3.5M rows for the
chess dataset) and reuse `df`:

```python
from datadiner.io import load_events
from datadiner.retention import (
    retention_rate_heatmap, retention_counts_heatmap,
    churn_rate_heatmap, churn_counts_heatmap, vs_average_heatmap,
    retention_curve, usage_frequency, lifecycle_states,
)

df = load_events("Retention course/1. Retention analysis/chess_data_synthetic.csv")
```

`load_events` parses dates and validates the `date` + `user_id` columns. Pass
`date_col=` / `user_col=` if a dataset names them differently. Heatmaps take
`granularity='weekly'` or `'monthly'`. All chart functions accept a `save=` /
`save_prefix=` path (default to inline; only save when asked).

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
  cause, until it's been drilled into. (The chess dataset has planted shocks — a
  sharp diagonal in `vs_average_heatmap` or `churn_rate_heatmap` is the tell.)
- **Offer the next view:** e.g. "want the churn view to see exactly where the drop
  is?"
