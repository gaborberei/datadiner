# Retention exercises — online chess platform, 2024

> The data is synthetic, generated for teaching. The figures are not the reported results
> of any real platform.

An online chess platform's full year of play, 2024. One row means *this player played at
least one rated game during this week* — the log is **weekly**, and a player has no row for
a week they didn't play. `event_count` holds how many **days** that week they were active
(1–7), not how many games. Two attributes come from the signup record and never change:
`platform` (`desktop` / `mobile`) and `acquisition_channel` (`organic` / `paid` / `social`),
so grouping by either splits *players*, not events. There are no ratings, no game counts, no
session lengths and no country or app-version columns.

**Data:** `chess_dot_com_retention_article_weekly.csv`, in this folder.
**Contract:** `dataset_brief.yaml`, in this folder. Read it before the CSV.

## How to work

Run `/retention-analysis` and let it drive; it saves a run to
`output/chess_dot_com_retention_article/<timestamp>/` — `report.md`, `charts/` and `data/`.
Un-segmented figures land in `charts/overall/`, segmented ones in `charts/<segment_col>/`.

Answer in your own words and **cite what you used**: which view, which columns, which date
range. A number without a source is not an answer. Where a task asks "how confident are
you", say plainly whether you'd let someone spend money on it or whether it needs another
source first.

---

## Part 1 — Orientation

Get the environment working and prove you understand what you're holding.


**1.** Without opening the CSV, answer from `dataset_brief.yaml` alone: what is the grain
of one row? What is the declared core action? Which columns can you segment by? What does
`event_count` count — and what does it *not* count?

**2.** Load the file with `datadiner.io.load_events`. Report the row count, the distinct
user count, and the first and last week. Do they match what the brief declares?

**3.** The workflow says to pass `active_event='<core_action>'` to every view. Do that here,
then check what it changed. Why does it make no difference on this dataset, and what would
you have had to look at to know that in advance?

**4.** Generate the Phase-1 overall run. Find the output folder and list what's in it. Which
subfolder do un-segmented charts go to, and why does that convention exist?

---

## Part 2 — Reading the views

**5.** Look at the usage-frequency histogram. Describe its shape. Is this a daily, weekly or
monthly product? Compute the mean average-days-active-per-month across users, then explain
why quoting that single number to a stakeholder would misrepresent the player base.

**6.** On the retention curve: where does it stop falling, and what is the level it settles
at? Say what that plateau tells you about the product that the first-week drop does not.
What would the curve have to look like instead for you to say the product has no durable
core?

**7.** From the lifecycle bars and the quick-ratio line: is the player base growing net?
Give the quick ratio's typical level for the year and say where it sits relative to the
break-even line. Identify any week it crossed that line.

**8.** The cohort heatmaps are coloured **per column**. What does a green cell actually
claim — and what does it *not* claim? Separately: why does the reading guide tell you to
look at the grey `Users` column before you trust any percentage in that row?


---

## Part 3 — What happened in 2024

Nobody has given you a list of events. Everything below is findable in the data. For each:
**name the metric you judged it by and say why that metric**, quantify the effect, say who
it hit, and say whether it was temporary or permanent.

Picking the wrong measure is the most common way to get one of these confidently wrong.

**9.** Five consecutive signup cohorts in the early-March region retain far worse than
their neighbours. Find them and quantify the gap. Then decide: is this a problem with *who
signed up in those weeks*, or something that hit everyone active at that time? Say which
heatmap direction told you, and what the other direction would have looked like instead.

**10.** Look at signup volume in the same window, broken down by `acquisition_channel`. One
channel clearly drove the extra volume. Does that same channel own the retention damage?
Check the week-1 retention of each channel inside the window before you answer — the obvious
conclusion here is only half right, and saying which half is the point of the task.

**11.** In April, weekly signups fall sharply. Did retention get worse or better? Give the
numbers. What does your answer imply about the players acquired in the previous window, and
what would you tell someone who wants to restart that spend?

