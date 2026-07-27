---
name: data-quality-gate
description: Validate a dataset CSV against its dataset_brief.yaml BEFORE building any analysis on it. Use on the first load of a dataset in a session, before computing any metric, when the user asks to analyze a dataset that ships with a brief, or whenever the CSV or brief changes.
---

# Data-quality gate

## Purpose

Catch a broken, substituted, or mis-contracted data file before any analysis
is built on it — and decide, from the brief's grain, which analyses are even
meaningful on this data.

## When to use

The first time a dataset is loaded in a session. Re-run if the CSV or the brief
changes. Do not start metrics, charts, or modeling before the gate has passed
once. Every dataset under `datasets/<name>/` ships a `dataset_brief.yaml`, so
this gate always has something to check.

## Instructions

Run the bundled checker (all logic lives in Python — do not re-derive checks
in prose). Run it from the repo root, passing the brief's path, and read its
**exit code** (`0` = PASS). Do not hand-roll equivalent checks in pandas: that
produces a verbose ad-hoc report instead of the one-line outcome below, and
silently drifts from what the real checker validates.

```bash
python .claude/skills/data-quality-gate/validate.py datasets/<name>/dataset_brief.yaml
```

It validates the brief↔CSV contract (declared columns, primary-key
uniqueness, core action, documented value sets, row/user counts, time
coverage) and summarises missing periods at the brief's granularity. It works
on any event log with at least a time column + `user_id`; `event_type` and a
count column are only required when the brief documents them, so a
presence-only `date + user_id` log passes too.

Needs `pandas` + `pyyaml` (`pip install pyyaml` if missing).

## Outcome policy

- **All PASS** → proceed. **Never a standalone turn, never a question to the
  user.** Emit exactly one line, appended to the bottom of the next substantive
  message (the mission framing in tutor mode, the first chart in analysis mode):

  ```
  ✅ <dataset> verified against dataset_brief.yaml — <n>/<n> checks passed.
  ```

  Do not paste the per-check output unless asked for it.
- **Any FAIL** → **HALT analysis.** Show which check failed with expected vs
  actual, and ask the user whether the data changed intentionally. If it did,
  the brief must be updated first — never silently adapt the analysis to data
  that contradicts its brief.
- **Never ask the user to produce the validation checklist.** The gate is
  mechanical verification, not a teaching moment — it does not become a question
  even in Socratic/tutor contexts.

## Decision rules after a pass

- `schema.granularity: weekly` → day-granularity analyses are off-limits
  (within-week timing does not exist); never build a daily dense grid. Work in
  weekly windows and weekly retention.
- Event grain **with gaps** → any rolling-window or streak metric requires a
  zero-filled dense grid first (`rolling(7)` on sparse rows means "last 7
  active days", not "last 7 calendar days").

## Remember

- Verification ≠ conclusions: a passing gate says the file is intact and
  matches its contract, not that the data is unbiased.
- Gaps under a declared `data_quality.sparsity` are a quirk to handle, not a
  quality failure.
- **NEVER open an answer key** (a `solutions.yaml` / `ground_truth_*` file, if
  one sits next to the brief) — it spoils the exercise the dataset exists for.
