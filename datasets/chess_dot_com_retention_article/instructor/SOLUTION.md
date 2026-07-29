# Tempo — case solution and grading key

⚠️ **Spoilers.** Answer key for [`../CASE.md`](../CASE.md). Every figure below was recomputed
from `../chess_dot_com_retention_article_weekly.csv` by `case_metrics.py` in this folder,
which runs on the `datadiner` package. Run it before grading and diff your own numbers
against it.

> **Instructor note.** The dataset was generated with five deliberate shocks. A sixth
> observation — the August rollback in Q4 — is a consequence of how shock 3 was
> implemented, and it is the single best finding available in this case.
>
> Calibration is not asked as a question. It is required by the hand-in format: every
> finding carries a `CONFIDENCE` value and must be marked *established* or
> *worth investigating*. Grade that distinction as heavily as the findings.
>
> **On question form.** Q2–Q6 all name the intervention and ask whether it worked, so the
> graded skill is *choosing the right measure*, not spotting the event. Detection is still
> tested, but by Q1, which names no metric, window or hint. See "Hard mode" at the foot of
> this file for detection-form rewrites of Q2–Q6 if you want to run the case that way.

---

## 0. Method — read this before checking any number

**The data ships weekly.** One row per player per active week — a player is active in a week
if they played on any day of it. The `event_count` column (1–7 active days) is presence
intensity only and is not used by any figure below; every metric here is built on row
presence.

**Weeks start Saturday, anchored to 2024-01-06** (pandas `W-FRI`), and that anchoring is
already baked into the file. This matters more than it looks. If a student re-buckets the
dates onto Monday-anchored weeks, every cohort boundary shifts by up to six days and blends
shocked with unshocked signups: March then reads **48.4%** instead of **11.0%**, and every
magnitude in this file is muted three- to four-fold. If their step changes look smeared into
two-week ramps, check the week anchor first.

**Definitions** (these are the ones printed in `CASE.md`):

| Metric | Definition |
|---|---|
| WAU | distinct players active in the week |
| Cohort | signup week = week of first appearance (identifiers are never reissued) |
| NURR | of the cohort signing up in *w*, the share active in *w+1* |
| CURR | of players active in *w−1* who were **not new** in *w−1*, the share active in *w* |
| Churned | active in *w−1*, absent in *w* — one missed week, booked immediately |
| Quick ratio | (new + resurrected) / churned |

CURR **excludes the previous week's new arrivals**, and this is not a detail. Include them
and the year-long trend in Q6 reads +29.4pp instead of +6.8pp, because early weeks are mostly
newcomers and the "trend" is cohort mix draining out; it also swings −15.2pp in March from
the *marketing* shock, which has nothing to do with established players.

**A note on the package.** `datadiner.retention.weekly_rates()` supplies WAU, NURR, CURR,
lifecycle counts and quick ratio. `lifecycle_states()` uses a *different, more forgiving*
churn model — a player sits in `At-Risk` for a week before being booked as `Churned` — so its
Quick Ratio runs higher (median 1.39, one week below 1.0). Its `At-Risk` column equals the
`churned` column used here. Both models are defensible; this case grades on the immediate one.

**Data validation.** The correct file has exactly 1,059,597 rows, 124,333 distinct users and
52 Saturday-anchored weeks running 2024-01-06 → 2024-12-28 (week 52 covers through
2025-01-03). Its `event_count` column sums to 3,589,248, the active player-days of the daily
log it was rolled up from. If row or user counts differ, **stop and report a data mismatch** —
every tolerance below is calibrated to this generation.

---

## Q1 — Is this product healthy?

**Answer: yes on retention, no on the growth engine. Growth is real but thin.**

**The curve flattens.** Average cohort retention falls steeply for two weeks, decelerates,
and settles on a plateau:

| Week since signup | 1 | 4 | 8 | 12 | 20 | 30 | 40 |
|---|---|---|---|---|---|---|---|
| % of cohort still active | 39.7 | 40.8 | 32.3 | 28.6 | 25.4 | 23.6 | 22.8 |

