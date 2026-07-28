# SOLUTION — Gambit: "Did v3.0 work?"

# ⚠️ INSTRUCTOR ONLY — SPOILERS

Do not read if you intend to attempt the case. All figures derived directly from the
CSV; supporting tables in `evidence.md`.

**The case's punchline:** the CEO's deck line is **false as written**, and the two
most important findings in the year are ones nobody asked about.

---

## Q1 — Is Gambit growing, and how?

### Answer

Yes, strongly — but the growth story has **three distinct regimes**, and the
inflection is *not* where the deck implies.

| Regime | Weeks | Signups/wk | What's happening |
|---|---|---|---|
| Flat | 0-12 (Jan–Mar) | ~260, no trend | Steady-state acquisition |
| **Dip** | **13-17 (Apr–early May)** | **116-141** | **~52 % below trend, 5 weeks** |
| Recovery | 18-29 (May–Jul) | 219-270 | Back to pre-dip level, still flat |
| **Acceleration** | **30-51 (Aug–Dec)** | **315 → 772** | **~2.4×, compounding** |

WAU: **264 → 4,920 (18.6×)**. Games: 1,294 → 27,742/wk.

### The load-bearing point

**The acceleration starts around week 30 (late July) — roughly six weeks *before*
v3.0 ships.** Whatever caused H2 growth was already running when v3.0 launched.

### Rubric

| | |
|---|---|
| **Full** | Identifies the wk-30 acceleration inflection AND the wk 13-17 signup dip, with dates and magnitudes; notes acceleration predates the release |
| **Partial** | "Growing, ~3× in H2" with a rough inflection but misses the April dip, or gives no magnitudes |
| **Miss** | Reports total growth only; no regimes; no dates |

⚠️ **Watch for:** citing 3× H2 WAU growth without noting that WAU growth is
mechanically downstream of signup growth that began earlier. Also: quoting *WAU* 18×
as "growth" without distinguishing acquisition from retention.

---

## Q2 — Did v3.0 work? *(the named intervention)*

### Answer: no. v3.0 coincides with the worst two weeks of the year.

**What happened, quantified:**

| Metric | Baseline (wk 35) | wk 36 | wk 37 | vs. trend at trough |
|---|---|---|---|---|
| WAU | 2,116 | 1,533 (**−27.6 %**) | 1,277 (**−16.7 %** further) | **~46 % below trend** |
| CURR (established) | ~69 % | 42.1 % | 41.7 % | **−26 pts** |
| NURR (cohorts 35-36) | ~43 % | 25.7 % | 21.9 % | **−20 pts** |
| Games per active | 4.64 | 4.52 | 4.43 | ~flat |

Cumulative: **~2,600 user-weeks and ~13,000 games below trend** across wk 36-38.
Recovery to trend by **wk 39-40** (early October).

**v3.0 shipped Tue 10 Sep = week 36, day 2.** The largest single-week WAU drop of the
year begins in the week the release shipped.

### The mechanism — the sharpest evidence in the case

**Games-per-active barely moves through the shock: 4.64 → 4.52 → 4.43.**

Decompose the volume drop into its two possible causes:

> games = (active players) × (games per active player)

Games fell from 9,811 to 5,653 (−42 %). Games-per-active fell 4.5 %. **Essentially
all of the drop is the player count.**

That distinction is the whole diagnosis. The release did not make players *play less*
— it stopped a large share of them from playing **at all**, while the ones who got
through played a normal number of games. That is the signature of a **broken path
into a game** (matchmaking, client crash on launch, failed update on one platform),
not of a feature people disliked or ignored. A change that merely annoyed users would
depress games-per-active; this one did not touch it.

A student who reports "activity dropped 28 %" has the *what*. A student who reports
"the player count dropped while per-player volume held, so something blocked access
rather than reduced appetite" has the *mechanism*, and that is what tells engineering
where to look.

### The attribution argument the student must make

**Pattern shape is the evidence.** The drop is a **diagonal** effect — it hits every
cohort in the same *calendar* week regardless of tenure. Established players (CURR
−26 pts) and brand-new players (NURR −20 pts) fall together. That rules out:

- a cohort-quality problem (would be **horizontal** — confined to specific signup weeks)
- a tenure/lifecycle milestone (would be **vertical** — same cohort *age*, different calendar weeks)

A simultaneous all-cohort drop is the signature of something that hit everyone at
once: a ship, an outage, or an external shock.

**Falsification tests the student should run, and the results:**

| Test | Result |
|---|---|
| Is it seasonality? | **No** — the summer trough is wk 17-29; September is seasonally *rising*. Seasonality works against the drop. |
| Is it fewer games per player (engagement) or fewer players? | **Fewer players.** g/active is flat (4.64→4.43). Players stopped showing up; those who did played normally. |
| Is it confined to a segment/platform? | No — broad-based. |
| Is it permanent? | **No** — full recovery to trend by wk 39-40, ~3 weeks. |

