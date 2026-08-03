#!/usr/bin/env python3
"""
Data-quality gate: validate a dataset CSV against its dataset_brief.yaml.

Usage:
    python validate.py [path/to/dataset_brief.yaml]   # default ./dataset_brief.yaml

Reads ONLY the brief and the CSV it describes. Checks the machine-readable
contract (columns, primary key, core action, value sets, counts, time
coverage) and summarises missing periods at the brief's granularity.

Works on any event log with at least a time column + user_id. event_type and a
count column are optional — they are only required when the brief documents
them (so a presence-only `date + user_id` log passes too).

Exit code 0 = all contract checks pass; 1 = at least one failure.
Self-contained: needs only pandas + pyyaml.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import yaml

FAILURES: list[str] = []


def check(name: str, ok: bool, expected=None, actual=None) -> None:
    if ok:
        print(f"[PASS] {name}")
    else:
        FAILURES.append(name)
        print(f"[FAIL] {name} — expected {expected!r}, got {actual!r}")


def main(brief_path: str) -> int:
    brief_path = Path(brief_path)
    if not brief_path.exists():
        print(f"[FAIL] brief not found: {brief_path}")
        return 1
    brief = yaml.safe_load(brief_path.read_text()) or {}

    schema = brief.get("schema") or {}
    analysis = brief.get("analysis") or {}
    dq = brief.get("data_quality") or {}
    dataset = brief.get("dataset") or {}
    columns_doc = brief.get("columns") or {}
    experiments = (brief.get("known_context") or {}).get("experiments") or []

    csv_file = dataset.get("file")
    if not csv_file:
        print("[FAIL] brief has no dataset.file")
        return 1
    csv_path = brief_path.parent / csv_file
    if not csv_path.exists():
        print(f"[FAIL] CSV not found: {csv_path}")
        return 1

    dtypes = {k: str for k in (schema.get("dtypes") or {})}
    # keep_default_na=False so blank variant cells stay "" and compare literally
    df = pd.read_csv(csv_path, dtype=dtypes or None, keep_default_na=False, na_values=[])
    print(f"loaded {csv_path.name}: {len(df):,} rows × {len(df.columns)} columns\n")

    time_col = schema.get("time_column", "event_time")
    user_col = schema.get("user_column", "user_id")
    count_col = schema.get("count_column")
    granularity = schema.get("granularity", "event")

    # --- declared columns exist -------------------------------------------
    # time_col + user_col are always required. event_type / count_column are
    # required only when the brief documents them (presence-only logs omit them).
    declared = [time_col, user_col]
    if "event_type" in columns_doc or analysis.get("core_action"):
        declared += ["event_type"]
    declared += [count_col] if count_col else []
    declared += analysis.get("segment_cols") or []
    declared += [e["variant_column"] for e in experiments if e.get("variant_column")]
    missing = [c for c in declared if c not in df.columns]
    check("declared columns exist", not missing, declared, f"missing {missing}")

    # --- primary key unique -------------------------------------------------
    # Exact uniqueness by default; a brief may declare a known allowance for
    # second-resolution event logs (same-second, same-type repeats are common).
    pk = schema.get("primary_key")
    if pk and all(c in df.columns for c in pk):
        dupes = int(df.duplicated(pk).sum())
        allowed = int(dq.get("primary_key_dupes_max", 0) or 0)
        label = "0 duplicates" if allowed == 0 else f"<= {allowed:,} duplicates"
        check(f"primary key {pk} unique", dupes <= allowed, label, f"{dupes:,} duplicates")

    # --- core action present -------------------------------------------------
    core = analysis.get("core_action")
    if core and "event_type" in df.columns:
        ets = set(df["event_type"].unique())
        check(f"core_action {core!r} present", core in ets, core, sorted(ets)[:10])

    # --- event_count minimum --------------------------------------------------
    if count_col and count_col in df.columns and dq.get("event_count_min") is not None:
        counts = pd.to_numeric(df[count_col], errors="coerce")
        check(f"{count_col} >= {dq['event_count_min']}",
              counts.min() >= dq["event_count_min"], f">= {dq['event_count_min']}", counts.min())

    # --- documented value sets match -------------------------------------------
    for col, spec in columns_doc.items():
        if col not in df.columns or not isinstance(spec, dict):
            continue
        values = spec.get("values")
        if isinstance(values, dict):
            expected = set(values.keys())
        elif isinstance(values, list):
            expected = {"" if v is None else str(v) for v in values}
        else:
            continue  # prose description — not enforceable
        actual = {str(v) for v in df[col].unique()}
        check(f"columns.{col}.values match data", actual == expected,
              sorted(expected), sorted(actual))

    # --- row / user counts -------------------------------------------------------
    if dataset.get("rows") is not None:
        check("dataset.rows", len(df) == int(dataset["rows"]), int(dataset["rows"]), len(df))
    if dataset.get("users") is not None and user_col in df.columns:
        raw = str(dataset["users"]).replace("~", "").replace(",", "").strip()
        approx = "~" in str(dataset["users"])
        n_users = df[user_col].nunique()
        target = int(raw)
        ok = abs(n_users - target) <= 0.05 * target if approx else n_users == target
        check(f"dataset.users ({'~5% tolerance' if approx else 'exact'})", ok, dataset["users"], n_users)

    # --- time coverage ---------------------------------------------------------------
    # Accept the grain's own vocabulary: a daily brief says start_date/end_date, a
    # weekly one start_week/end_week. Keyed on the period word so a brief that names
    # its bounds correctly is still checked, instead of silently skipping.
    tc = brief.get("time_coverage") or {}
    if time_col in df.columns:
        t = pd.to_datetime(df[time_col])

        def _first(*keys):
            """(key, value) of the first key the brief actually declares."""
            for k in keys:
                if tc.get(k):
                    return k, tc[k]
            return None, None

        key, want = _first("start_week", "start_date", "start_period", "start")
        if want:
            check(f"time_coverage.{key}", str(t.min().date()) == str(want),
                  str(want), str(t.min().date()))
        key, want = _first("end_week", "end_date", "end_period", "end")
        if want:
            check(f"time_coverage.{key}", str(t.max().date()) == str(want),
                  str(want), str(t.max().date()))
        # NB: not granularity.rstrip('ly') — that yields 'dai' for 'daily'.
        period_word = {"daily": "day", "weekly": "week", "monthly": "month"}.get(
            granularity, granularity)
        key, want = _first("n_weeks", "n_days", "n_months", "n_periods")
        if want and key in ("n_periods", f"n_{period_word}s"):
            check(f"time_coverage.{key}", t.nunique() == int(want),
                  int(want), t.nunique())

    # --- missing periods (info, judged against the declared sparsity) -----------------
    if time_col in df.columns:
        t = pd.to_datetime(df[time_col])
        # Bucket to the period FIRST so nunique counts distinct periods, not raw
        # (second-resolution) timestamps — otherwise event logs report nonsense.
        if granularity == "weekly":
            p = t.dt.to_period("W").dt.start_time
            period_days = 7
        else:
            p = t.dt.normalize()
            period_days = 1
        unit = "week" if granularity == "weekly" else "day"
        per = pd.DataFrame({"user_id": df[user_col], "p": p})
        agg = per.groupby("user_id")["p"].agg(["min", "max", "nunique"])
        span = ((agg["max"] - agg["min"]).dt.days // period_days) + 1
        missing_periods = int((span - agg["nunique"]).sum())
        pct = missing_periods / int(span.sum()) if span.sum() else 0.0
        users_with_gaps = int(((span - agg["nunique"]) > 0).sum())
        print(f"\n[INFO] missing {unit}s between each user's first and last activity: "
              f"{missing_periods:,} ({pct:.1%}); users with gaps: {users_with_gaps:,}")
        sparsity = dq.get("sparsity")
        if sparsity in ("active_weeks_only", "active_periods_only"):
            print(f"[INFO] gaps are DECLARED ({sparsity}) — expected, not a failure. "
                  f"Zero-fill before any rolling-{unit} metric.")
        elif missing_periods > 0:
            print(f"[WARN] gaps present but the brief declares no sparsity — confirm whether "
                  f"this is by design, and zero-fill before rolling-{unit} metrics.")

    print()
    if FAILURES:
        print(f"VERDICT: FAIL — {len(FAILURES)} check(s) failed: {FAILURES}")
        return 1
    print("VERDICT: PASS — data matches the brief")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "./dataset_brief.yaml"))
