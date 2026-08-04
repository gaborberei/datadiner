"""Column-role inference and the remembered-answers file.

There is no dataset contract to validate against here. The assistant guesses
what it can from the file, asks the user the handful of things a CSV cannot
reveal, and writes the answers to ``analysis.yaml`` next to the data so the
questions are asked exactly once.

    from retentionkit.config import infer_config, load_config, save_config

    guess = infer_config("activity.csv")     # -> pre-fill the questions
    cfg = save_config("activity.csv", {**guess, "core_action": "game_played"})
"""

from __future__ import annotations

from pathlib import Path
import warnings

import pandas as pd
import yaml

CONFIG_NAME = "analysis.yaml"

# Above this many distinct values a column is an id or free text, not a segment.
MAX_SEGMENT_CARDINALITY = 20

_USER_HINTS = ("user", "player", "account", "customer", "member", "id")
_EVENT_HINTS = ("event", "action", "type", "activity")
_COUNT_HINTS = ("count", "events", "n_", "num", "qty", "volume")

# What the assistant must settle before analysis. Everything else is inferred.
QUESTIONS = (
    "user_col / date_col — which columns identify the user and the day",
    "core_action — which event_type counts as 'active' (or any event)",
    "segment_cols — which columns are real user segments worth cutting by",
    "grain — weekly or monthly retention periods",
)


def infer_config(source, sample_rows=200_000):
    """Guess the column roles from the data. Every value is a *proposal*.

    Parameters
    ----------
    source : str | Path | DataFrame
    sample_rows : rows to read when ``source`` is a path.

    Returns
    -------
    dict with the config keys (``user_col``, ``date_col``, ``event_col``,
    ``core_action``, ``count_col``, ``segment_cols``, ``grain``) plus
    ``_candidates`` holding the alternatives, so the caller can offer them.
    """
    if isinstance(source, pd.DataFrame):
        df = source
    else:
        df = pd.read_csv(source, nrows=sample_rows)

    cols = list(df.columns)
    nunique = {c: int(df[c].nunique(dropna=True)) for c in cols}
    n = len(df)

    date_col = _pick_date(df, cols)
    user_col = _pick_user(df, cols, nunique, n, exclude={date_col})
    event_col = _pick_event(cols, nunique, exclude={date_col, user_col})
    count_col = _pick_count(df, cols, exclude={date_col, user_col, event_col})

    segments = [
        c for c in cols
        if c not in {date_col, user_col, event_col, count_col}
        and 1 < nunique[c] <= MAX_SEGMENT_CARDINALITY
    ]

    core_action = None
    event_values = []
    if event_col:
        counts = df[event_col].value_counts()
        event_values = [str(v) for v in counts.index]
        # A single-valued event column labels the grain rather than varying, so
        # filtering on it is a no-op; propose it anyway, it costs nothing.
        core_action = event_values[0] if event_values else None

    return {
        "user_col": user_col,
        "date_col": date_col,
        "event_col": event_col,
        "core_action": core_action,
        "count_col": count_col,
        "segment_cols": segments,
        "grain": "week",
        "_candidates": {
            "date": _date_candidates(df, cols),
            "user": [c for c in cols if nunique[c] > 1 and c != date_col][:3],
            "event_values": event_values,
            "segments": {c: sorted(str(v) for v in df[c].dropna().unique())
                         for c in segments},
            "rows_sampled": n,
        },
    }


def _date_candidates(df, cols):
    """Columns that parse as plausible activity dates.

    Probing every column means most of them fail to parse — that is the point of
    the probe, so pandas' per-column "could not infer format" notice is noise
    here rather than information.
    """
    out = []
    for c in cols:
        if pd.api.types.is_numeric_dtype(df[c]):
            continue
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            parsed = pd.to_datetime(df[c], errors="coerce")
        if parsed.notna().mean() >= 0.95 and parsed.dt.year.min() >= 2000:
            out.append(c)
    return out


def _pick_date(df, cols):
    candidates = _date_candidates(df, cols)
    return candidates[0] if candidates else None


def _pick_user(df, cols, nunique, n, exclude):
    def score(c):
        name_hit = any(h in c.lower() for h in _USER_HINTS)
        # An id repeats — many distinct values, but not one per row.
        id_shaped = 1 < nunique[c] < n
        return (name_hit, id_shaped, nunique[c])

    candidates = [c for c in cols if c not in exclude and nunique[c] > 1]
    return max(candidates, key=score) if candidates else None


def _pick_event(cols, nunique, exclude):
    for c in cols:
        if c in exclude or c is None:
            continue
        if (any(h in c.lower() for h in _EVENT_HINTS)
                and nunique[c] <= MAX_SEGMENT_CARDINALITY):
            return c
    return None


def _pick_count(df, cols, exclude):
    numeric = [
        c for c in cols
        if c not in exclude and c is not None
        and pd.api.types.is_numeric_dtype(df[c])
    ]
    for c in numeric:
        if any(h in c.lower() for h in _COUNT_HINTS):
            return c
    return numeric[0] if numeric else None


# ---------------------------------------------------------------------------
# analysis.yaml
# ---------------------------------------------------------------------------

_KEYS = ("file", "user_col", "date_col", "event_col", "core_action",
         "count_col", "segment_cols", "grain", "week_start",
         "natural_frequency", "notes")


def config_path(csv_path):
    """Where the remembered answers live for a given CSV."""
    return Path(csv_path).parent / CONFIG_NAME


def load_config(csv_path):
    """Read ``analysis.yaml`` next to the CSV, or None if it isn't there yet."""
    path = config_path(csv_path)
    if not path.exists():
        return None
    cfg = yaml.safe_load(path.read_text()) or {}
    cfg["file"] = str(Path(csv_path).parent / cfg.get("file", Path(csv_path).name))
    return cfg


def save_config(csv_path, answers):
    """Write the answers to ``analysis.yaml`` next to the CSV; return the config.

    Only the keys the analysis actually reads are kept, so the file stays a
    dozen lines — it is a memo of what was decided, not a schema.
    """
    csv_path = Path(csv_path)
    cfg = {k: answers[k] for k in _KEYS if k in answers and answers[k] is not None}
    cfg["file"] = csv_path.name
    config_path(csv_path).write_text(
        yaml.safe_dump(cfg, sort_keys=False, default_flow_style=False,
                       allow_unicode=True)
    )
    return cfg


def build_kwargs(cfg):
    """The subset of a config that :meth:`ActivityMatrix.build` takes."""
    kwargs = {
        "grain": cfg.get("grain", "week"),
        "active_event": cfg.get("core_action"),
        "segment_cols": cfg.get("segment_cols") or [],
        "count_col": cfg.get("count_col", "event_count"),
    }
    if cfg.get("week_start"):
        kwargs["week_start"] = cfg["week_start"]
    return kwargs
