# Answer key — chess retention exercises

**Instructor-facing. Git-ignored. Never show this to a student.**

Every figure below was measured from `chess_dot_com_retention_article_weekly.csv`
(1,187,624 rows · 128,966 users · 2024-01-06 → 2024-12-28), not carried over from any
earlier narrative. Re-derive after regenerating the dataset — the four seeded generator
scripts change these numbers.

### A note on cohort dates that affects every answer below

The CSV stores Saturday week-starts (`2024-03-02`). The `datadiner` views —
`cohort_matrix`, the heatmaps, `weekly_rates` — label the *same* cohort by the preceding
**Monday** (`2024-02-26`). Membership and values are identical; only the printed label
shifts by four days. Below, **Saturday dates are the CSV's**, and the heatmap label is given
in parentheses where it helps. Accept either from a student as long as they're consistent
and say which they used.

---

## Part 1 — Orientation

**1.** 11 checks, `VERDICT: PASS`. The `INFO` line reports 1,164,894 missing user-weeks
(49.5%) across 84,937 users. Not a failure: the brief declares
`data_quality.sparsity: active_periods_only`, so absence *is* the zero — a player has no row
for a week they didn't play. Full credit needs the consequence: any rolling-window or streak
metric must zero-fill to a dense grid first, or `rolling(7)` means "the last 7 *active*
weeks", not the last 7 calendar weeks.

**2.** Grain: one row per user per active **week**, Saturday-anchored. Core action:
`game_played`. Segmentable: `platform`, `acquisition_channel` (from
`analysis.segment_cols`). `event_count` counts **days active in that week (1–7)** — it is a
presence count. It does **not** count games, sessions or minutes; the source log never
recorded game volume.

**3.** 1,187,624 rows · 128,966 distinct users · 2024-01-06 → 2024-12-28. All three match
`dataset.rows`, `dataset.users` and `time_coverage` in the brief exactly — which is what the
gate in task 1 already asserted.

**4.** It changes nothing: `event_type` is constant (`game_played` on every row), so the
filter matches 100% of the data and is a no-op. Knowing in advance required reading the
brief — `columns.event_type` documents a single value and says "it labels the grain, it does
not vary", and `known_context` states the no-op outright. The transferable lesson: confirm a
filter actually removes rows, or you'll believe you measured something you didn't.

**5.** `output/chess_dot_com_retention_article/<timestamp>/` containing `report.md`,
`charts/` and `data/`. Un-segmented charts go to `charts/overall/`. The convention exists so
a run's figures are organised by *cut* rather than dumped flat — segmented views route to
`charts/<segment_col>/`, so overall and segmented versions of the same view never collide.

**6.** Rule 5 — respect the data grain. Day-of-week is impossible because the weekly rollup
destroyed within-week timing: `event_count` says a player was active on three days, never
*which* three. A 7-day rolling window is impossible because there are no daily rows to roll
over at all, and rolling over weekly rows in a sparse file silently means "last 7 active
weeks". Both are unrecoverable from this file, not merely awkward — they'd need the
underlying daily log.

---

## Part 2 — Reading the views

**7.** Clearly **bimodal**: a large casual mass at ~2–4 active days/month and a distinct
committed hump at ~18–26 days/month. It is fundamentally a **weekly** product with a
substantial near-daily minority (16.0% of users average ≥15 days/month). Mean = **6.25**,
median = 3.50. The mean is a bad summary because only **11.0%** of users fall in the 5–10
day range — it lands in the *empty valley between the two humps* and describes almost
nobody. Students who report the mean without noticing the bimodality have missed the point
of running this view first.

**8.** Falls from 100% to **46.7%** at week 1, is at 35.2% by week 8, and flattens onto a
plateau of roughly **23–24%** (23.4% at week 40), essentially flat from ~week 30. The
plateau says a durable core exists: about a quarter of every intake forms a lasting habit
rather than decaying to zero, which the steep week-1 drop alone would not tell you. For no
durable core, the curve would still be visibly declining at the right edge and heading
toward zero rather than running flat.

**9.** Colour is normalised **within a column**, so a green cell claims "good *for that
age*" — good relative to other cohorts at the same weeks-since-signup. It does **not** claim
high absolute retention; a green cell at week 20 may be a much lower percentage than a
yellow cell at week 2. The grey `Users` column matters because a rate on a small cohort is
noise: a striking percentage on a few hundred players can be sampling variation, and the
cohort sizes here range from ~1,500 to ~3,800.

**10.** Yes, growing net for essentially the whole year — median quick ratio **1.15**,
starting around 1.5–1.6 and settling near 1.1. Seven weeks touch or cross below 1.0
(heatmap/`weekly_rates` labels): `2024-03-11` (0.99), `2024-04-01` (0.79), `2024-08-12`
(0.99), `2024-08-19` (0.99), **`2024-09-16` (0.34)**, `2024-12-09` (0.98), `2024-12-23`
(1.00). Only the September week is a real collapse; the others graze break-even. A student
who names only September is fine, but the April 0.79 is a legitimate second catch.

