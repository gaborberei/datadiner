"""Dataset profiling for bring-your-own (BYO) event logs.

When a user brings a CSV that does NOT ship a `dataset_brief.yaml`, we still need
the brief's facts before any analysis. This module auto-detects everything that
can be inferred from the data itself, so the dataset-onboarding skill only has to
*ask the user* the handful of things the data can't tell us (the business grain,
which event counts as "active", which candidate columns are real segments, and any
known incidents).

    from datadiner.profile import profile_events, brief_skeleton
    p = profile_events("my_events.csv")
    # ...ask the user the non-inferable bits, collect into `answers`...
    brief = brief_skeleton(p, answers)        # dict, ready to yaml.safe_dump
"""

from __future__ import annotations

import warnings

import pandas as pd
from pandas.api import types as pdt

# A column with more distinct values than this is not a usable categorical
# segment (it's an id, a free-text field, or a timestamp).
MAX_SEGMENT_CARDINALITY = 20
# id-like column name hints (used only to rank candidates, never to decide alone)
_USER_HINTS = ("user", "player", "account", "customer", "member", "id")
_EVENT_HINTS = ("event", "action", "type", "activity")


def profile_events(source, sample_rows=None):
    """Profile an event-log CSV/DataFrame; return the inferable facts as a dict.

    Parameters
    ----------
    source : str | pathlib.Path | pandas.DataFrame
        CSV path or an already-loaded frame.
    sample_rows : int, optional
        If given and `source` is a path, read only this many rows (fast preview
        on a huge file). Counts derived from a sample are flagged `sampled=True`.

    Returns
    -------
    dict with keys:
        rows, sampled, columns (name->dtype),
        user_id_candidates  : [{column, n_unique}], best first
        time_candidates     : [{column, start, end, has_time_component,
                                granularity_hint}], best first
        segment_candidates  : [{column, n_unique, values}]   (<= MAX_CARDINALITY)
        event_type_candidate: column name or None
        core_action_candidates : [{event, rows}]  (by volume) or []
        notes               : list of human-readable observations
    """
    if isinstance(source, pd.DataFrame):
        df = source.copy()
        sampled = False
    else:
        df = pd.read_csv(source, nrows=sample_rows)
        sampled = sample_rows is not None

    n = len(df)
    cols = list(df.columns)
    nunique = {c: int(df[c].nunique(dropna=True)) for c in cols}
    notes = []

    # --- time candidates: parseable as datetime -------------------------------
    # Only string/datetime columns — numeric columns (e.g. abs_week) would parse
    # as nanosecond-epoch timestamps and pollute the list.
    time_candidates = []
    for c in cols:
        if pdt.is_numeric_dtype(df[c]):
            continue
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            parsed = pd.to_datetime(df[c], errors="coerce")
        if parsed.notna().mean() < 0.95:   # mostly unparseable -> not a time col
            continue
        if parsed.dt.year.min() < 2000:    # implausible for product activity data
            continue
        has_time = bool((parsed.dt.hour.fillna(0).gt(0)
                         | parsed.dt.minute.fillna(0).gt(0)
                         | parsed.dt.second.fillna(0).gt(0)).any())
        time_candidates.append({
            "column": c,
            "start": str(parsed.min().date()),
            "end": str(parsed.max().date()),
            "has_time_component": has_time,
            # event-grain if there are real timestamps; else day-grain
            "granularity_hint": "event" if has_time else "daily",
        })
    # prefer a real timestamp column over a date-only column
    time_candidates.sort(key=lambda t: t["has_time_component"], reverse=True)
    time_cols = {t["column"] for t in time_candidates}

    # --- user_id candidates: high-cardinality, id-like name ranks first -------
    # Exclude detected time columns so dates don't show up as user ids.
    def _user_score(c):
        name_hit = any(h in c.lower() for h in _USER_HINTS)
        ratio = nunique[c] / n if n else 0   # ids: many distinct, but < ~all rows
        return (name_hit, nunique[c] > 1 and ratio < 0.95, nunique[c])

    user_cands = sorted(
        [c for c in cols if nunique[c] > 1 and c not in time_cols],
        key=_user_score, reverse=True,
    )
    user_id_candidates = [{"column": c, "n_unique": nunique[c]} for c in user_cands[:3]]

    # --- segment candidates: low-cardinality, not id/time ----------------------
    user_top = user_cands[0] if user_cands else None
    segment_candidates = []
    for c in cols:
        if c in time_cols or c == user_top:
            continue
        if 1 < nunique[c] <= MAX_SEGMENT_CARDINALITY:
            vals = sorted(str(v) for v in df[c].dropna().unique())
            segment_candidates.append({"column": c, "n_unique": nunique[c], "values": vals})

    # --- event_type column + core-action candidates ---------------------------
    event_col = None
    for c in cols:
        if c in time_cols or c == user_top:
            continue
        if any(h in c.lower() for h in _EVENT_HINTS) and nunique[c] <= MAX_SEGMENT_CARDINALITY:
            event_col = c
            break
    core_action_candidates = []
    if event_col:
        vc = df[event_col].value_counts()
        core_action_candidates = [{"event": str(k), "rows": int(v)} for k, v in vc.items()]
        # the event column shouldn't also be offered as a segment
        segment_candidates = [s for s in segment_candidates if s["column"] != event_col]

    # --- proposed primary key + duplicate count -------------------------------
    # Second-resolution event logs commonly have a few exact repeats; measuring
    # them lets the brief declare a known, benign allowance instead of failing.
    primary_key = []
    if time_candidates and user_top:
        primary_key = [time_candidates[0]["column"], user_top]
        if event_col:
            primary_key.append(event_col)
    primary_key_dupes = int(df.duplicated(primary_key).sum()) if primary_key else None
    if primary_key_dupes:
        notes.append(
            f"{primary_key_dupes:,} exact duplicate rows on {primary_key} "
            f"(common in second-resolution logs); confirm they're benign."
        )

    if not time_candidates:
        notes.append("No column parses as a date/time — confirm which column carries the activity timestamp.")
    if not event_col:
        notes.append("No event_type-like column found — this may be a presence-only (date + user_id) log; 'active' = a row exists.")
    if sampled:
        notes.append(f"Counts derived from a {sample_rows:,}-row sample; re-profile without sampling before writing final counts.")

    return {
        "rows": n,
        "sampled": sampled,
        "columns": {c: str(df[c].dtype) for c in cols},
        "user_id_candidates": user_id_candidates,
        "time_candidates": time_candidates,
        "segment_candidates": segment_candidates,
        "event_type_candidate": event_col,
        "core_action_candidates": core_action_candidates,
        "primary_key": primary_key,
        "primary_key_dupes": primary_key_dupes,
        "notes": notes,
    }


