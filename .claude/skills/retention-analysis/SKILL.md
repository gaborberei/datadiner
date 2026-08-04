---
name: retention-analysis
description: Interactive retention-analysis companion for any date+user_id activity log. Use when the user asks about retention, churn, cohorts, lifecycle states, engagement frequency, or whether they are growing/shrinking — to pick the right view, run it on the data, and explain how to read it. Works on any event log with a `date` and `user_id` column.
---

# Retention analysis

## Purpose

Answer a retention question with the **right view + a plain-English read** — not a
fixed report. This skill is a router and reading guide on top of the `retentionkit`
package. Do not reimplement cohort/heatmap/lifecycle logic; call the functions below.

## When to use

Any question about keeping users over time on a `date` + `user_id` activity log:
retention, churn, cohorts, lifecycle (new/retained/resurrected/at-risk/churned),
engagement frequency, or "are we growing net?". One-at-a-time, conversational —
answer the question asked, then offer the natural next view.

## Prerequisites

1. **No `analysis.yaml` next to the CSV?** (`config.load_config()` returns `None`.)
   Run the **dataset-onboarding** skill first — it infers the column roles, asks the
   four things it can't know, and writes the file. The shipped `datasets/` all have one.
2. Run the **data-quality-gate** skill first and lead with what it says — the panel
   density and the natural frequency, which is what should pick the grain.
3. Note the config's `segment_cols` (cut with `segment_by=`) and its `core_action`
   (passed as `active_event=` for core-action retention).

## Loading the data

Run from the repo root. Each dataset lives in `datasets/<name>/`. Load the CSV **once
per session** — the activity logs are large — and reuse `df`:

```python
from retentionkit import load_activity, ActivityMatrix, metrics, plots
from retentionkit.config import load_config

cfg = load_config("datasets/lesson_1_chess/activity.csv")
df  = load_activity(cfg["file"])
```

`load_activity` parses dates and picks memory-frugal dtypes (categories for
low-cardinality strings, unsigned ints for counts), keeping every other column so
`segment_by=` works. Pass `date_col=` / `user_col=` if a dataset names them
differently — they're renamed to the canonical `date` / `user_id` — plus `dtype=` to
override an inference and `usecols=` to read a subset.

Then build the panel once and derive everything from it:

```python
am = ActivityMatrix.build(df, grain=cfg["grain"], active_event=cfg["core_action"],
                          segment_cols=cfg["segment_cols"], week_start=cfg["week_start"])
daily_am = ActivityMatrix.build(df, grain="day", active_event=cfg["core_action"])
```

`grain` is `'week'` or `'month'` — **never `'day'` for retention**; the daily panel
exists only to feed `usage_frequency`. `config.build_kwargs(cfg)` packages the build
arguments if you'd rather not spell them out.

## Default workflow — two phases

Always read the **overall** picture before any segment. Don't open with a segmented
chart — segments only mean something against the whole.

**Phase 1 — Overall (un-segmented):**
1. **Usage frequency** — the engagement-cadence histogram (avg active days per month
   per user): is this a daily, weekly, or monthly product? Read it *before* charting
   retention, because it frames what "active" should mean.
2. **Retention curve** — the overall decay shape: how fast do we lose users, and
   where does it flatten?
3. **Lifecycle states + Quick Ratio** — New / Retained / Resurrected / At-Risk /
   Churned, and whether the base grows on net (>1) or shrinks (<1).
4. **Cohort heatmaps** — all five (`retention_rate`, `retention_counts`,
   `churn_rate`, `churn_counts`, `vs_average`), then read whichever localize the
   signal (typically `retention_rate` + `churn_rate` / `vs_average`). For an ad-hoc
   single question, it's fine to run just the one the question asks for.

