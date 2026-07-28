# Case studies — solution-based assignments

**Experimental. Self-contained. Nothing outside this folder is modified.**

An alternative to the Socratic `retention-tutor`: an HBS-style **case study with
data**. The student reads a one-page business case, opens the dataset, answers a
fixed set of questions, and their write-up is compared against an authored solution.

## Format

Each case is a folder holding three files:

| File | Audience | Contents |
|---|---|---|
| `CASE.md` | **Student** | The one-pager: company, dynamics, stakeholder, the ask, the data pointer, the questions, the deliverable. Self-contained — no other file needed to do the work. |
| `SOLUTION.md` | **Instructor / grader** | ⚠️ Spoilers. The authored answer to each question with computed figures, the grading rubric, and the common wrong answers to watch for. |
| `evidence.md` | Instructor | The raw computed tables the solution rests on, so a grader can check a student's number without re-deriving it. |

## Design principle — tiered disclosure

The case **names one intervention** (here: the v3.0 release, with its date) and
leaves every other anomaly in the data **unnamed**.

- The named one exercises **attribution** — quantify the effect, rule out confounds,
  defend a causal claim. This is the job most analysts actually have.
- The unnamed ones exercise **detection** — and, more importantly, they reproduce the
  most common real analyst moment: *being asked about X and finding Y*, where Y turns
  out to matter more.

Naming everything retires the detective skill; naming nothing leaves the student with
no "so what?" to answer. The split is deliberate and should be preserved when
authoring new cases.

## Grading

Each question in `SOLUTION.md` carries a three-tier rubric — **Full / Partial /
Miss** — stated in terms of *what the student must have committed to*, not wording.
Numbers are graded within a tolerance band, since reasonable methodology choices
(week boundaries, trend baselines) shift them a few points.

The intended flow: student writes answers → grader (human or model) compares against
`SOLUTION.md` → feedback names which tier each answer reached and what evidence was
missing.

## Authoring a new case

1. Pick a dataset under `datasets/`. Run the analysis yourself and write down every
   real pattern with figures — **do not** author the solution from the dataset's
   `solutions.yaml`; derive it from the data so the numbers are defensible.
2. Choose **one** anomaly to name in the case. Prefer one with a plausible product
   cause and a clean date.
3. Write the story around the company's actual dynamics — growth stage, headcount
   pressure, what the team believes, what decision is pending. The stakes are what
   make an answer *wrong* rather than merely incomplete.
4. Write 4-6 questions that escalate: describe → quantify → attribute → recommend.
5. Author `SOLUTION.md` last, and include the wrong answers you expect.

## Cases

- **`01-gambit-coach/`** — chess app, release regression, 2024 full year.
  Dataset: `datasets/chess_growth/`. Difficulty: intermediate.
