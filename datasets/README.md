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
    instructor/
      SOLUTION.md                  the case answer key + grading rubric
      case_metrics.py              recomputes every figure in SOLUTION.md
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

## Which files are spoilers

Two answer keys can appear in a dataset folder. They are different things with **opposite**
rules, so don't confuse them:

| | Used by | Committed? |
|---|---|---|
| `solutions.yaml` | the Socratic **retention-tutor** skill, via `teaching.load_rubric()` | **No** — git-ignored, never shown to the learner |
| `instructor/` | the **case study**, for a human or model grading a submission | **Yes** — it is the published answer key |

---

# Case studies — solution-based assignments

**Experimental.** An alternative to the Socratic `retention-tutor`: an HBS-style **case study
with data**. The student reads a business case, opens the dataset, answers a fixed set of
questions, and their write-up is compared against an authored solution.

## Format

| File | Audience | Contents |
|---|---|---|
| `CASE.md` | **Student** | The one-pager: company, dynamics, stakeholder, the ask, the data pointer, the questions, the deliverable, and a reference section defining the metrics and charts. Self-contained — no other file needed to do the work. |
| `instructor/SOLUTION.md` | **Instructor / grader** | ⚠️ Spoilers. The authored answer to each question with computed figures, the evidence tables behind them, per-claim tolerance bands, calibration guidance, the grading rubric, and the common wrong answers to watch for. |
| `instructor/case_metrics.py` | Instructor | Recomputes every figure quoted in `SOLUTION.md` from the log, via the `datadiner` package. Run it before grading and diff your own numbers against it. |

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

## Grading

Each question in `SOLUTION.md` carries tolerance bands and a rubric stated in terms of *what
the student must have committed to*, not wording. Numbers are graded within a band, since
reasonable methodology choices (week boundaries, trend baselines) shift them a few points.

The intended flow: student writes answers → grader (human or model) runs `case_metrics.py`,
then compares against `SOLUTION.md` → feedback names which band each answer reached and what
evidence was missing.

Weight the *established vs. worth-investigating* distinction at least as heavily as the
findings themselves. A confident wrong answer scores below a hedged right one.

## Authoring a new case

1. Pick a dataset. Run the analysis yourself and write down every real pattern with figures —
   **do not** author the solution from the dataset's `solutions.yaml`; derive it from the data
   so the numbers are defensible.
2. Choose which anomalies to name. Prefer ones with a plausible product cause and a clean date.
3. Write the story around the company's actual dynamics — growth stage, headcount pressure,
   what the team believes, what decision is pending. The stakes are what make an answer
   *wrong* rather than merely incomplete.
4. Write 4–6 questions that escalate: describe → quantify → attribute → recommend.
5. Author `SOLUTION.md` last, and include the wrong answers you expect.
6. Write `case_metrics.py` on the `datadiner` package — never inline the analysis — and check
   every figure in `SOLUTION.md` against its output.
7. Sweep `CASE.md` for leaks: it must not state any metric, window or magnitude the questions
   are meant to make the student find.

## Cases

- **`chess_dot_com_retention_article/`** — "Tempo", a chess platform, full-year 2024. Five
  injected shocks plus one rollback that was never reversed; the student judges five named
  interventions and finds the slow trend underneath them. Difficulty: intermediate.
  The dataset is **weekly** — one row per player per active week, Saturday-anchored, with
  `event_count` holding active days (1–7).