**12.** A long run of consecutive cohorts starting in late May retains dramatically better
than anything before it. Find the window, quantify the lift, and identify the exact cohort
where it ends. What does the ending tell you — and which is the more useful finding for the
team, the lift or the way it stopped?

**13.** One calendar week is bad for every cohort at once, regardless of how long those
players had been around. Find it and quantify the drop in weekly actives. Then test the
claim *"it fixed itself — actives were back within a month, so there was no lasting
damage."* Check the cohort whose first return week fell inside that window before you agree.
State precisely what recovered and what didn't.

**14.** The final cohort in the file shows 0% week-1 retention. Is that a finding about the
product? Explain what produces it, and name the general trap it's an example of. While
you're there: two December cohorts retain below the year's baseline. Would you report that
as established, or as worth investigating? Defend the choice.

---

## Part 4 — Next steps


**15.**  "Should we increase marketing spend?" — build to the trap: compare channels on
week-1 retention (they tie), then on CURR and active-days (they don't). Then the
Feb-Mar surge: did more paid spend buy worse users, or did something else happen that
week? Closes on what CAC/LTV data would be needed to actually answer it.

 **16.** "How do the two platforms perform?" — mobile is 69% of users and 2.5× the active
days. Where does the gap open (week 1) and where doesn't it (CURR)? What does that
imply about desktop onboarding vs desktop engagement?

**17.**  "What should we focus on?" — forces a prioritization argument: the week-1 cliff
costs ~1,320 users per 2,480-user cohort, but the mobile/desktop and organic/paid gaps
compound over the whole flat tail. Includes the September shock as an

---

## Reference

### The metrics

If your numbers look off, check these first.

- **Week** — starts Saturday, anchored to 2024-01-06. Already baked into the data; don't
  re-bucket it.
- **WAU** — distinct players with a row in the week.
- **Cohort** — signup week = the week a player first appears. Identifiers are never
  reissued, so the earliest week a player appears is their signup week.
- **New / Retained / Resurrected / Churned**, for week *W*: *new* = first appearance is *W* ·
  *retained* = active in *W* and *W−1* · *resurrected* = active in *W*, absent in *W−1*, not
  new · *churned* = active in *W−1*, absent in *W*.
- **Quick ratio** — (new + resurrected) / churned. Above 1 the base grows, below 1 it shrinks.

Note the repo carries two deliberate churn definitions: `lifecycle_states()` holds a user in
`At-Risk` for a week before booking them `Churned`, while `weekly_rates()` churns on one
missed week. Say which you used.

### The charts

| Chart | X axis | Y axis | One point/cell means | Healthy looks like |
|---|---|---|---|---|
| **Retention curve** | weeks since signup (0, 1, 2 …) | % of the cohort still active | at age *N*, this share of signups is still playing | falls steeply, then **flattens** onto a plateau well above zero — a durable core. A curve still heading to zero at the right edge has no core. |
| **Cohort heatmap** | weeks since signup | one row per signup cohort (oldest at top) | of the cohort in this row, the % still active at this age | rows that look alike, fading gently rightward. Read the grey `Users` column first — a bright cell on a tiny cohort is noise. |
| **Lifecycle bars** | calendar week | players, new/retained/resurrected stacked up, churned down | how the active base was composed that week | the *retained* band growing as a share of the bar. If growth is all new + resurrected while retained stays flat, you are refilling a leaky bucket. |
| **Quick ratio line** | calendar week | (new + resurrected) / churned | how many players you gained for each one you lost | steady and comfortably above 1. The 1.0 line is break-even. |

Three directions worth knowing on the heatmap, because they mean different things. A **bad
row** — one cohort worse than its neighbours at every age — points at *who you acquired* that
week. A **diagonal** — one calendar period bad across every cohort regardless of age — points
at something external that hit everyone at once. A **column** — one age bad across all
cohorts — points at a tenure milestone, like a trial expiring.
