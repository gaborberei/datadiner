# CLAUDE.md — retentionkit

You are a **product-retention analyst**. Explain what a number says and why it
matters, not just how it was computed. Cite the source on every finding (file,
columns, date range). Flag anomalies as "worth investigating", never as a proven
cause.

## What this repo is

A minimal analyst for **daily-aggregated activity logs**. Point it at a CSV,
answer four questions, get the figures.

Expected input — one row per user per active day:

```
date, user_id, event_type, event_count, <segment columns...>
```

Only `date` and `user_id` are required. The log is **active-periods-only**: a row
exists only where someone did something, and absence is implicit.

## The one idea

Load the log once into a **sparse users × periods panel**
(`ActivityMatrix`), then derive every figure from it. Retention is computed
**weekly or monthly** — never daily, whatever the input grain.

Three properties of that panel matter more than anything else in the codebase:

1. **The period axis is complete.** Every calendar week/month between the first
   and last activity gets a column, including ones where nobody was active.
   Building the axis from the *observed* periods would delete an empty week and
   shift every later age left by one, dating the whole heatmap wrong.
2. **Zero-fill is free.** Over that complete grid, an unstored cell *is* a zero.
   The dense panel the retention math wants never has to be materialized.
3. **Zero ≠ unobservable.** A cell is `0` when the user was around and did
   nothing; it is `NaN` when the cohort hasn't lived that long yet
   (right-censoring). Never let the second become the first.

Segmenting is a **row mask on the panel**, not a rebuild: a user's cohort is
their own first active period, so it survives subsetting untouched.

## Repo map

- `retentionkit/` — the package. Shared logic lives here; skills and notebooks
  *call* it, never inline analysis.
  - `io.py` — `load_activity()` (memory-frugal CSV load), `quality_report()`
    (leads with sparsity), `natural_frequency()` (the cadence users keep),
    `format_quality_report()`.
  - `matrix.py` — `ActivityMatrix`: the sparse panel, cohorts, `where()` /
    `segment_masks()` / `segments()`, and `period_axis()`.
  - `metrics.py` — numbers only, DataFrames out: `cohort_table(kind=...)`,
    `retention_curve()`, `lifecycle_states()`, `usage_frequency()`,
    `cohort_patterns()` (a reading aid, not a conclusion).
  - `plots.py` — rendering only, one function per figure. `retention_curve()`
    and `quick_ratio()` take either one frame or a list of `(label, frame)` and
    overlay a line per segment. The figures are the
    **DataDiner course figures**, definition for definition: `RdYlGn` cohort
    heatmaps normalized *within each age column* (no colorbar, cells annotated),
    and seaborn `whitegrid` + the `muted` palette everywhere else, assigned by
    fixed slot. **One deliberate divergence:** the `Signups` column is on the same
    ramp rather than flat grey, scaled only against its own values, so signup
    volume reads at a glance. It never encodes retention.
  - `report.py` — `run_report()` / `Run` → an output folder. Runs are
    **resumable**: `run.json` records what a run contains, so `run_id=` appends a
    later cut to an existing folder instead of minting a second one. One analysis
    is one run. A *list* `segment_by` crosses the columns (platform × channel);
    independent cuts are separate calls sharing a `run_id`.
  - `config.py` — `infer_config()` guesses column roles; `load_config()` /
    `save_config()` read and write `analysis.yaml`.
- `datasets/<name>/` — an `activity.csv` (git-ignored) plus its `analysis.yaml`.
- `output/<dataset>/<run>/` — generated, git-ignored: `report.md`, `charts/`
  (`overall/` and `<segment_col>/`), `data/`.
- `.claude/skills/` — three skills, all of which *call* the package:
  `retention-analysis` (the workflow), `data-quality-gate` (read the log's shape
  first), `dataset-onboarding` (write an `analysis.yaml` for a CSV without one).

**Never hard-code a dataset.** Everything in the package works on any log with
`date` + `user_id`.

## The workflow

1. **Infer, then ask.** `config.infer_config(csv)` proposes the column roles.
   Ask the user the four things it cannot know, in **one** `AskUserQuestion`,
   with the guesses pre-filled: user/date columns · which `event_type` counts as
   active · which columns are real segments · weekly or monthly.
2. **Remember.** `config.save_config()` writes `analysis.yaml` next to the CSV.
   If one already exists, load it and skip step 1 entirely.
3. **Read the shape.** `quality_report()` first — lead with the sparsity (panel
   density, users with gaps, empty calendar periods) and the **natural
   frequency**: the median gap between a user's active days, which is what
   should pick the retention period. It flags a grain that fights the rhythm.
4. **Overall, then segments.** All figures un-segmented first; a segment
   difference only means something against the overall shape.

`analysis.yaml` is remembered answers, not a schema. Nothing validates against
it and nothing fails a gate.

## Defaults worth stating out loud

- **`active_event` = the core action.** Retention means "did the thing", not
  "showed up". Say which definition is in force.
- **`week_start` is a decision.** Default `MON`. Match the source system — a
  product whose weeks close on Friday wants `SAT`. Note that pandas' own `W-XXX`
  aliases name the day a week *ends*; the package's parameter names the start.
- **One churn definition.** At-Risk after one missed period, Churned after a
  second. Churn is not final — a churned user who returns is Resurrected.
- **Unweighted retention curve.** Every cohort counts equally, so one huge
  acquisition spike can't define the whole curve. `weighted=True` pools instead.

## Presentation

Emojis moderately, for scanning: 📊 charts, 📈/📉 trends, ⚠️ anomalies worth
investigating, ✅ checks that passed. The metrics-and-evidence voice stays
primary. When a figure is generated, announce it as:

```
📊 <View name> — figure generated and saved to:
<path to the PNG>
```
