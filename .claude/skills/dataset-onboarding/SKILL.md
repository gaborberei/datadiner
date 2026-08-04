---
name: dataset-onboarding
description: Build an analysis.yaml for a bring-your-own CSV that doesn't have one. Use when the user points at an activity-log CSV with no analysis.yaml next to it, before any analysis can run. Infers the column roles from the data and asks the user only the facts the data can't reveal, then writes the config.
---

# Dataset onboarding

## Purpose

A user's own CSV won't ship an `analysis.yaml`, and the analysis needs four decisions
the data can't make for itself. This skill: **infer everything inferable, ask the user
only the non-inferable facts in one question, then write the config** so it's
remembered next session.

## When to use

When the user wants to analyze a CSV that has **no `analysis.yaml`** beside it —
i.e. `config.load_config(path)` returns `None`. Run this first; then hand off to
**data-quality-gate** → **retention-analysis**. If the file already exists, **load it
and skip this skill entirely** — the answers were already given.

## Step 1 — Infer (don't ask what the data can answer)

```python
from retentionkit.config import load_config, infer_config, save_config

if load_config(csv) is None:
    guess = infer_config(csv)          # sample_rows= to cap the read on a huge file
```

`infer_config` proposes `user_col`, `date_col`, `event_col`, `core_action`,
`count_col`, `segment_cols` and `grain`, plus `_candidates` holding the alternatives
— date candidates, other plausible user columns, the `event_type` values by volume,
and each segment column's value set. **Every value is a proposal, not a decision.**
Show the user a short summary of what was detected.

## Step 2 — Ask ONLY the non-inferable facts — in ONE question

Ask all four in a **single `AskUserQuestion`**, with the guesses pre-filled and the
`_candidates` offered as the alternatives. These are the four things inference cannot
settle (`config.QUESTIONS`):

1. **`user_col` / `date_col`** — which columns identify the user and the day.
2. **`core_action`** — which `event_type` counts as "active", or *any event* for a
   presence-only log. This is the difference between "did the thing" and "showed up".
3. **`segment_cols`** — which low-cardinality columns are real user segments worth
   cutting by, versus noise (a week index, a row tag).
4. **`grain`** — weekly or monthly retention periods. Never daily.

Also settle **`week_start`** (default `MON`) if the product's weeks close somewhere
else — match the source system. Note that pandas' `W-XXX` aliases name the day a week
*ends*; this package's parameter names the start.

Everything else — row counts, unique users, date range, segment value sets, density,
natural frequency — is **measured, never asked**. The natural frequency in particular
is measured fresh by `quality_report()` on every run, so it is not stored.

## Step 3 — Save

```python
cfg = save_config(csv, {**guess, **answers})   # writes analysis.yaml next to the CSV
```

`save_config` keeps only the keys the analysis actually reads, so the file stays about
a dozen lines — a memo of what was decided, not a schema. Nothing validates against it
and nothing fails a gate.

Then hand off to **data-quality-gate**, which reads the log's shape and will flag it
if the grain just chosen fights the cadence users actually keep — that's the one
answer worth revisiting immediately.

## Remember

- The inferred values are *guesses to confirm* — always let the user correct the
  user/date/core-action picks.
- Use the config straight away: `run_report(df, dataset=name, config=cfg)`, or
  `config.build_kwargs(cfg)` for the `ActivityMatrix.build` arguments.
- A BYO log whose columns aren't named `date`/`user_id` needs nothing special —
  `load_activity(path, date_col=..., user_col=...)` renames them to the canonical
  pair every view expects.
