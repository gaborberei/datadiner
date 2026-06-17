"""
DataDiner — Teaching module
==========================
Support for the Socratic `retention-tutor` skill: load a dataset's **private**
teaching rubric so the tutor can grade discoveries and aim hints — without ever
showing the answer key to the learner.

Two artifacts feed the rubric, both dataset-agnostic:

- ``<dir>/ground_truth_config.yaml`` — the hidden answer key (git-ignored as a
  spoiler). Holds the real ``shocks`` and the per-dimension / per-segment retention
  differences. **Never shown to the learner.** May be absent in a published checkout
  — then the tutor runs in coaching mode (facilitation, no grading).
- ``<dir>/dataset_brief.yaml`` — the analyst-facing contract. Holds the assignment
  (``task``), graduated ``hints``, ``known_context``, and the exact
  ``retention_metric`` / ``analysis`` definitions. Safe to share with the learner.

``load_rubric`` tolerates either file (or keys within them) being missing, and
normalizes the two ground-truth schemas (notion ships ``shocks`` +
``dimensions.*.retention_multiplier``; chess ships neither but has
``dimensions`` / ``segments``).

Usage:
    from datadiner.teaching import load_rubric
    r = load_rubric("datasets/notion")
    if r["has_answer_key"]:
        ...   # graded mode: validate findings against r["shocks"]
    else:
        ...   # coaching mode: facilitation only
"""

from pathlib import Path

import yaml


def _load_yaml(path):
    """Return a parsed YAML mapping, or {} when the file is missing/empty."""
    if not path.exists():
        return {}
    with open(path) as fh:
        return yaml.safe_load(fh) or {}


def _segment_expectations(ground_truth):
    """Pull the comparable retention differences out of a ground-truth config.

    Tolerant of both schemas: a dimension contributes when it declares a
    ``retention_multiplier`` map (notion); ``segments`` contribute their
    ``retention`` block (plateau / decay) when present. Returns {} if neither.
    """
    out = {}
    for dim, spec in (ground_truth.get("dimensions") or {}).items():
        if isinstance(spec, dict) and "retention_multiplier" in spec:
            out[dim] = spec["retention_multiplier"]
    segments = ground_truth.get("segments") or {}
    seg_ret = {
        name: spec["retention"]
        for name, spec in segments.items()
        if isinstance(spec, dict) and "retention" in spec
    }
    if seg_ret:
        out["segments"] = seg_ret
    return out


def load_rubric(dataset_dir):
    """Load the private teaching rubric for a dataset directory.

    Parameters
    ----------
    dataset_dir : str | Path
        A ``datasets/<name>/`` directory holding a ``dataset_brief.yaml`` and,
        when available, a ``ground_truth_config.yaml``.

    Returns
    -------
    dict with keys:
        shocks               list of ground-truth shocks (``[]`` when none/absent).
        segment_expectations comparable retention differences by dimension/segment.
        metric               brief ``retention_metric`` (definitions to confirm).
        analysis             brief ``analysis`` block (core_action, segment_cols).
        task                 the assignment to frame the exercise.
        hints                graduated hints to dole out when the learner is stuck.
        known_context        shareable background context.
        has_answer_key       True only when ``ground_truth_config.yaml`` exists —
                             selects graded vs coaching mode.

    Never raises on missing files or keys: a directory with neither file yields an
    empty rubric with ``has_answer_key=False`` (pure coaching mode).
    """
    d = Path(dataset_dir)
    gt_path = d / "ground_truth_config.yaml"
    ground_truth = _load_yaml(gt_path)
    brief = _load_yaml(d / "dataset_brief.yaml")

    return {
        "shocks": ground_truth.get("shocks") or [],
        "segment_expectations": _segment_expectations(ground_truth),
        "metric": brief.get("retention_metric"),
        "analysis": brief.get("analysis"),
        "task": brief.get("task"),
        "hints": brief.get("hints"),
        "known_context": brief.get("known_context"),
        "has_answer_key": gt_path.exists(),
    }
