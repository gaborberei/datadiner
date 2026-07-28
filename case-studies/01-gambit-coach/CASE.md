# Case study — Gambit: "Did v3.0 work?"

*Retention & growth analysis · full-year 2024 · intermediate*
*Read this page before opening the data. Budget: 90 minutes.*

---

## The company

**Gambit** is a chess app — mobile and web — founded in 2022 by two former
competitive players. You play rated games against matched opponents. That's the
whole product: no puzzles, no courses, no streaming. One action, played over and
over.

It closed a **$12M Series A in November 2023** on the strength of a clean engagement
story, and spent 2024 doing what a Series A company does — hiring, buying growth, and
building the one big feature that's supposed to justify the next round.

Where it stands at the end of 2024:

| | |
|---|---|
| Registered players who played ≥1 game in 2024 | **17,891** |
| Weekly active players, final week of December | **~4,900** |
| Weekly active players, first week of January | **~260** |
| Games played, full year | **~430,000** |
| Headcount | 24 (6 eng, 2 product, 3 growth) |
| Runway | 14 months |

**Series B conversations open in Q1 2025.** The deck is being written now.

## How the company works

Three groups, and they do not fully agree with each other.

**Growth** (led by **Aleks Nowak**) owns paid acquisition — `paid_search` and
`social` — and reports on signups. Aleks's number is *signups*, and Aleks hits it.

**Product** (led by **Devi Ramaswamy**, VP Product) owns the roadmap. Product spent
most of 2024 building one thing: **v3.0**, a full rewrite of the game client — new
matchmaking engine, redesigned board and game screen, rebuilt on both platforms.
Four engineers, five months. It was the company's single biggest bet of the year.

**v3.0 shipped to all players at once on Tuesday, 10 September 2024.** No phased
rollout, no holdback group, no staged release — the team was behind schedule and
wanted it live before the board met. There is no control group. This matters for what
you can and cannot claim.

**June Park (CEO)** is writing the Series B deck. The current draft contains this
line:

> *"H2 acceleration was driven by our v3.0 release — weekly actives grew 3× in the
> second half."*

## The ask

Devi sends you this on a Thursday:

> Hey — I need a sanity check before June puts the v3.0 line in front of investors.
>
> The 3× number is real, I checked it myself. But I sat in the launch retro and
> something felt off about September, and nobody wants to be the person who says so.
>
> I don't want a dashboard. I want to know: **did v3.0 actually do what we say it
> did?** And if the honest answer is "no" or "not the way we're telling it," I need
> to know that *before* the deck is final, not after an investor's analyst finds it.
>
> Also — you'll be in the data anyway. If anything else in this year looks wrong,
> tell me. I'd rather hear it from you.
>
> Thursday next week. Six lines, not sixty. — D

---

## The data

`../../datasets/chess_growth/chess_growth_analyst_daily.csv`

One row per **(date, user_id, event_type)** with an `event_count`.
263,125 rows · 17,891 players · **2024-01-01 → 2024-12-29**.

| Column | Notes |
|---|---|
| `date` | Calendar day |
| `user_id` | Stable per-player ID. **First observed date = signup day.** |
| `event_type` | Only ever `game_played`. There is no event mix to dissect. |
| `event_count` | Games played that day (1–26) |
| `acquisition_channel` | `organic`, `paid_search`, `referral`, `social` — fixed at signup |
| `country` | BR, DE, IN, PH, RU, UK, US — fixed at signup |
| `platform` | `android`, `ios`, `web` — fixed at signup |

**Two things about how this data behaves — read them, they will save you an hour:**

1. **A player appears on a day only if they played that day.** Absence of a row means
   no games, not missing data. Zero-fill before any rolling-window metric.
2. **Activity is decided weekly and then scattered across days.** The daily pattern
   carries day-of-week structure but *no* day-over-day dependence. A missed **day**
   is not churn. Build the lifecycle on **weeks**.

*(Week 0 = the week of 2024-01-01. Weeks run Monday–Sunday.)*

---

## Your questions

Answer all five. Show the number you're relying on and where it came from.

**Q1 — Is Gambit growing, and how?**
Characterize signup and weekly-active growth across 2024. Not "yes" — *where* the
trajectory changes, *when*, and by *how much*. If the shape changes during the year,
date it.

**Q2 — Did v3.0 work?**
This is Devi's actual question. Quantify what happened to player activity around
**10 September 2024**. Then take a position: is the release the cause? State
explicitly what evidence would *falsify* your answer, and whether you find that
evidence. If activity moved, say *through what mechanism* — fewer players, or the
same players doing less? Finally: is June's deck line defensible as written?

**Q3 — Are new players getting better or worse?**
Track how well each weekly signup cohort comes back after its first week, across the
whole year. Identify any cohorts that stand out — good or bad — and date them **to
the signup week, not the calendar week**. For anything you find, form a hypothesis
about the cause and then **test it against a segment cut**. Report what the cut does
to your hypothesis, including if it kills it.

**Q4 — What about the players who were already there?**
Separately from new signups: what happened over the year to the retention of
*established* players? Is the trend up, down, or flat, and by how much? Be careful
not to let cohort-mix or seasonality masquerade as a trend.

**Q5 — The recommendation.**
The board wants to increase paid acquisition spend for 2025. Based on what you found,
what do you tell them — and if you'd shift the mix, which channel and on what
evidence?

---

## What you hand in

**Six lines to Devi. Recommendation first, then the evidence.** Assume it gets
forwarded to the CEO without you in the room.

Attach a one-page appendix with your findings stated as:

> **WHEN** (weeks/dates) · **WHICH** metric · **MAGNITUDE** · **ROOT CAUSE** —
> and how confident you are in that cause.

Flag anything you consider *worth investigating* rather than proven. You will be
graded on that distinction as much as on the findings themselves.

---

### Two warnings

**You have no control group.** v3.0 shipped to everyone simultaneously. Any causal
claim you make is an inference from timing and pattern shape, not from an experiment.
Say so where it applies — an analyst who overclaims causation from a launch date is
the failure mode this case exists to teach.

**Devi asked you to flag anything else you find.** That sentence is not filler.