The tail sits at **23.0%** across weeks 30–40 and is stable. That is the gold-standard shape
from article #6 — a durable core forms and does not erode. The product has product–market fit
for about a fifth of everyone who signs up. It is not a curve heading to zero.

**Growth is product-driven, not churn-and-replace.** The retained band grows from **31.1%**
of WAU in the second week of the year to **78.9%** in the last. A leaky bucket cannot do
that — the retained band would stay flat while new and resurrected churned in and out.

**But the quick ratio is weak.** (new + resurrected) / churned:

- median **1.19**, range **0.46 – 1.81**
- five weeks below break-even: 2024-03-16 (0.92), 2024-04-06 (0.86), 2024-08-17 (0.97),
  2024-08-24 (0.98), 2024-09-21 (0.46)

The commonly cited healthy benchmark is 4.0. Tempo is at ~1.2. It gains about six players
for every five it loses. That is growth, but it is growth with no margin for error — and
the two weeks in which acquisition paused or an outage hit are exactly the weeks it dipped
below 1.0.

**The number to rely on, and what would change the answer:** the retained-band share
(31% → 79%). If that had stayed flat while WAU tripled, the correct answer would be
"leaky bucket, stop spending." It did not, so the correct answer is "the product works,
the acquisition engine is the fragile part."

**Implication for the board decision.** Option A buys volume into a funnel whose first week
is the weakest part of it. The quick ratio says the constraint is not distribution.

### Tolerances

| Claim | Value | Tolerance |
|---|---|---|
| Retention curve plateau | 23.0% | accept 20–25% |
| Week-1 average retention | 39.7% | ±2pp |
| Retained share of WAU, week 2 | 31.1% | ±3pp |
| Retained share of WAU, final week | 78.9% | ±3pp — **the key number** |
| Quick ratio, median | 1.19 | ±0.15 |
| Quick ratio, minimum | 0.46 | ±0.05 — week of 2024-09-21 |
| Weeks with QR < 1.0 | 5 | exact list above |

**Required verdict:** healthy retention (the curve flattens, it does not go to zero) **and**
a weak growth engine (QR ~1.2 against the 4.0 benchmark). Credit "growth is product-driven,
not churn-and-replace" only if supported by the retained-band figure or an equivalent.

---

## Q2 — "In March we ran a new marketing campaign. How did it go?"

**Answer: it succeeded on the metric marketing was watching and failed on the only one that
mattered.**

**The trap is in the question.** Three defensible measures give three different verdicts:

