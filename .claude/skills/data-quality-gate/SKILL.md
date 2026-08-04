---
name: data-quality-gate
description: Read the shape of an activity-log CSV — sparsity, natural frequency, gaps — BEFORE building any analysis on it. Use on the first load of a dataset in a session, before computing any metric, or whenever the CSV changes.
---

# Data-quality read

## Purpose

Understand the shape of the log before any figure is built on it — how sparse the
panel is, what cadence users actually keep, and which periods are missing — so the
retention period is chosen from the data rather than assumed, and so the numbers are
read with their limits in view.

## When to use

The first time a dataset is loaded in a session, before metrics or charts. Re-run if
the CSV changes. **retention-analysis runs this as its first step.**

## Instructions

All the logic lives in Python — do not re-derive checks in prose, and do not
hand-roll equivalents in pandas (that drifts from what the package actually measures):

```python
from retentionkit import load_activity, quality_report, format_quality_report
from retentionkit.config import load_config

cfg = load_config("datasets/<name>/activity.csv")
df  = load_activity(cfg["file"])
m   = quality_report(df, grain=cfg["grain"], active_event=cfg["core_action"],
                     week_start=cfg["week_start"])
print(format_quality_report(m))
```

`quality_report` measures rows/users/span, **panel density**, users with gaps, empty
calendar periods, median active periods per user, single-period users, duplicate
rows, and the **natural frequency**. `format_quality_report(m)` renders it as a short
Markdown block; `m["flags"]` is the plain-English list behind it.

## Outcome policy

**Nothing here fails or blocks.** `analysis.yaml` is remembered answers, not a schema
— nothing validates against it and there is no gate to pass. These are things for an
analyst to weigh.

Lead with, in this order:

1. **Panel density** — "of N users × P periods, activity lands in x% of cells.
   Everything else is a real zero, not missing data."
2. **Natural frequency vs the chosen grain** — the median gap between a user's active
   days. This is what should pick the retention period. If they disagree, the report
   already says so: ⚠️ a period **shorter** than the rhythm manufactures churn, a
   **longer** one hides it.
3. **The remaining flags** — empty periods, single-period users, resurrection,
   duplicates, negative counts, null user ids.

Fold the headline into the next substantive message rather than spending a turn on
it; surface the ⚠️ flags on their own, since they change how every later number reads.
Don't paste the full per-flag output unless asked.

If the data contradicts the config — the cadence has moved, a segment column is gone
— say so and offer to update `analysis.yaml`. Never silently adapt the analysis to
data that contradicts the decisions on file.

## Decision rules after the read

- **Weekly-grain source data** → day-granularity analyses are off-limits (within-week
  timing does not exist). Never build a daily dense grid for retention; the daily
  panel exists only to feed `usage_frequency`.
- **Very sparse at week grain** (density < 5%, median user active in a handful of
  weeks) → check whether monthly is the honest retention period.
- **Users with gaps** → resurrection is real in this log, so churn must not be read as
  final.
- **Event grain with gaps** → any rolling-window or streak metric needs the zero-filled
  panel first (`rolling(7)` on sparse rows means "last 7 *active* days", not "last 7
  calendar days").

## Remember

- Verification ≠ conclusions: a clean-looking log is intact, not unbiased.
- Empty calendar periods keep their column so cohort ages stay aligned. Deleting them
  would shift every later age left by one and date the whole heatmap wrong.
- `0` is "observed, nobody active"; `NaN` is "this cohort hasn't lived that long yet".
  They are not interchangeable.
