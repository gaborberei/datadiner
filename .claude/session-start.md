# retentionkit — orientation

A retention analyst for daily-aggregated activity logs. One idea: load the log once
into a sparse users × periods panel, then derive every figure from it.

## Where things are

- `datasets/<name>/activity.csv` — the log (git-ignored), with its `analysis.yaml`
  next to it holding the decisions already made (core action, segments, grain).
- `retentionkit/` — the package. All shared logic lives here; skills *call* it,
  never inline the analysis.
- `output/<dataset>/<run>/` — generated: `report.md`, `charts/`, `data/`.

## Which skill

- **`/retention-analysis`** — the workflow. Read the shape of the log, then the
  figures: overall first, segments second.
- **`/dataset-onboarding`** — only when a CSV has no `analysis.yaml` beside it. It
  infers the column roles, asks the four things it can't know, and writes the file.
- **`/data-quality-gate`** — reads the log's shape (sparsity, natural frequency).
  `/retention-analysis` already runs it as its first step.

Answer the question the user actually asked. A question about the repo, a dataset, or
a metric is not a request to start a run.