**Phase 2 — Segment drill-down (user's choice):** once the overall picture is read,
**ask which segment column(s) or combination** to inspect (offer the config's
`segment_cols`), then re-run with `segment_by=`. This is how you find *which* segment
owns a shift seen in Phase 1.

Drive the phases **one step at a time** — don't dump every chart at once. For each
view: run it, give the plain-English read (cite file + columns + date range),
announce the figure, then **pause** for the user's interpretation before advancing.
Offer the next view each time.

## Generating a run folder

**`run_report` is the default path** — it runs every view and writes the folder in
one call, and the user doesn't have to ask for it:

```python
from retentionkit.report import run_report

run_dir = run_report(df, dataset="lesson_1_chess", config=cfg,
                     source="datasets/lesson_1_chess/activity.csv")
```

That writes `output/<dataset>/<YYYY-MM-DD-HHMM>/` — a `report.md` (provenance, the
data-quality read, one section per view) alongside `charts/` PNGs and `data/` CSVs,
every figure with a CSV twin so any number is checkable. Un-segmented figures land in
`charts/overall/`, segmented ones in `charts/<segment_col>/` (combinations in
`charts/<col>_x_<col>/`). The folder is git-ignored.

**Runs are resumable — one analysis is one run.** Pass `run_id=` to append a later
cut to an existing folder instead of minting a second one; cuts already present are
skipped, so adding a segment costs only that segment's figures. Pass `refresh=True`
to redraw cuts that are already there (what you want after changing `plots` or
`metrics`).

```python
run_report(df, dataset="lesson_1_chess", config=cfg, segment_by="platform",
           run_id=run_dir.name)                     # Phase 2, same folder
```

A **list** `segment_by` *crosses* the columns — `["platform", "acquisition_channel"]`
gives one set of figures per platform × channel combination. For two **independent**
cuts, call twice with the same `run_id`.

Skip the run folder only when the user opts out ("don't save", "just a quick look") —
then work inline with the calls in the router below.

📊 **Announce every figure as it renders** — a standard block so the user can open the
chart alongside the read:

```
📊 Usage-frequency histogram — figure generated and saved to:
output/lesson_1_chess/<YYYY-MM-DD-HHMM>/charts/overall/usage_frequency.png
```

## Working a single view inline

`metrics` returns DataFrames and draws nothing; `plots` renders them. That split is
why every figure's data is exportable — pair them:

```python
table = metrics.cohort_table(am, kind="retention_rate")   # cohorts x age
fig   = plots.cohort_heatmap(table, kind="retention_rate", grain=am.grain)

curve = metrics.retention_curve(am)            # weighted=True pools cohorts instead
fig   = plots.retention_curve(curve, grain=am.grain)

states = metrics.lifecycle_states(am)          # one frame -> two figures
fig    = plots.lifecycle_bars(states, grain=am.grain)
fig    = plots.quick_ratio(states, grain=am.grain)

usage = metrics.usage_frequency(daily_am)      # needs the DAILY panel
fig   = plots.usage_frequency(usage)
```

The five cohort heatmaps are **one function with `kind=`**, not five functions —
they're five transforms of a single computation.

## Segmentation

Segmenting is a **row mask on the panel, not a rebuild**: a user's cohort is their own
first active period, so it survives subsetting and every cut stays on the same
calendar axis. Use columns from the config's `segment_cols`:

```python
for label, mask in am.segment_masks("platform"):      # ('platform=mobile', mask)
    seg = am.where(mask)                              # same mask works on daily_am
    curve = metrics.retention_curve(seg)

mobile = am.where(am.attrs["platform"] == "mobile")   # or mask it directly
```

`am.segments(cols)` hands back `(label, ActivityMatrix)` pairs if you don't need the
mask itself. `plots.retention_curve()` and `plots.quick_ratio()` take **either** one
frame **or** a list of `(label, frame)` and overlay a line per segment — those two are
the views worth comparing on a shared axis. The heatmaps, the histogram and the
lifecycle bars render one figure per segment instead. Combinations multiply fast;
past a couple of columns, steer the user to specific values.

## Core action — what counts as "active"

By default a user is "active" in a period if they have **any** row. When the config
declares a `core_action` (e.g. `game_played`), pass `active_event=` so retention
reflects meaningful use rather than an incidental page view. **Say which definition is
in force** — retention means "did the thing", not "showed up".

Presence-only logs (just `date` + `user_id`, no `event_type`) have no core action;
leave `active_event` unset. `usage_frequency` is the exploratory view used to *pick*
the metric, so it doesn't presuppose one — but it reads whatever panel you hand it, so
build `daily_am` with `active_event=` if you want the core action's cadence alone.

`week_start` is a decision, not a default to accept: `MON` unless the source system's
weeks close elsewhere. Note that pandas' `W-XXX` aliases name the day a week *ends*;
this package's parameter names the start.

## Question → view router

| The user is asking… | Call |
|---|---|
| "show / measure retention", "are we keeping users" (as %) | `cohort_table(am, kind="retention_rate")` → `cohort_heatmap` |
| same, but in absolute user counts | `cohort_table(am, kind="retention_counts")` |
| "how fast do we lose users", "what's the decay shape" | `retention_curve(am)` → `plots.retention_curve` |
| "how many / what % are we churning" | `cohort_table(am, kind="churn_counts" / "churn_rate")` |
| "which cohorts are better/worse", "did a cohort break" | `cohort_table(am, kind="vs_average")` |
| "how often do users engage", "daily vs weekly product" | `usage_frequency(daily_am)` → `plots.usage_frequency` |
| "growth quality", "new vs churned", "are we growing net" | `lifecycle_states(am)` → `lifecycle_bars` + `quick_ratio` |
| "what's our core metric / is retention defined right" | start with `usage_frequency` to find the natural cadence, then frame the metric **before** charting |
| "…broken down by segment / channel / platform" | `am.segment_masks(col)` + `am.where(mask)`, or `segment_by=` on `run_report` |
| "where should I even look?" | `cohort_patterns(am)` — points at the strongest signal per lens |

Every `metrics` function returns a DataFrame; the matching `plots` function returns
the figure.

## How to read each view

- **Counts vs rates:** counts show absolute users (size of the problem); rates show %
  still active (quality of retention). Lead with rates unless asked about volume.
- **Three lenses — read the heatmap by direction:**
  - **Horizontal (row) = cohort-specific effects.** One cohort over its lifetime —
    does *this* intake retain? Reflects acquisition campaigns or market expansion. A
    *small* cohort with *strong* retention = low volume but high quality; a
    large-but-weak row is the opposite.
  - **Diagonal = simultaneous, all-cohort events.** One calendar period across every
    cohort regardless of age — the signature of a shock that hits everyone at once
    (feature launch, bug, an outage-style drop).
  - **Vertical (column) = tenure milestones.** One age across all cohorts — the
    "survival" moments common in trial/subscription products: drop-off after a 30-day
    trial ends, churn spikes at annual renewal.
  - `cohort_patterns(am)` surfaces the strongest signal of each lens (where it is,
    magnitude, how many cohorts) to point you at what to drill — it points, it doesn't
    conclude a cause.
- **Coloring is column-normalized:** color compares cells *within the same age
  column*, not across columns. Green means "good *for that age*", not "high absolute
  retention".
- **The `Signups` column** is each cohort's starting size — read it before trusting a
  rate (a great rate on 12 users is noise). It's on the same ramp as the rest but
  scaled only against its own values, so volume reads at a glance; it never encodes
  retention.
- **`vs_average`:** positive = this cohort beat the average for its age, negative =
  lagged. Best for spotting which cohort/period broke.
- **Zero vs NaN:** `0` means the user was around and did nothing; `NaN` means the
  cohort hasn't lived that long yet (right-censoring). Never read the second as the
  first — the young cohorts' tails are empty, not dead.
- **Quick Ratio** = (New + Resurrected) / Churned. **> 1 = growing net, < 1 =
  shrinking.** The stacked bars show the composition behind it.
- **One churn definition:** At-Risk after one missed period, Churned after a second.
  Churn is not final — a churned user who returns is Resurrected.
- **The curve is unweighted:** every cohort counts equally, so one acquisition spike
  can't define the whole curve. Its `cohorts` column says how many cohorts are old
  enough to contribute at each age — the tail rests on fewer than the head.
  `weighted=True` pools instead.

## Grain

Default to **weekly** for a few months to ~1 year of data; **monthly** for long
horizons or when weekly cohorts get too small to read. Retention is weekly or monthly
whatever the input grain — **never daily**; daily retention on a daily log measures
noise. Let the **natural frequency** from the quality report pick it: a period shorter
than the rhythm manufactures churn, a longer one hides it.

## Interaction rules

- If the metric is ambiguous, **define/confirm it before charting** (active = at least
  one row that period? which event?).
- **Cite the source** every time: CSV, columns used, and the date range.
- **Explain the read in business terms**, not just "here's a chart" — what it says
  about the product.
- **Flag, don't conclude:** call an anomaly "worth investigating", not a proven cause,
  until it's been drilled into. A sharp **diagonal** in `vs_average` or `churn_rate`
  is the tell of a calendar-period shock; segment the view to find which segment owns
  it.
- **Offer the next view:** e.g. "want the churn view to see exactly where the drop is?"