**11.** Both are "correct" — they label the same cohort under different week conventions
(CSV = Saturday start, views = preceding Monday). No retention number changes; cohort
membership and every cell value are identical. In a write-up: state the convention once
("cohorts labelled by their Saturday start, as stored in the file") and stay consistent.
The risk being taught is cross-referencing a heatmap date against a raw-data date and
concluding an event moved by a week.

---

## Part 3 — What happened in 2024

**12.** Cohorts **2024-03-02 → 2024-03-30** (heatmap `2024-02-26` → `2024-03-25`), five
consecutive weeks. Week-1 retention **33.3–34.2%** against a **~44–45%** baseline in
surrounding weeks — a gap of about **−11pp**, and the deficit persists at every age
(−10 to −19pp in the vs-average view across weeks 1–6). It is an **intake** problem: the
signal is a set of bad **rows** (each cohort is worse than its neighbours throughout its
whole life), not a diagonal. A calendar shock hitting everyone at once would instead appear
as a **diagonal** stripe — bad cells sliding one column right per row down — which is what
task 16 contains. Note signups were simultaneously *elevated* (3,126–3,824/wk vs ~2,400–2,900
baseline): more players, worse players.

**13. Trap task.** `paid` clearly drove the volume: paid signups jump from ~1,022/wk to
**1,531 / 1,827 / 1,480 / 1,528 / 1,687** across the five weeks, while organic *fell* from
1,238 to 873–1,183. The trap is concluding "paid targeting was the problem". Week-1
retention inside the window drops for **all three channels almost equally** — organic
31.2–33.9%, paid 32.0–34.5%, social 34.5–39.8% — against their own ~44–46% baselines. So paid
owns the **volume**, not the **damage**. Whatever depressed retention in that window hit
organic signups just as hard, which rules out "we bought bad users" as a complete
explanation. A student who blames paid and stops has made exactly the intended error;
one who notices the volume/damage split has the point.

**14.** Signups roughly halve: 3,617 (2024-03-30) → **1,543 / 1,638 / 2,219 / 1,994** across
April. Retention gets **better** — week-1 recovers to **43.5–45.2%**, back to the January
baseline, immediately. Implication: the extra March volume was disproportionately low-fit,
and the surrounding-weeks baseline is the platform's real quality level. To someone wanting
to restart the spend: the constraint isn't spend, it's that this particular volume source
converted players who didn't come back — restarting it without changing targeting buys the
same −11pp. Caveat worth crediting: April also carries the quick-ratio 0.79 week, so volume
was genuinely lost, not just quality gained.

**15.** Cohorts **2024-05-25 → 2024-08-03** (heatmap `2024-05-20` → `2024-07-29`), eleven
consecutive weeks. Week-1 retention **61.0–63.5%** versus ~42.6% in the weeks just before —
a lift of about **+19pp**, the largest single effect in the file. It ends cleanly: the very
next cohort, **2024-08-10**, drops to **48.0%**, then 44.0% and 42.4% — back to baseline
within three weeks. The more useful finding is **the ending**: something that produced a
+19pp improvement in new-player retention was in effect for eleven weeks and then stopped
and was never restored. The lift is a historical fact; the un-restored regression is a
live, actionable one. Credit students who frame it that way.

**16. Trap task.** Calendar week **2024-09-21** (labelled `2024-09-16` by the views). WAU
falls **32,310 → 21,927, about −32%**, with churn spiking to 15,739 in that single week
(roughly double the ~7,500 norm) and the quick ratio hitting 0.34. Aggregate WAU recovers
over about four weeks: 23,754 → 29,252 → 30,794 → **31,965** by 2024-10-19, and the
lifecycle bars show a large *Resurrected* wave doing the recovering — those are returning
players, not new ones.

