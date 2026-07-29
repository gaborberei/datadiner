"""DataDiner — product analytics helper library.

Shared, importable from anywhere in the repo (the repo root is the package's
parent). Submodules:

    retention   cohort heatmaps, retention curve, usage frequency, lifecycle
                states, weekly rates (NURR / CURR / quick ratio)
    io          shared event-log loading and summaries
    report      bundle a run into output/<dataset>/<run>/ (charts + CSVs + report.md)
    teaching    load_rubric() — private grading rubric for the retention-tutor skill

Planned: engagement, activation, resurrection (add a submodule per domain).

Usage:
    from datadiner.io import load_events
    from datadiner.retention import retention_rate_heatmap
    # convenience: retention's public API is also re-exported here, e.g.
    from datadiner import retention_rate_heatmap
"""

from . import io  # noqa: F401
from . import profile  # noqa: F401
from .profile import profile_events, brief_skeleton
from .retention import (
    retention_counts_heatmap,
    retention_rate_heatmap,
    churn_counts_heatmap,
    churn_rate_heatmap,
    vs_average_heatmap,
    retention_curve,
    usage_frequency,
    lifecycle_states,
    weekly_rates,
    cohort_matrix,
    cohort_patterns,
)
from . import report  # noqa: F401
from .report import (
    AnalysisReport,
    cohort_sections,
    overview_sections,
    overall_report,
    ensure_phase1,
    assert_phase1_complete,
    IncompleteRunError,
    PHASE1_REQUIRED_SLUGS,
)
from . import teaching  # noqa: F401
from .teaching import load_rubric

__all__ = [
    "io",
    "profile",
    "report",
    "teaching",
    "profile_events",
    "brief_skeleton",
    "load_rubric",
    "retention_counts_heatmap",
    "retention_rate_heatmap",
    "churn_counts_heatmap",
    "churn_rate_heatmap",
    "vs_average_heatmap",
    "retention_curve",
    "usage_frequency",
    "lifecycle_states",
    "weekly_rates",
    "cohort_matrix",
    "cohort_patterns",
    "AnalysisReport",
    "cohort_sections",
    "overview_sections",
    "overall_report",
    "ensure_phase1",
    "assert_phase1_complete",
    "IncompleteRunError",
    "PHASE1_REQUIRED_SLUGS",
]
