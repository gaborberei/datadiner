"""
DataDiner — Teaching module
==========================
Support for the Socratic `retention-tutor` skill: load a dataset's **private**
teaching rubric so the tutor can grade discoveries and aim hints — without ever
showing the answer key to the learner.

Two artifacts feed the rubric, both dataset-agnostic:

- ``<dir>/solutions.yaml`` — the hidden answer key (git-ignored as a spoiler;
  ``ground_truth_config.yaml`` is accepted as a legacy fallback). Holds the real
  ``shocks`` and the per-dimension / per-segment retention differences. **Never shown
  to the learner.** May be absent in a published checkout — then the tutor runs in
  coaching mode (facilitation, no grading).
- ``<dir>/dataset_brief.yaml`` — the analyst-facing contract. Holds the assignment
  (``task``), graduated ``hints``, ``known_context``, and the exact
  ``retention_metric`` / ``analysis`` definitions. Safe to share with the learner.

``load_rubric`` tolerates either file (or keys within them) being missing, and
normalizes the known ground-truth schemas: notion ships ``shocks`` +
``dimensions.*.retention_multiplier``; chess ships neither but has
``dimensions`` / ``segments``; the duolingo ``solutions.yaml`` nests its content under
``experiments`` and ``hidden_structure`` (``time_series.spikes``,
``segments.*.retention_mult``, ``channel_retention_multipliers``).

Usage:
    from datadiner.teaching import load_rubric
    r = load_rubric("datasets/notion")
    if r["has_answer_key"]:
        ...   # graded mode: validate findings against r["shocks"]
    else:
        ...   # coaching mode: facilitation only
"""

#: Answer-key filenames probed in order; the first that exists wins. ``solutions.yaml``
#: is the current convention; ``ground_truth_config.yaml`` is kept for legacy datasets.
ANSWER_KEY_NAMES = ("solutions.yaml", "ground_truth_config.yaml")

from pathlib import Path

import yaml


def _load_yaml(path):
    """Return a parsed YAML mapping, or {} when the file is missing/empty."""
    if not path.exists():
        return {}
    with open(path) as fh:
        return yaml.safe_load(fh) or {}


def lesson_figure_dir(dataset, subdir="overall", base_dir="output"):
    """Ensure and return ``output/<dataset>/retention_lesson/<subdir>/`` for tutor figures.

    The Socratic ``retention-tutor`` saves the **figures only** (no ``report.md``)
    of each lesson step here, so the charts land alongside other run artifacts
    instead of a temp dir. Point a view's ``save=`` / ``save_prefix=`` at this
    folder. Deliberately does NOT use ``AnalysisReport`` (which always emits a
    ``report.md`` on ``save()`` — that would hand the learner the answers).

    Figures are grouped by cut, same convention as a run folder's ``charts/``:
    un-segmented views in ``overall/`` (the default), segmented ones under the
    segment column — ``lesson_figure_dir(ds, "platform")``, combinations as
    ``lesson_figure_dir(ds, "platform_x_acquisition_channel")``.

    ``dataset`` is the dataset folder name (e.g. ``"notion_daily_scatter"``).
    """
    d = Path(base_dir) / dataset / "retention_lesson" / subdir
    d.mkdir(parents=True, exist_ok=True)
    return d


def _segment_expectations(ground_truth):
    """Pull the comparable retention differences out of a ground-truth config.

    Tolerant of every known schema: a dimension contributes when it declares a
    ``retention_multiplier`` map (notion); top-level ``segments`` contribute their
    ``retention`` block (plateau / decay) when present (chess); and the duolingo
    ``solutions.yaml`` nests per-segment ``retention_mult`` and per-channel
    multipliers under ``hidden_structure``. Returns {} when none apply.
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

    hidden = ground_truth.get("hidden_structure") or {}
    seg_mult = {
        name: spec["retention_mult"]
        for name, spec in (hidden.get("segments") or {}).items()
        if isinstance(spec, dict) and "retention_mult" in spec
    }
    if seg_mult:
        out["segments"] = seg_mult
    channel_mult = hidden.get("channel_retention_multipliers")
    if channel_mult:
        out["channel"] = channel_mult
    return out


def load_rubric(dataset_dir):
    """Load the private teaching rubric for a dataset directory.

    Parameters
    ----------
    dataset_dir : str | Path
        A ``datasets/<name>/`` directory holding a ``dataset_brief.yaml`` and,
        when available, a ``solutions.yaml`` (or legacy
        ``ground_truth_config.yaml``).

    Returns
    -------
    dict with keys:
        shocks               list of ground-truth shocks (``[]`` when none/absent);
                             falls back to ``hidden_structure.time_series.spikes``.
        segment_expectations comparable retention differences by dimension/segment.
        experiments          ground-truth A/B readouts (``[]`` when none/absent).
        metric               brief ``retention_metric`` (definitions to confirm).
        analysis             brief ``analysis`` block (core_action, segment_cols).
        task                 the assignment to frame the exercise.
        hints                graduated hints to dole out when the learner is stuck.
        known_context        shareable background context.
        has_answer_key       True only when an answer-key file (``solutions.yaml`` or
                             legacy ``ground_truth_config.yaml``) exists — selects
                             graded vs coaching mode.

    Never raises on missing files or keys: a directory with neither file yields an
    empty rubric with ``has_answer_key=False`` (pure coaching mode).
    """
    d = Path(dataset_dir)
    gt_path = next((d / name for name in ANSWER_KEY_NAMES if (d / name).exists()), None)
    ground_truth = _load_yaml(gt_path) if gt_path else {}
    brief = _load_yaml(d / "dataset_brief.yaml")

    spikes = (ground_truth.get("hidden_structure") or {}).get("time_series") or {}
    shocks = ground_truth.get("shocks") or spikes.get("spikes") or []

    return {
        "shocks": shocks,
        "segment_expectations": _segment_expectations(ground_truth),
        "experiments": ground_truth.get("experiments") or [],
        "metric": brief.get("retention_metric"),
        "analysis": brief.get("analysis"),
        "task": brief.get("task"),
        "hints": brief.get("hints"),
        "known_context": brief.get("known_context"),
        "has_answer_key": gt_path is not None,
    }
