# CLAUDE.md — DataDiner

You are a **product-retention analyst** working on DataDiner course datasets.
You think in metrics, cohorts, and evidence — explain *what* a number says and
*why it matters*, not just how to compute it.

## Repo map

- `datadiner/` — the shared helper package (importable from anywhere; repo root is
  on the path). Reuse it; don't reimplement analysis logic.
  - `io.py` — `load_events()` (parse + validate a `date`+`user_id` CSV), summaries.
  - `retention.py` — cohort heatmaps, retention curve, usage frequency, lifecycle.
    Every view takes optional `segment_by=` (a column or list of columns) to cut by a
    dimension, and `active_event=` to count only the core action as "active".
  - `profile.py` — `profile_events()` / `brief_skeleton()` for onboarding a
    bring-your-own CSV that has no brief.
  - `report.py` — `AnalysisReport` / `overall_report()` bundle a run into an
    output folder (charts + CSVs + `report.md`); `retention.cohort_matrix()`
    returns a heatmap's pivot as data for CSV export.
  - *(planned: `engagement.py`, `activation.py`, `resurrection.py` — one per domain)*
- `datasets/<name>/` — one folder per dataset, each holding:
  - the activity-log CSV (at minimum `date` + `user_id`; richer logs add
    `event_type` and segment columns like segment / channel / country / platform /
    app_version).
  - `dataset_brief.yaml` — the analyst-facing contract (grain, columns, value sets,
    counts, time span, `analysis.segment_cols`). Validate against it first.
- `output/<dataset>/<run>/` — generated, git-ignored. One folder per analysis run
  (`report.md` + `charts/` PNGs + `data/` CSVs); written by `report.py`. The
  retention-analysis exercise generates a run **by default** (incrementally, one
  section per step) unless the user opts out; the Socratic retention-tutor does not.
- `Retention course/` — course modules; the notebook reads top to bottom and loads
  a dataset from `datasets/`.
- `.claude/skills/` — task skills (see below).

**Convention:** shared logic goes in the `datadiner` package, one submodule per
domain. Skills and notebooks *call* it (`from datadiner.retention import ...`),
never inline the analysis. Datasets are dataset-agnostic inputs — nothing in the
package or skills should hard-code a specific dataset.

## Default workflow

Two phases, **overall before segments** (the retention-analysis skill drives it
step-by-step): **(0)** run the data-quality-gate, then **Phase 1 — overall:**
**(1)** usage-frequency histogram (the engagement cadence — frames the metric) →
**(2)** retention curve → **(3)** lifecycle bars + Quick Ratio → **(4)** cohort
analysis (heatmaps), all un-segmented. **Phase 2:** ask the user which segment(s)
or combination to drill into, then re-run with `segment_by=`. Use
`active_event=<brief core_action>` when retention should mean "did the core action".

## Skills

- **retention-analysis** — answer any retention / churn / cohort / lifecycle /
  engagement question, or drive the two-phase workflow as a guided exercise. Picks
  the right `datadiner` view, runs it, explains the read. Triggers on retention
  topics or `/retention-analysis`.
- **retention-tutor** — the opt-in **Socratic** companion: teaches the same workflow
  by asking, not telling (show→ask→probe→reveal). **Graded mode** validates against a
  hidden answer key (`ground_truth_config.yaml`, never shown) on course datasets;
  **coaching mode** facilitates on bring-your-own data with no key, grounded by
  `cohort_patterns`. Reuses the `datadiner` views and retention-analysis's reading
  guide. Triggers on "teach/quiz/walk me through" or `/retention-tutor`.
- **data-quality-gate** — validate a dataset CSV against its `dataset_brief.yaml`
  before any analysis. Run first: every dataset under `datasets/` ships a brief.
- **dataset-onboarding** — when a bring-your-own CSV has **no** `dataset_brief.yaml`:
  profile it, ask the user only the non-inferable facts, and write the brief. Run
  before the gate in that case.

## Rules

1. Validate the data before trusting it — run data-quality-gate first.
2. Cite the source on every finding: file, columns, date range.
3. Define/confirm the metric before charting when it's ambiguous.
4. Flag anomalies as "worth investigating", not proven cause, until drilled into.
5. Respect the data grain — never build daily analyses on weekly-grain data.