The claim is **half true**. What recovered: aggregate WAU, within a month. What did **not**:
the cohort that signed up **2024-09-14**, whose first-ever return week landed inside the
outage. Its week-1 retention is **29.1%** against a ~45% baseline, and it never catches up —
that cohort is permanently impaired. The following cohort (`2024-09-21`, 1,520 signups —
also the year's smallest, since signups were suppressed during the outage) sits at 37.1%,
still below baseline. So: temporary for the installed base, permanent for the players who
happened to be brand new that week. This is the diagonal-vs-row distinction from task 12
applied in reverse.

**17.** Not a finding — **right-censoring**. `2024-12-28` is the last week in the file, so
there is no week 53 in which its cohort could return; the 0% is an artifact of the window's
edge, not player behaviour. The general trap: any cohort-age cell needs the calendar time to
have actually elapsed, and the bottom-right triangle of every cohort heatmap is
structurally empty for the same reason.

The December cohorts `2024-12-14` (**39.6%**) and `2024-12-21` (**37.6%**) do sit below the
~44–45% baseline. Correct answer: **worth investigating**, not established. The dip is real
and consistent across both weeks, but there is only one December in the file, holiday
seasonality would look identical, and the window is at the truncated end of the data where
these cohorts have the fewest observed weeks. It needs a prior year or spend data before
anyone acts on it. Marking it "established" is the error being tested.

---

## Part 4 — Synthesis

**18. The most important task. Trap.** Mean `event_count` per active user per month rises
**2.672 (Jan) → 3.437 (Dec)**, about **+29%**. The conclusion is **wrong — or right for
entirely the wrong reason.**

Split by tenure and the "improvement" disappears:

| Tenure at time of activity | Jan | Dec |
|---|---|---|
| New (signup week) | 2.633 | 2.578 |
| 1–4 weeks | 2.747 | 2.917 |
| 12+ weeks | 3.279 (Mar) | 3.585 |

New players are **flat to slightly down** across the entire year — the product is not making
anyone more engaged at the point of arrival. What actually moves is the **tenure mix of the
active base**:

| Share of weekly active rows | Jan | Dec |
|---|---|---|
| New | 61.2% | 6.0% |
| 12+ weeks | 0.0% | **66.5%** |

Tenured players were always the more intense ones (~3.3–3.6 days/week vs ~2.6 for new). As
the platform ages, they come to dominate the active base, so the *aggregate* mean rises
while **every individual tenure band is roughly flat**. This is a composition effect —
Simpson's-paradox flavoured — and it is the single most transferable lesson in the set. Any
young, growing product will show this artifact on almost any per-user intensity metric.

A student who accepts the +29% at face value has failed the task, however well they
computed it. A student who says "engagement is improving because the base is maturing" is
close but should be pushed: the base maturing is a *fact about the mix*, not evidence that
the product got better at engaging anyone.

**19.** WAU ends at **38,516**, ten players below the year's record of 38,526 (week
`2024-12-16`).

- **Getting better: CURR** — 74.4% averaged over the first eight weeks, **81.4%** over the
  last eight (monthly means run 74.7% in January to 82.0% in December). Established players
  are meaningfully stickier than they were. Mechanism: partly genuine, partly the same
  maturation as task 18 — survivors are self-selected stickier players.
- **Getting worse: the quick ratio** — **1.52** averaged over the first eight weeks,
  **1.08** over the last eight, touching 0.98–1.00 in three of the final four weeks.
  Essentially break-even by December. Mechanism: churn scales with the *installed base*
  while new signups stay roughly flat at ~2,000–3,000/week, so the denominator grows and the
  numerator doesn't. Growth is decelerating toward stall even though nothing about the
  product got worse.

Neither shows in the WAU line because WAU is a *level* and both of these are *rates*: a base
of 38,000 growing at 1.03 still sets a record every week right up until it stops. Accept
NURR-flat-to-slightly-down (44.9% Jan → 41.9% Dec) as an alternative "getting worse", but
the quick ratio is the stronger answer because it's approaching a threshold with meaning.

**20.**

*By platform* — gap open from **week 1** and never closes:

| | wk1 | wk4 | wk12 | wk40 |
|---|---|---|---|---|
| mobile (89,271 users) | 50.0% | 47.7% | 35.8% | 25.9% |
| desktop (39,695 users) | 39.2% | 35.0% | 21.1% | 17.6% |

*By channel* — **statistically indistinguishable at week 1**, then they fan out:

| | wk1 | wk4 | wk12 | wk40 |
|---|---|---|---|---|
| organic (48,684) | 46.1% | 47.2% | 36.6% | 27.6% |
| social (32,257) | 48.2% | 43.3% | 29.9% | 22.7% |
| paid (48,025) | 46.2% | 40.5% | 27.0% | 20.3% |

The implication is the whole point: **desktop has an activation problem** (its users never
start — the 11pp gap is fully open before any habit could form), while **paid has a
habit-formation problem** (its users start exactly as well as organic's and then decay
faster; by week 12 the gap is 9.6pp). A team watching only week-1 retention would see paid
at 46.2% vs organic 46.1% and conclude paid is fine — and would be wrong, because paid's
failure is entirely invisible before about week 4. Corroborating evidence from the frequency
histograms: paid produces 6.3% near-daily players against organic's 25.9%, and desktop 4.5%
against mobile's 21.1%.

---

## Grading notes

- The three deliberate traps are **13** (paid owns volume, not damage), **16** ("it fixed
  itself"), and **18** (the composition effect). A student who clears all three understands
  the material regardless of how they did on the mechanical tasks.
- **17** tests calibration rather than detection — the December dip is genuinely ambiguous
  and "worth investigating" is the right answer, not a hedge.
- Throughout, prefer an answer that names its metric and its uncertainty over one that
  reports a confident number. A confident wrong answer should score below a hedged right one.
