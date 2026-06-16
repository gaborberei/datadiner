---
name: dataset-onboarding
description: Build a dataset_brief.yaml for a bring-your-own CSV that doesn't ship one. Use when the user points at an activity-log CSV with no dataset_brief.yaml next to it, before any analysis or the data-quality-gate can run. Auto-detects what it can from the data and asks the user only the facts the data can't reveal, then writes the brief.
---

# Dataset onboarding

## Purpose

A user's own CSV won't ship a `dataset_brief.yaml`, but every analysis (and the
**data-quality-gate**) needs that contract. This skill builds one: **auto-detect
everything inferable from the data, ask the user only the non-inferable facts,
then write the brief** so the gate runs and the file is reusable next session.

## When to use

When the user wants to analyze a CSV under `datasets/<name>/` (or anywhere) that has
**no `dataset_brief.yaml`** beside it. Run this first; once the brief exists, hand off
to **data-quality-gate** → **retention-analysis**.

## Step 1 — Auto-profile (don't ask what the data can answer)

Use the bundled profiler — do not re-derive detection in prose:

```python
from datadiner.profile import profile_events
p = profile_events("datasets/<name>/<file>.csv")      # add sample_rows= for a fast preview of a huge file
```

`profile_events` returns what's inferable: `rows`, `columns`+dtypes,
`user_id_candidates`, `time_candidates` (with a `granularity_hint`),
`segment_candidates` (low-cardinality columns + their value sets),
`event_type_candidate` + `core_action_candidates` (by volume), a proposed
`primary_key` + its `primary_key_dupes`, and `notes`. Show the user a short summary
of what was detected.

## Step 2 — Ask ONLY the non-inferable facts

Confirm the auto-detected guesses and fill the gaps the data can't tell you. Ask
(skip any the profile makes unambiguous):

1. **User id & activity timestamp** — confirm which column is the user id and which
   carries the activity time (from `user_id_candidates` / `time_candidates`).
2. **Grain** — what does one row represent? (one event? one user-day?)
3. **What counts as "active" / the core action** — which `event_type` value defines a
   meaningful active use (from `core_action_candidates`), or "any row" for a
   presence-only `date`+`user_id` log. This becomes `analysis.core_action` and the
   `active_event=` you pass to the retention views.
4. **Segments** — which `segment_candidates` are real user attributes to cut by vs
   noise (e.g. a week index). These become `analysis.segment_cols`.
5. **Known context** — any incidents / experiments / releases the team knows about
   (optional; helps the shock hunt). 
6. **Description & folder name** — a one-line product description and the
   `datasets/<name>/` the brief belongs in.

Everything else (row count, unique users, date range, segment value sets, duplicate
key count, sparsity) is **measured, never asked**. If `primary_key_dupes > 0`, tell
the user it's usually benign second-resolution repeats and will be recorded as a
known allowance (`data_quality.primary_key_dupes_max`).

## Step 3 — Assemble, write, validate

```python
from datadiner.profile import brief_skeleton
import yaml
brief = brief_skeleton(p, answers)            # answers = the dict you collected above
yaml.safe_dump(brief, open("datasets/<name>/dataset_brief.yaml", "w"), sort_keys=False)
```

`answers` keys: `file`, `user_col`, `time_col`, `granularity`, `core_action` (or
None), `segment_cols`, `product`, `grain`, optional `sparsity` /
`primary_key_dupes_max` / `known_context`, and the measured `users` count. Pass the
real unique-user count (e.g. `pd.read_csv(path, usecols=[user_col])[user_col].nunique()`).

Then run the **data-quality-gate** on the new brief and iterate until it PASSES:

```bash
python .claude/skills/data-quality-gate/validate.py datasets/<name>/dataset_brief.yaml
```

## Remember

- The profiler's candidates are *guesses to confirm*, not decisions — always let the
  user correct the user/time/core-action picks.
- Use the brief's `analysis.segment_cols` and `core_action` straight away:
  `retention_curve(df, segment_by=[...], active_event=core_action)`.
- Loading a BYO log whose columns aren't named `date`/`user_id`: pass them through —
  `load_events(path, date_col=time_col, user_col=user_col)` renames to the canonical
  pair the retention views expect.
- Never open an answer-key file (`solutions.yaml` / `ground_truth_*`) if one sits next
  to the data.