**The recovery is the strongest clue and the most-missed one.** A release that
genuinely made the product worse would leave a persistent lower level. A ~3-week dip
with **full recovery to the prior trend** is the signature of a **launch defect that
was hotfixed or rolled back** — not of v3.0 being the wrong product decision. The
shape says "bug, then patch," and it is the difference between a recommendation to
revert the release and a recommendation to fix the release process.

### Verdict on the deck line

> *"H2 acceleration was driven by our v3.0 release"*

**Indefensible on three counts.** (1) Acceleration began ~wk 30, six weeks before
launch. (2) The launch window contains the year's largest activity *regression*.
(3) There was no holdback group, so no causal claim about v3.0's *benefit* is
supportable from this data at all — only the timing coincidence of the harm.

An acceptable rewrite: *"H2 weekly actives grew 3×, driven by acquisition scaling
from August. v3.0 shipped in September; a launch defect cost ~3 weeks of activity
before it was resolved."*

### Rubric

| | |
|---|---|
| **Full** | Quantifies the drop (≈−28 % wk 36, ≈−40 % cumulative vs. wk 35, or ~46 % below trend); **decomposes it into player count vs. games-per-player and identifies it as a player-count collapse**; identifies the all-cohort/diagonal pattern hitting new *and* established players; notes full recovery by wk 39-40 and reads it as defect-then-fix rather than permanent damage; rules out seasonality with evidence; states the no-control-group limit; calls the deck line wrong |
| **Partial** | Finds and dates the September drop with a magnitude, links it to the release, but misses the mechanism decomposition or the recovery's significance, or asserts causation without acknowledging the missing control |
| **Miss** | Reports H2 growth as v3.0's success; or misses September entirely because they looked only at the annual trend |

⚠️ **Watch for the three dominant failure modes:**
1. **Before/after diffing.** Comparing H2 to H1 and declaring v3.0 a success. The
   annual trend hides a three-week hole.
2. **Skipping the decomposition.** Reporting the volume drop without splitting it
   into players × games-per-player. Without that split there is no mechanism, and the
   finding cannot be handed to engineering as anything actionable.
3. **Overclaiming causation.** "v3.0 caused a 28 % drop" stated flatly. The
   defensible claim is *"an all-cohort regression begins in the release week and
   recovers in three weeks; the release is the leading candidate and is worth
   investigating, but with no staged rollout we cannot separate it from a coincident
   outage."* Grade this distinction hard — the case is built to teach it.

---

## Q3 — Are new players getting better or worse? *(unnamed — detection)*

### Answer: two large cohort-quality shifts, neither previously known.

**Finding 3a — the wk 9-12 collapse (the important one).**
NURR baseline ~42 %. Cohorts signing up in **weeks 9-12 (4-31 Mar)** return at
**12.0 / 8.6 / 11.2 / 10.0 %** — a **~75 % relative collapse** confined to four
signup weeks. ~1,064 players acquired and effectively lost.

**Finding 3b — the wk 18-30 boom.** Cohorts from **weeks 18-30 (May–Jul)** retain at
**50-65 %** vs. the ~42 % baseline — sustained for 13 weeks, then settling back to
~41-45 % from week 31.

**Finding 3c — the wk 13-17 signup dip had *normal* quality.** NURR 41-51 %, i.e. at
or above baseline. Volume fell ~52 %; quality did not.

### The trap — this is the pedagogical core of Q3

The obvious hypothesis for 3a is **"we bought bad traffic."** The case explicitly
asks the student to test a hypothesis with a segment cut. The cut **kills it**:

| band | organic | paid_search | referral | social |
|---|---|---|---|---|
| wk 0-8 | 45.3 | 34.8 | 56.8 | 39.0 |
| **wk 9-12** | **10.8** | **9.1** | **13.6** | **9.8** |
| wk 13-17 | 47.6 | 40.1 | 54.4 | 42.9 |

**All four channels collapse together**, including `organic` and `referral`, which
nobody buys. Signup mix is unchanged. A bad ad source cannot depress organic and
referral retention simultaneously.

**Correct reading:** something broke **for everyone who signed up in that window,
regardless of where they came from** → a defect in the *new-player experience*
(onboarding, first-match quality, account creation) live during weeks 9-12. Worth
investigating, not proven.

**The coherent narrative** (which a strong student may assemble, and which should be
labelled a hypothesis, not a finding): a new-player defect ran wk 9-12 → it was
noticed and acquisition was throttled while it was fixed (the wk 13-17 dip, with
volume down but quality restored) → the fix over-delivered, and relaunched onboarding
produced the elevated wk 18-30 NURR → the effect decayed to a new baseline as volume
scaled from wk 31.

### Rubric

