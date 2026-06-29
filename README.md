```
██████╗  █████╗ ████████╗ █████╗ ██████╗ ██╗███╗   ██╗███████╗██████╗
██╔══██╗██╔══██╗╚══██╔══╝██╔══██╗██╔══██╗██║████╗  ██║██╔════╝██╔══██╗
██║  ██║███████║   ██║   ███████║██║  ██║██║██╔██╗ ██║█████╗  ██████╔╝
██║  ██║██╔══██║   ██║   ██╔══██║██║  ██║██║██║╚██╗██║██╔══╝  ██╔══██╗
██████╔╝██║  ██║   ██║   ██║  ██║██████╔╝██║██║ ╚████║███████╗██║  ██║
╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═════╝ ╚═╝╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝
  ·  retention · cohorts · lifecycle · churn  —  metrics with evidence  ·
```

# datadiner

A toolkit and course for **product-retention analysis** — retention, cohorts,
lifecycle, and churn, done as metrics with evidence. Point it at any
`date` + `user_id` + `event_type` activity log and walk the workflow below, either as a direct
analysis or as a guided Socratic lesson. Code and datasets for my courses live here.

## Workflow

```
                      ┌─────────────────────────────────────┐
                      │      Point at an activity-log       │
                      │  CSV (date + user_id + event_type)  │
                      └──────────────────┬──────────────────┘
                                         │
                            ┌────────────┴────────────┐
                            │  Does a dataset_brief    │
                            │  .yaml sit next to it?   │
                            └────────────┬────────────┘
                                         │
                  ┌──────────────────────┴──────────────────────┐
                 NO                                             YES
                  │                                              │
       ┌──────────▼───────────┐                                 │
       │ dataset-onboarding   │                                 │
       │ profile CSV, ask the │                                 │
       │ non-inferable facts, │                                 │
       │ WRITE the brief      │                                 │
       └──────────┬───────────┘                                 │
                  └──────────────────────┬───────────────────────┘
                                         │
                          ┌──────────────▼───────────────┐
                          │  (0) data-quality-gate        │
                          │  validate CSV vs the brief    │  ← Rule 1: run first
                          │  (grain, columns, value sets) │
                          └──────────────┬───────────────┘
                                         │ passes
        ════════════════════════════════▼════════════════════════════════
        ║                  PHASE 1 — OVERALL (un-segmented)              ║
        ════════════════════════════════╤════════════════════════════════
                                         │
        ┌────────────────────────────────┼────────────────────────────────┐
        │ (1) usage-frequency histogram  →  engagement cadence; frames     │
        │     the metric                                                   │
        │            │                                                     │
        │            ▼                                                     │
        │ (2) retention curve                                              │
        │            │                                                     │
        │            ▼                                                     │
        │ (3) lifecycle bars + Quick Ratio                                 │
        │            │                                                     │
        │            ▼                                                     │
        │ (4) cohort analysis (heatmaps)                                   │
        └────────────────────────────────┬────────────────────────────────┘
                                         │
                          ┌──────────────▼───────────────┐
                          │ Ask the user: which          │
                          │ segment(s) / combination     │
                          │ to drill into?               │
                          └──────────────┬───────────────┘
                                         │
        ════════════════════════════════▼════════════════════════════════
        ║          PHASE 2 — SEGMENTS                                    ║
        ║  re-run views (1)–(4) with segment_by=<col(s)>                 ║
        ║  use active_event=<brief core_action> when retention          ║
        ║  should mean "did the core action"                            ║
        ════════════════════════════════╤════════════════════════════════
                                         │
                          ┌──────────────▼───────────────┐
                          │  Save a run? (only on ask)    │
                          │  report.py → output/<dataset> │
                          │  /<run>/  report.md + charts/ │
                          │  + data/ CSVs                 │
                          └───────────────────────────────┘

  ── Driven by skills ───────────────────────────────────────────────────
     retention-analysis  → picks the right datadiner view, runs it, reads it
     retention-tutor     → same workflow, taught Socratically (opt-in)
     All views live in the datadiner package; skills CALL it, never inline.
```

## Datasets

The datasets that power the Socratic tutor and the guided exercises are
**synthetic**, generated by a companion repo:
[gaborberei/synthetic_data_generators](https://github.com/gaborberei/synthetic_data_generators).
No real user data is used.