| Judged by | Verdict |
|---|---|
| Installs — "beat target by ~40%" (marketing's own note) | Success |
| Signup volume — 2,265–2,771/week, normal | Neutral |
| **NURR — 11.0% against a 38.6% baseline** | **Disaster** |

A student who answers "it went well, installs beat target by 40%" has used a real number
from the case and reached the wrong conclusion. That is the intended failure mode, and it is
the reason this question is asked in evaluation form. Credit is for **naming the measure and
defending it**, not for finding the dip.

**What moves:** NURR, and nothing else.

| Signup week | 2024-03-02 | 03-09 | 03-16 | 03-23 | 03-30 |
|---|---|---|---|---|---|
| NURR | 11.0% | 10.5% | 10.8% | 10.9% | 11.5% |
| Cohort size | 2,265 | 2,771 | 2,268 | 2,267 | 2,621 |

Mean **11.0%** against a baseline of **38.6%** either side — a fall of **27.7 percentage
points**, or **−71.7% relative**, sustained for five consecutive signup cohorts and ending
cleanly.

**Who it hit:** new players only. CURR is undisturbed through March (**78.1–79.3%**, on
trend). Established players never noticed. Cohort sizes are normal, so acquisition *volume*
was fine — it was acquisition *quality* that collapsed.

**Temporary or permanent:** the intake damage is temporary and confined to cohorts signing
up 2 Mar – 5 Apr. The 2024-04-06 cohort is back to 39.6%.

**Probable cause:** *Feb 26 — cross-promotion campaign with a mobile puzzle-game publisher.*
The marketing note that "installs beat target by ~40%" is the tell: the campaign was judged
on installs, and installs is the metric it optimised. A puzzle-game audience is adjacent to
chess but not the same audience. The campaign concludes **Apr 2**, and the first cohort
after it is normal. **A bad marketing campaign attracted the wrong users, and those users
churned immediately.**

**Decoys to reject:** the Mar 4 office move and the Mar 11 logo refresh sit inside the
window but would affect all players, not only new ones. The Mar 25 queue-timeout change
lands too late to explain cohorts starting 2 March.

### Tolerances

**Measure axis — score this first.**

| Student judges by | Score |
|---|---|
| NURR / week-1 cohort retention | **correct** |
| Installs alone | **incorrect** — the intended failure mode |
| Signup volume alone | **incorrect** — volume was normal |
| Names two or more measures and explains why NURR governs | **excellent** |

| Claim | Value | Tolerance |
|---|---|---|
| Metric affected | NURR only | must exclude CURR |
| NURR, cohorts 03-02 → 03-30 | 11.0, 10.5, 10.8, 10.9, 11.5 (mean 11.0%) | accept 9–13% |
| Baseline NURR either side | 38.6% | accept 36–41% |
| Absolute drop | −27.7pp | accept 25–31pp |
| Relative drop | −71.7% | accept −65 to −78% |
| Window | 5 cohorts, 2024-03-02 to 2024-03-30 | accept "March" |
| Cohort sizes | 2,265–2,771, normal | must NOT claim a volume drop |
| CURR during March | 78.1–79.3%, on trend | must be undisturbed |
| Attribution | Feb 26 puzzle-game cross-promotion | Mar 4 / Mar 11 / Mar 25 = wrong |

Mark down any answer claiming March hit established players or reduced signup volume.

> ⚠️ **Known artefact in these cohorts** — the March cohorts recover to baseline by week 12,
> which real churn does not do. Not asked about in the case; see "Known artefact" below
> before responding to a student who raises it.

---

## Q3 — "What was the effect of the marketing budget cut in April?"

**Answer: it cost volume and nothing else. Behaviourally it was free.**

This question is graded on whether the student is willing to say *the cut did no damage*.
Analysts are reliably bad at this — asked about a cut, they hunt for harm. The honest answer
is that Tempo bought 24% fewer players for a month and the ones it did buy were
indistinguishable from every other cohort in the year.

A student who goes further and observes that March's campaign spent money to acquire players
worth almost nothing, while April's cut simply bought fewer normal players, has drawn the
right comparison: **April was cheaper than March in every sense that matters.**

**What moves:** signup volume, and nothing else.

| Signup week | 2024-04-06 | 04-13 | 04-20 | 04-27 |
|---|---|---|---|---|
| New players | 1,543 | 1,638 | 2,219 | 1,994 |

Non-April weekly mean is **2,436**. April's mean is **1,848**, a **−24.1%** drop; the two
trough weeks are **−34.7%**.

**Who it hit:** nobody, in behavioural terms. This is the point of the question. NURR for
April cohorts is **37.7–39.7%** and CURR is **78.7–79.5%** — both dead normal. **Fewer people
arrived, and the ones who did behaved exactly like everybody else.**

**Temporary or permanent:** temporary. Volume recovers from the 2024-04-20 week.

**Probable cause:** *Apr 3 — all performance-marketing spend paused pending the Q2 budget
review, resumed in stages from Apr 18.* The dates line up almost exactly, including the
staged recovery.

**Why this question is paired with Q2.** March and April are opposite failures. March is a
**rate** problem invisible in volume; April is a **volume** problem invisible in rates. A
student working only in retention percentages will miss April entirely — the percentages
look fine. A student working only in absolute counts will miss March — the cohort sizes
look fine. This is the case for keeping both the counts view and the percentage view, made
concrete.

### Tolerances

| Claim | Value | Tolerance |
|---|---|---|
| Metric affected | signup volume only | must exclude NURR and CURR |
| Weekly signups | 1,543 / 1,638 / 2,219 / 1,994 | exact |
| Non-April weekly mean | 2,436 | ±50 |
| April weekly mean | 1,848 | ±50 |
| Drop | −24.1% | accept −20 to −28% |
| Two trough weeks | −34.7% | accept −30 to −40% |
| NURR for April cohorts | 37.7–39.7%, normal | must be normal |
| Attribution | Apr 3 marketing spend pause | |

**Key discrimination:** the student must state that behaviour was *unaffected*. An answer
that treats April as a retention problem has misread it. Award a bonus if the student
explicitly contrasts March (rate, invisible in volume) with April (volume, invisible in
rates).

---

## Q4 — "How would you evaluate the new onboarding flow we rolled out from May through July?"

**Answer: it was the most valuable thing Tempo shipped all year, and it has not been running
since 12 August.**

**The premise of the question is wrong, and correcting it is the answer.** The question says
"May through July." The data says the improved cohorts run **25 May to 3 August**, and then
stop abruptly. A student who answers only "it worked, +19pp" has accepted the framing and
missed the finding. A student who replies "before I evaluate it — it didn't run May through
July, it ran 24 May to 12 August, and it's been off ever since" has done the job.

This is the reason to name the intervention rather than the window. In detection form the
student is looking for *an* event and will happily stop at one. In evaluation form the
stated dates are a claim they have to check.

**What moves:** NURR, upward, hard.

| Signup week | 05-25 | 06-01 | 06-08 | 06-15 | 06-22 | 06-29 | 07-06 | 07-13 | 07-20 | 07-27 | 08-03 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| NURR | 56.6 | 58.7 | 57.3 | 57.5 | 57.3 | 57.0 | 57.1 | 56.9 | 56.7 | 57.6 | 58.8 |

Mean **57.4%** against a **38.6%** baseline — **+18.8pp, or +49% relative**, held flat across
eleven consecutive cohorts. It starts with the cohort of **25 May** and ends with the cohort
of **3 August**.

The gain persists into the long run, unlike March's loss: these cohorts sit at **45.0–49.3%
at week 4** against a **39.0%** baseline, and at **28.9–38.1% at week 8** against **31.2%**.

> Two cohorts in this window read low at week 8 — 2024-07-27 at **28.9%** and 2024-08-03 at
> **30.3%**. Their week 8 lands on 21 and 28 September, i.e. inside the outage. This is a
> shock-on-shock interaction, not a failure of the onboarding flow. A student who notices
> it deserves credit; a student who uses it to argue the improvement decayed has been
> caught by it.

**Who it hit:** new players only. CURR is flat across the window.

**Probable cause:** *May 24 — new first-session flow ships to 100% of new players.* Shipped
the day before the first improved cohort. **A new onboarding flow rolled out and early
retention jumped by half.**

**Temporary or permanent — and this is the finding of the case:**

> It is **temporary, and it should not have been.** The 2024-08-10 cohort drops to **41.4%**
> and 08-17 to **37.6%** — back to baseline. That is a *snap*, not a decay. The log explains
> it: ***Aug 12 — first-session flow reverted to the previous version following a regression
> in the Android build. Release notes mark the revert "temporary." No re-ship is recorded for
> the rest of the year.***
>
> The best thing that happened to Tempo all year was switched off by accident in August and
> never switched back on. Nobody noticed, because weekly actives kept climbing the whole
> time. The *Sep 2* entry — growth PM departs, role unfilled — explains why nobody owned it.

**Decoys to reject:** Jun 3 (first tournament), Jun 17 (reconnect), Jul 8 (Coach), Jul 22
(Android stability) all sit inside the improved window and are tempting. None of them
explains a step change beginning 25 May, and none explains the August reversal. Jul 22's
Android stability release is the most seductive — note that it *precedes* an Android
regression by three weeks, which is an argument against it, not for it.

**Implication for the board decision.** Option B is not a speculative investment. Tempo has
already run the experiment, the effect size is +18.8pp NURR, and the feature is currently
turned off. This is the strongest recommendation available in the case, and it is the one
the vanity metric hid.

### Tolerances

**Premise axis — score this before anything else.**

| Student response | Score |
|---|---|
| Accepts "May through July", reports +19pp | partial — found the effect, missed the point |
| Corrects the end date to August | good |
| Identifies it as a **rollback that was never reversed** | strong |
| Carries that into the recommendation (Option B = restoring a known effect) | excellent |

| Claim | Value | Tolerance |
|---|---|---|
| Metric affected | NURR only | |
| NURR across the window | 56.6–58.8%, mean 57.4% | accept 55–61% |
| Uplift vs baseline | +18.8pp / +49% relative | accept +16 to +22pp |
| First improved cohort | **2024-05-25** | ±1 week |
| Last improved cohort | **2024-08-03** | ±1 week |
| Number of cohorts | 11 | accept 10–12 |
| Persistence, week 4 | 45.0–49.3% (vs 39.0% baseline) | ±3pp |
| Persistence, week 8 | 28.9–38.1% (vs 31.2% baseline) | ±3pp — see note above |
| Ship attribution | May 24 first-session flow | |
| **End attribution** | **Aug 12 revert, never re-shipped** | |
| Post-window NURR | 41.4% (08-10), 37.6% (08-17) | ±2pp |

**This is the highest-value item in the case.** Score it separately: *found the improvement*
= baseline credit; *bounded it at both ends* = good; *identified the end as a **rollback**,
not a decay* = strong (the evidence is that NURR snaps 58.8 → 41.4 → 37.6 in two weeks rather
than decaying, and the Aug 12 entry marks the revert "temporary" with no re-ship);
*connected it to the recommendation* = excellent.

---

## Q5 — "In mid-September a Cloudflare outage took Tempo offline for four days. How did that affect users?"

**Answer: it cost about four to five weeks of activity, permanently damaged one cohort at
intake, and the exposure that caused it is still open.**

The cause is named, so the graded work is *scope and duration*: how deep, how wide, how long,
and who it hit. The trap is accepting Lindqvist's "it fixed itself."

**What moves:** everything at once, for exactly one week.

| Metric | Week 09-14 | Week 09-21 | Week 09-28 |
|---|---|---|---|
| WAU | 28,703 | **21,927** | 23,754 |
| CURR | 82.2% | **59.2%** | 82.0% |
| Quick ratio | 1.21 | **0.46** | 1.39 |
| Churned | 5,707 | **12,501** | 4,635 |

WAU falls **−23.6%** week on week. CURR falls 23pp in one week and returns to trend the next.

**Who it hit:** everyone, simultaneously and equally. That is the diagnostic signature. In a
cohort table it is a **vertical stripe** — every cohort, regardless of age, dips in the same
calendar column. When a single column hurts all rows equally you are looking at an external
event, not a product or activation problem. The 2024-09-14 cohort takes a double hit (NURR
**29.1%**, against **38.8%** the week before) because their first week *was* the outage week.

**The signup evidence — this is what establishes scope.** New signups that week fall to
**1,520 against a 2,436 weekly baseline, −38%.** Acquisition and activity are suppressed
together, in the same week, by similar amounts. That is the signature of a failure at the
edge — strangers could not reach the site either. Had this been a single feature going down,
signups would have been untouched. A student who uses the signup drop to establish *how much
of the product was affected*, rather than listing it as one more casualty, has reasoned
properly.

**Probable cause:** *Sep 17 — elevated 5xx error rates traced to the edge provider.*
*Sep 21–25 — Cloudflare outage; Tempo unreachable for most players for four days.*
**An external infrastructure outage took the whole platform offline.** Note *Aug 1 — edge/CDN
provider consolidated onto a single vendor to cut cost, second provider contract not
renewed*: the single point of failure was created seven weeks before it failed.

**Testing Lindqvist's "it fixed itself" claim — it mostly did, but not instantly.** WAU does
not regain its pre-outage level the following week. Recovery runs
**21,927 → 23,754 → 25,738 → 27,352 → 28,592 → 29,666**: within 0.4% of the 14 September
level by the week of **19 October** (4 weeks) and fully clear of it on **26 October**
(5 weeks). The quick ratio overshoots to 1.39 the following week, which is resurrection —
players coming back, not new players arriving. So the claim is directionally right and
materially incomplete. The cost was about four weeks of suppressed activity plus one cohort
permanently damaged at intake.

**The uncomfortable follow-up:** *Sep 26 — post-incident review recommends multi-CDN
failover. Not implemented in 2024.* The dependency that caused a −24% week is still live
going into the year being planned, and none of options A–D addresses it. A strong submission
raises this without being asked, because it is the largest unpriced risk in the plan.

### Tolerances

| Claim | Value | Tolerance |
|---|---|---|
| Affected week | 2024-09-21 | exact |
| **Signups that week** | **1,520 vs 2,436 baseline (−38%)** | ±100 |
| WAU before → after | 28,703 → 21,927 | exact |
| WAU drop | −23.6% | accept −20 to −32% |
| CURR | 82.2% → **59.2%** → 82.0% | ±2pp |
| Quick ratio | 0.46 | ±0.05 |
| Churned that week | 12,501 vs 5,707 prior | ±300 |
| Who | all cohorts equally — vertical stripe | must be stated |
| 2024-09-14 cohort NURR | 29.1% (vs 38.8% prior week) | ±2pp |
| Recovery to pre-outage WAU | within 0.4% by 2024-10-19 (4 wks); clear 2024-10-26 (5 wks) | accept 3–5 weeks |
| Attribution | Sep 17 error rates, Sep 21–25 Cloudflare outage | |

**Required:** the student must show the effect was *uniform across cohorts* — the vertical
stripe — rather than concentrated in any one group. Reading the log is not sufficient; the
claim has to come from the data.

**Bonus:** noting that "it fixed itself" is incomplete; that the Sep 26 multi-CDN
recommendation was never implemented; and that *Aug 1 — edge/CDN consolidated onto a single
vendor* created the single point of failure seven weeks earlier.

---

## Q6 — "Is there any trend across the year?"

**Answer: yes — established-player weekly survival improved by ~7 percentage points, and it
is invisible in every chart the company looks at.**

**What moves:** CURR, slowly and monotonically.

| | First 4 weeks | Last 4 weeks | Change |
|---|---|---|---|
| CURR | **76.7%** | **83.5%** | **+6.8pp** |

Linear fit across the year, excluding the outage week: **+0.136pp per week ≈ +7.1pp
annualised**. There is no step anywhere — it is a slope. Weekly values move
76.8 → 76.8 → 76.8 → … → 83.4 → 83.4 → 83.9.

**Who it hit:** established players only. This is what CURR measures, and it is the reason
the metric is worth separating from NURR. A single blended "retention" number would have
mixed this steady gain with the violent NURR swings in Q2 and Q4 and shown almost nothing.

**Temporary or permanent:** permanent, and compounding. A 7pp improvement in weekly
survival is the difference between an expected lifetime of ~4.3 weeks and ~6.1 weeks for an
established player.

**Probable cause:** no single entry. *Aug 19\* — a series of small matchmaking latency
improvements begins, continues in most releases through December* is the closest match and
covers only part of the year. *Jun 17 — reconnect-on-disconnect* plausibly contributes.
**Gradual product improvements pushed CURR up across the whole year** — this is
accumulated quality work, not a launch, which is exactly why it is invisible to anyone
watching a weekly total.

**Why it is the easiest finding to miss.** It never produces a spike. On the WAU chart it is
indistinguishable from acquisition. It only becomes visible by plotting CURR as a series in
its own right.

### Tolerances

| Claim | Value | Tolerance |
|---|---|---|
| Metric affected | CURR only | must exclude NURR |
| First 4 weeks mean | 76.7% | ±1pp |
| Last 4 weeks mean | 83.5% | ±1pp |
| Change | +6.8pp | accept +5 to +9pp |
| Slope (excl. outage week) | +0.136pp/week ≈ +7.1pp/yr | ±0.04pp/week |
| Shape | monotonic drift, no step | must not be described as an event |
| Who | established players only | |
| Attribution | accumulated quality work; Aug 19 latency series, Jun 17 reconnect | no single cause is correct |

Exclude `2024-09-21` before fitting the trend. A student who leaves it in gets a slightly
flatter slope — accept it if they say why.

⚠️ **If a student reports ~+29pp here, they have included the previous week's new arrivals in
the CURR denominator.** Their number is reproducible, not random — say so, then show why
excluding newcomers is what makes this a statement about established players.

---

## Calibration — instructor reference

Not a question in the case. Use this to score the `CONFIDENCE` column in the student's
appendix. Findings are sorted by the quality of their signature, not by size.

### Bet on these

- **Q4 (onboarding + August rollback).** Eleven consecutive cohorts, a step change, a clean
  start date one day after a matching log entry, a clean end date three days after a matching
  log entry, and the effect persists to week 8. Strongest finding in the case.
- **Q5 (outage).** Vertical stripe across all cohorts, a matching incident report with
  matching dates, signups and activity suppressed together, and a plausible recovery curve.
- **Q6 (CURR drift).** Monotonic across the year, survives removal of the outage week.

### Verify before betting

- **Q3 (April budget cut).** The volume drop is unambiguous, but the *cause* rests entirely
  on one log line. Ask finance for the actual monthly spend before claiming it.
- **Q1's plateau.** Only **12 cohorts** are old enough to be observed at week 40, and they
  are the launch-era cohorts — unlikely to be representative. The triangle is thin at the
  right edge. Report the plateau with that caveat.

**Penalise a uniform confidence column.** A student who marks everything "high" has not
calibrated, even if every finding is correct. This is the axis that separates the top band.

### Known artefact — March *(do not penalise either way)*

The case no longer asks students to interrogate this, because the true explanation is a
property of the data generator rather than of any product. It is documented here so that a
student who *does* raise it is recognised rather than corrected.

The NURR collapse is real and unmissable — 11.0% against a 38.6% baseline. But follow those
cohorts forward:

| Cohort | W1 | W4 | W12 | W20 |
|---|---|---|---|---|
| 2024-03-02 | 11.0 | 33.3 | 25.4 | 24.8 |
| 2024-03-09 | 10.5 | 31.7 | 25.2 | 24.6 |
| 2024-03-16 | 10.8 | 33.5 | 27.5 | 25.2 |
| 2024-03-23 | 10.9 | 32.0 | 26.2 | 25.7 |
| 2024-03-30 | 11.5 | 32.7 | 26.4 | 25.5 |
| **2024-02-24 (baseline)** | **39.8** | **38.6** | **27.1** | **25.4** |

The March cohorts lose 72% of their week-1 return rate and then **converge back to the
baseline by week 12**. That is not how churn behaves. Players who fail to return in their
first week overwhelmingly do not reappear at normal rates in week 4 — the whole premise of
activation work is that the first session is decisive.

**Cause:** the shock was injected into the week-1 return rate without propagating through the
rest of the cohort's decay curve. It is a generator artefact, not a product signal.

**How to handle it.** The expected answer to Q2 is simply that the campaign was a quality
failure, and that is complete. If a student notes that the damage doesn't persist the way
churn should, acknowledge it as a sharp observation about the dataset and award credit. Do
not require it, and do not treat its absence as a gap.

---

## Model answer — five lines to Lindqvist

> Defend Option B. The product is healthy — the retention curve plateaus at 23% and the
> retained band grew from 31% to 79% of weekly actives, so the growth is real, not
> churn-and-replace.
>
> But the quick ratio is 1.2 against a 4.0 benchmark, and the weakest point in the funnel is
> the first week, where we lose 60% of every cohort.
>
> We already fixed that. The first-session flow shipped 24 May lifted new-user week-1
> retention from 39% to 57% and held it for eleven cohorts. It was reverted on 12 August
> after an Android regression, marked "temporary," and never re-shipped. We have been running
> without it for five months and nobody noticed because weekly actives kept rising.
>
> $1.6M of acquisition into the current funnel buys players into the version of the product
> that retains 39%. Restoring and extending the first session is a known +19pp effect for
> $480k.
>
> Two things I would not put in the plan yet: the March cohort damage doesn't decay like real
> churn and I want the raw event logs before we act on it, and the September outage
> post-mortem recommended a fallback provider that was never built — that exposure is still
> open.

---

## Grading

| Band | Description |
|---|---|
| **Pass** | Q1 answered with a number. Q4 and Q5 quantified and correctly attributed. Confidence stated somewhere. |
| **Good** | All five windows explained. March judged on NURR rather than installs. April correctly called as a volume-not-rate event with no behavioural damage. September identified as external via the cross-cohort signature. |
| **Strong** | The August rollback found and named as a rollback rather than a fade, correcting the "May through July" premise in the question. Recommendation follows from it. September scope argued from the −38% signup drop. |
| **Excellent** | The above, plus the thin right edge of the cohort triangle caveated on Q1, plus the unimplemented multi-CDN failover raised as live unpriced risk, plus a `CONFIDENCE` column that is actually discriminating rather than uniformly high. |

Weight the *worth-investigating vs. established* distinction at least as heavily as the
findings. **A confident wrong answer scores below a hedged right one.**

### Grading rules

1. **Recompute, don't recall.** Every number you assert should come from `case_metrics.py` or
   your own computation against the CSV — not from this file's tables and not from memory.
2. **Grade against realised values, not design intent.** The generator's target parameters
   (NURR 12% and 60%, a 30% outage drop, CURR 78→86%) differ from what it produced. A student
   who reports the realised value is **correct**. Never mark a student wrong for matching the
   data.
3. **Do not reveal unearned answers.** If a question was not attempted, report it as
   unattempted rather than disclosing the finding.
4. **Attribution is graded separately from quantification.** A student can find the right
   movement and name the wrong cause. Score these independently.
5. **Q2–Q6 name the intervention.** Do not award credit for "detecting" something the question
   already told the student about. The graded skills are metric choice, scope and duration,
   and on Q4 premise correction.
6. **If a number falls outside tolerance, re-derive it their way before marking it wrong.**
   Most misses are definitional — daily vs weekly grain, the week anchor, or whether CURR
   excludes new users. Say which definition would reproduce their number.

---

## Hard mode — detection-form rewrites

Not used by default. Swap these in if you want the case to test *finding* the events rather
than *judging* them. The answer key above is unchanged; only the prompts differ, and the
`measure` and `premise` axes stop applying.

| | Detection form |
|---|---|
| **Q2** | Something moved in the March signup cohorts. Find it, and say what you think caused it. |
| **Q3** | Something moved in April. Find it, and say what you think caused it. |
| **Q4** | Something moved in the cohorts that signed up between late May and August. Find it, and be precise about when it starts and when it stops. |
| **Q5** | Something happened in the week of 21 September. What was it, and what do you think caused it? |
| **Q6** | Something moves slowly across all twelve months, underneath everything else. Find it and quantify it. |

**What changes when you do this.** The case gets harder, but in a *less useful* place.
Detection form removes the metric-selection trap in Q2 (installs vs NURR), the "was the cut
actually harmful" judgement in Q3, and the premise correction in Q4 — the single best
discriminator in the whole case. In exchange it adds "can you find a thing." Consider running
one question in detection form rather than all five; Q5 is the natural choice, since an outage
genuinely arrives at an analyst's desk as a number that moved rather than as a brief.