| | |
|---|---|
| **Full** | Finds 3a with cohort weeks and magnitude; runs the channel cut; **reports that it falsifies the acquisition-quality hypothesis** and redirects to a new-player-experience defect; also finds 3b; correctly dates all of it to signup cohort, not calendar week; labels causes as hypotheses |
| **Partial** | Finds the wk 9-12 collapse but skips the segment cut, or runs it and misreads it as confirming a channel problem; or finds only 3b |
| **Miss** | Reads NURR off the averaged retention curve and reports no cohort variation; or dates the anomaly to the calendar week of observation rather than the signup week |

⚠️ **Watch for:** dating the collapse to weeks 10-13 (when the *absence* is observed)
rather than the signup weeks 9-12. This is the single most common cohort-analysis
error and it changes the whole causal story — it points the investigation at the
wrong month.

---

## Q4 — What about established players? *(unnamed — trend detection)*

### Answer: ongoing retention improved materially and steadily.

CURR (week-over-week retention of players who were *not* new that week) rises from a
**~64 %** band early in the year to **~73 %** by December — **≈ +9 points**, monotone
once wk 36-37 is excluded.

```
wk  2-20 : ~62-66%
wk 21-35 : ~66-70%
wk 36-37 : 42.1 / 41.7   ← v3.0 shock, exclude from the trend
wk 41-51 : ~70-74%
```

This is a **genuinely good, entirely unreported result** — arguably the best news in
the dataset, and it is nowhere in the board deck. The product got stickier for
existing players all year.

### The confounds the student must handle

- **Cohort mix.** Late-2024 WAU is dominated by recent signups. If new players
  retained *better*, rising CURR could be composition, not improvement. Check: NURR
  for cohorts 31-51 is ~41-45 %, i.e. **at baseline, not elevated** — so the CURR
  rise is not explained by an influx of unusually good cohorts.
- **Seasonality.** The g/active trough is wk 17-29; the CURR rise continues straight
  through Nov-Dec. Not seasonal.
- **The shock.** Including wk 36-37 in a fitted trend drags the slope and can flip a
  naive regression's sign near that window.

### Rubric

| | |
|---|---|
| **Full** | Separates ongoing from new-user retention; reports the ~64→73 % / +9 pt drift with a direction; excludes or controls for wk 36-37; addresses at least one of cohort-mix or seasonality as a confound |
| **Partial** | Notes retention "improving" without magnitude, or fails to separate it from cohort effects |
| **Miss** | Reports the overall retention curve (which mixes tenure and calendar time) and concludes retention is flat |

---

## Q5 — The recommendation

### Answer

**Yes, increase spend — but the case for it is retention, not v3.0, and the mix
should shift.**

Supporting evidence:
1. **The product earns more spend.** CURR +9 pts means every acquired player is worth
   more in 2025 than in 2024. That, not v3.0, is the Series B story.
2. **Channel quality is stable and ranked all year:**
   `referral (47-68 %) > organic (41-60 %) > social (35-51 %) ≈ paid_search (33-49 %)`.
   Paid search is consistently the **worst-retaining** channel and it is where money
   goes. Shift toward referral mechanics; treat paid_search as volume, not quality.
3. **Fix the launch process before the next release.** The wk 36-37 hole cost ~13,000
   games. Shipping to 100 % with no holdback both caused the risk and destroyed the
   ability to measure the feature.
4. **Retrospectively investigate weeks 9-12.** ~1,064 players were acquired into a
   broken experience. At current spend that recurs as pure waste.

### Rubric

| | |
|---|---|
| **Full** | Recommends spend increase justified by the CURR improvement (not v3.0); names referral/organic over paid_search with the retention numbers; raises the holdback/measurement process issue |
| **Partial** | Recommends more spend on volume growth alone with no retention justification, or names channels without evidence |
| **Miss** | Recommends based on v3.0's "success"; or refuses to recommend |

---

## Overall grading

| Grade | Criterion |
|---|---|
| **Distinction** | Q2 correct *including* the recovery-implies-defect reading and the no-control-group caveat; Q3 segment cut run and correctly interpreted as falsifying; Q4 found. |
| **Pass** | Finds and correctly dates the September shock and at least one unnamed cohort anomaly; magnitudes roughly right; separates hypothesis from finding. |
| **Fail** | Accepts the deck line; or reports only the annual trend; or asserts causation with no falsification attempt. |

**Number tolerance:** ±3 pts on retention rates, ±5 % on WAU deltas. Week boundaries
and trend baselines are methodology choices; a student using ISO weeks or a different
counterfactual will land a few points off. Grade the **reasoning and the direction**,
not the decimal.

**The meta-lesson.** Devi asked one question. The two most valuable findings — the
wk 9-12 acquisition-quality collapse and the +9 pt ongoing-retention improvement —
were things nobody asked about. A student who answers only Q2 has done the assignment
and failed the job.