def brief_skeleton(profile, answers):
    """Assemble a dataset_brief.yaml dict from a profile + the user's answers.

    `answers` supplies the non-inferable facts the onboarding skill collected:
        file            : CSV filename (sits next to the brief)
        user_col        : the user id column
        time_col        : the activity timestamp column
        granularity     : 'event' | 'weekly' | 'daily' (default: from profile)
        core_action     : event_type that defines 'active', or None (any row)
        segment_cols    : list of columns to use as segments
        product         : one-line product description
        grain           : one-line description of what a row represents
        sparsity        : 'active_periods_only' | 'dense' (default active_periods_only)
        users           : measured unique-user count (caller passes the real number)
        known_context   : optional dict (experiments/releases/beliefs)

    The result mirrors the schema `.claude/skills/data-quality-gate/validate.py`
    reads, so it can be dumped to YAML and passed straight to the gate.
    """
    a = dict(answers)
    time_col = a["time_col"]
    user_col = a["user_col"]
    core = a.get("core_action")
    seg_cols = a.get("segment_cols") or []

    # carry value sets for documented segment columns straight from the profile
    seg_values = {s["column"]: s["values"] for s in profile.get("segment_candidates", [])}
    columns_doc = {}
    for c in seg_cols:
        if c in seg_values:
            columns_doc[c] = {"type": "string", "description": f"{c} (segment)",
                              "values": seg_values[c]}

    tinfo = next((t for t in profile.get("time_candidates", []) if t["column"] == time_col), None)

    brief = {
        "brief_version": 1,
        "schema": {
            "granularity": a.get("granularity") or (tinfo["granularity_hint"] if tinfo else "event"),
            "time_column": time_col,
            "user_column": user_col,
            "primary_key": a.get("primary_key") or (
                [time_col, user_col, "event_type"] if core else [time_col, user_col]
            ),
        },
        "analysis": {
            "natural_frequency": a.get("natural_frequency", "weekly"),
            "segment_cols": seg_cols,
        },
        "data_quality": {
            "sparsity": a.get("sparsity", "active_periods_only"),
        },
    }
    # Carry a known, benign duplicate-PK allowance so the gate passes on
    # second-resolution logs (the onboarding flow should confirm it's benign).
    dupes_max = a.get("primary_key_dupes_max", profile.get("primary_key_dupes") or 0)
    if dupes_max:
        brief["data_quality"]["primary_key_dupes_max"] = int(dupes_max)
    brief.update({
        "dataset": {
            "file": a["file"],
            "product": a.get("product", ""),
            "rows": profile["rows"],
            "users": a.get("users"),
        },
        "grain": a.get("grain", ""),
        "columns": columns_doc,
    })
    if core:
        brief["analysis"]["core_action"] = core
    if tinfo:
        brief["time_coverage"] = {"start_week": tinfo["start"], "end_week": tinfo["end"]}
    if a.get("known_context"):
        brief["known_context"] = a["known_context"]
    return brief
