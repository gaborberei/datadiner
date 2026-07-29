# `datasets/` — one folder per dataset

Everything about a dataset lives in its own folder: the data, the contract that describes it,
and — where one exists — the case study built on it.

```
datasets/
  README.md                        this file
  <dataset-name>/
    <dataset-name>.csv             the activity log
    dataset_brief.yaml             the analyst-facing contract
    solutions.yaml                 (optional) retention-tutor answer key — git-ignored
    CASE.md                        (optional) the case study, student-facing
```

## What every dataset ships

| File | Contents |
|---|---|
| the CSV | Required columns `date` + `user_id`; richer logs add `event_type` and segment columns (channel / country / platform / app_version). |
| `dataset_brief.yaml` | Grain, columns, value sets, counts, time span, `analysis.segment_cols`. **Validate against it before trusting the data** — run the `data-quality-gate` skill first. |

⚠️ **`.gitignore` excludes `*.csv`, so no dataset CSV is committed.** A fresh clone has the
briefs but not the data. Obtain the CSVs separately, or regenerate a derived one from its
source — e.g. the chess weekly rollup is a group-by on
`date.dt.to_period('W-FRI').dt.start_time` and `user_id`, with `event_count` as the row count.

One spoiler file can appear in a dataset folder: `solutions.yaml`, the answer key used by
the Socratic **retention-tutor** skill (via `teaching.load_rubric()`). It is git-ignored and
never shown to the learner.

---

# Case studies — solution-based assignments

**Experimental.** An alternative to the Socratic `retention-tutor`: an HBS-style **case study
with data**. The student reads a business case, opens the dataset, answers a fixed set of
questions, and their write-up is compared against an authored solution.

## Format

| File | Audience | Contents |
|---|---|---|
| `CASE.md` | **Student** | The one-pager: company, dynamics, stakeholder, the ask, the data pointer, the questions, the deliverable, and a reference section defining the metrics and charts. Self-contained — no other file needed to do the work. |

*Solution format — TBD.* How the authored solution is stored and graded is still being decided;
for now a case ships only its student-facing `CASE.md`.

The case is identified by its dataset, so a dataset carries at most one case. If a second is
ever needed on the same data, make it `cases/<name>/`.

## Design principle — tiered disclosure

The case **names some interventions** and leaves other anomalies in the data **unnamed**.

- A named one exercises **attribution** — quantify the effect, rule out confounds, defend a
  causal claim. This is the job most analysts actually have.
- An unnamed one exercises **detection** — and, more importantly, reproduces the most common
  real analyst moment: *being asked about X and finding Y*, where Y turns out to matter more.

Naming everything retires the detective skill; naming nothing leaves the student with no
"so what?" to answer. The split is deliberate and should be preserved when authoring new cases.

An **exhibit** — a product/marketing/ops log — supplies the candidate causes. Keep it honest:
every entry should either be a real cause, supply context, or be a plausible decoy the
solution teaches you to reject. Filler entries only make it longer to read.

## Authoring a new case

1. Pick a dataset. Run the analysis yourself and write down every real pattern with figures —
   **do not** author the case from the dataset's `solutions.yaml`; derive it from the data
   so the numbers are defensible.
2. Choose which anomalies to name. Prefer ones with a plausible product cause and a clean date.
3. Write the story around the company's actual dynamics — growth stage, headcount pressure,
   what the team believes, what decision is pending. The stakes are what make an answer
   *wrong* rather than merely incomplete.
4. Write 4–6 questions that escalate: describe → quantify → attribute → recommend.
5. Sweep `CASE.md` for leaks: it must not state any metric, window or magnitude the questions
   are meant to make the student find.

## Cases

- **`chess_dot_com_retention_article/`** — "Tempo", a chess platform, full-year 2024. Five
  injected shocks plus one rollback that was never reversed; the student judges five named
  interventions and finds the slow trend underneath them. Difficulty: intermediate.
  The dataset is **weekly** — one row per player per active week, Saturday-anchored, with
  `event_count` holding active days (1–7).
