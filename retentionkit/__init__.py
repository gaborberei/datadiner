"""retentionkit — a minimal retention analyst for daily activity logs.

The whole package hangs off one idea: load the log once into a sparse
users x periods panel, then derive every figure from it.

    from retentionkit import ActivityMatrix, load_activity, metrics, plots

    df = load_activity("activity.csv")
    am = ActivityMatrix.build(df, grain="week", active_event="game_played")
    table = metrics.cohort_table(am, kind="retention_rate")
    fig = plots.cohort_heatmap(table, kind="retention_rate")

Or run the lot into a folder:

    from retentionkit.report import run_report
    run_report(df, dataset="myproduct", grain="week")
"""

from .io import load_activity, quality_report, format_quality_report
from .matrix import ActivityMatrix
from . import config, metrics, plots, report

__all__ = [
    "ActivityMatrix",
    "load_activity",
    "quality_report",
    "format_quality_report",
    "config",
    "metrics",
    "plots",
    "report",
]

__version__ = "0.1.0"
