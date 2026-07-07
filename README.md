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

## Two ways to use it

Every session opens by asking which experience you want (a `SessionStart` hook —
see `.claude/session-start-menu.md`). There are two:

- **Take the course** — a guided **Socratic lesson** via the **retention-tutor**
  skill: *show → ask → probe → reveal*. It walks the very same workflow below, but
  draws the reasoning out of you instead of handing it over. It saves **figures only**
  (no `report.md`, which would leak the answers), grades against a **hidden answer key**
  on the course datasets, and switches to **coaching mode** (no key, flags "worth
  investigating") on bring-your-own data.
- **Analyze my own data** — a **direct analysis** via the **retention-analysis** skill:
  onboard a brief if the CSV lacks one → pass the **data-quality-gate** → **Phase 1**
  (overall) → **Phase 2** (segments).

Both paths share the **same** `datadiner` views and the same Phase 1 → Phase 2 spine;
they differ only in *how* it's taught and *what* gets saved.

## Workflow

```
                        ┌───────────────────────────────┐
                        │  Session start — pick a path   │
                        └───────────────┬───────────────┘
                                        │
             ┌──────────────────────────┴──────────────────────────┐
       Take the course                                       Analyze my own data
      (Socratic lesson)                                       (direct analysis)
             │                                                      │
  ┌──────────▼───────────┐                          ┌───────────────▼───────────────┐
  │ retention-tutor      │                          │   Point at an activity-log     │
  │                      │                          │  CSV (date+user_id+event_type) │
  │ show → ask → probe   │                          └───────────────┬───────────────┘
  │       → reveal       │                                          │
  │                      │                             ┌────────────┴────────────┐
  │ walks the SAME       │                             │  dataset_brief.yaml      │
  │ Phase 1 → Phase 2    │                             │  next to the CSV?        │
  │ workflow (right),    │                             └───┬──────────────────┬───┘
  │ taught Socratically  │                                NO                 YES
  │                      │                                 │                  │
  │ figures only         │                      ┌──────────▼──────────┐       │
  │ (no report.md →      │                      │ dataset-onboarding  │       │
  │  no answers leaked)  │                      │ profile CSV, ask    │       │
  │                      │                      │ non-inferable facts,│       │
  │ graded vs hidden key │                      │ WRITE the brief     │       │
  │ on course datasets;  │                      └──────────┬──────────┘       │
  │ coaching on BYO data │                                 └────────┬─────────┘
  └──────────┬───────────┘                                          │
             │                                    ┌─────────────────▼────────────────┐
             │                                    │  (0) data-quality-gate            │
             │                                    │  validate CSV vs the brief        │ ← Rule 1
             │                                    │  (grain, columns, value sets)     │
             │                                    └─────────────────┬────────────────┘
             │                                                      │ passes
             │                   ═══════════════════════════════════▼═══════════════════
             │                   ║        PHASE 1 — OVERALL (un-segmented)             ║
             │                   ║  (1) usage-frequency histogram → cadence; frames    ║
             │                   ║      the metric                                     ║
             │                   ║  (2) retention curve                                ║
             │                   ║  (3) lifecycle bars + Quick Ratio                   ║
             │                   ║  (4) cohort analysis (heatmaps)                      ║
             │                   ═══════════════════════════════╤═══════════════════════
             │                                                  │ pick segment(s)
             │                   ═══════════════════════════════▼═══════════════════════
             │                   ║        PHASE 2 — SEGMENTS                            ║
             │                   ║  re-run (1)–(4) with segment_by=<col(s)>             ║
             │                   ║  active_event=<brief core_action> for core-action    ║
             │                   ║  retention                                          ║
             │                   ═══════════════════════════════╤═══════════════════════
             │                                                  │
  ┌──────────▼───────────┐                       ┌──────────────▼───────────────┐
  │ saves FIGURES only   │                       │  Save a run? (only on ask)    │
  │ output/<ds>/         │                       │  report.py → output/<dataset> │
  │ retention_lesson/    │                       │  /<run>/ report.md + charts/  │
  └──────────────────────┘                       │  + data/ CSVs                 │
                                                  └───────────────────────────────┘

  ── Driven by skills ─────────────────────────────────────────────────────────────
     Take the course      → retention-tutor     (Socratic, opt-in; figures only)
     Analyze my own data  → dataset-onboarding → data-quality-gate → retention-analysis
     All views live in the datadiner package; skills CALL it, never inline.
```

## Datasets

The datasets that power the Socratic tutor and the guided exercises are
**synthetic**, generated by a companion repo:
[gaborberei/synthetic_data_generators](https://github.com/gaborberei/synthetic_data_generators).
No real user data is used.
