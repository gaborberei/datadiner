# Tempo — Is the board still growing?

*Companion case to article #6 — how to actually read retention curves, lifecycle charts
and cohorts · full-year 2024 · intermediate · budget 2–3 hours*

> Tempo is a fictional company. The dataset is synthetic and was generated for teaching
> purposes. The figures are not the reported results of any real platform.

---

## The situation

Judit Farkas had been Tempo's first data analyst for eleven weeks, and for eleven Mondays
she had sent the same email. Subject line: *Weekly actives*. One number, one chart, one
sentence of commentary. On Monday, 6 January 2025 the number was **38,104** — the highest
it had ever been — and the chart behind it was the kind that needs no explanation: a single
line leaving the bottom-left corner and arriving, without much drama, at the top-right.

Tomas Lindqvist, Tempo's VP of growth, forwarded it to the founders with three words above
it: *another record week*. Then he walked over to her desk.

> "Board meeting is the seventeenth. I've spent a year telling everybody we're in great
> shape, and I've written next year's plan on the assumption that I'm right. Before I send
> it, I'd like somebody to actually look.
>
> Is the product healthy — do people stick around, or are we filling a bucket with a hole
> in it? Did anything happen this year that we missed, because weekly actives is the only
> thing anybody here has ever looked at? And whatever is underneath all of it — is it
> getting better or worse?
>
> Nobody has prepared anything for you. There is no list. I don't know what's in there
> either."

There had been exactly one week all year in which the line went down, in late September,
and it came back within a fortnight. "We had a bad week," Lindqvist said. "Then we didn't
have a bad week any more. I didn't think about it again."

### The company

Tempo launched on 6 January 2024 with 2,748 players in the first week. A player signs up,
plays ten calibration games, gets a rating, and is then matched only against opponents
inside a narrow band of that rating. No leagues, no clubs, no video, no social graph. A
paid tier removes ads and unlocks post-game analysis; about 7% of active players subscribe.

By December Tempo employed 41 people on an $18M Series A raised on a growth curve rather
than a profit. Between 6 Jan 2024 and 3 Jan 2025, **124,333 distinct players** played at
least one rated game. Monthly actives went from 10,850 in January to 59,307 in December.

Founder Rui Anselmo describes the player he builds for:

> "A Tempo player is not an every-day person. They're a Tuesday-evening-and-Sunday-afternoon
> person. They play four games in an hour, they lose two, and you don't see them again until
> the weekend. If you build for the person who logs in daily you'll build the wrong product,
> because that person is one in fifty."

### What's at stake

The 2025 plan has one substantive line in it: **$1.6M of paid acquisition, up from $540k**.
Outside core infrastructure Tempo has four engineers and one designer, and Lindqvist intends
to walk into the board meeting defending exactly one priority.

| Option | Cost | Effect visible | Engineering |
|---|---|---|---|
| **A. Scale acquisition** | $1,600,000 | Immediately | None |
| **B. Rebuild the first session** | $480,000 | Q3 at the earliest | 2 eng + 1 designer, 2 quarters |
| **C. Lifecycle and win-back** | $340,000 | 6–8 weeks | 0.5 eng + 1 hire |
| **D. Hold** | $540,000 | — | None |

Blended cost per signup rose from **$4.10** in Q1 to **$6.30** in Q4, almost entirely on
auction price rather than any decline in conversion.

---

## The data

`chess_dot_com_retention_article_weekly.csv` — in this folder, beside this file.

**1,059,597 rows · 124,333 players · 52 weeks, 2024-01-06 → 2025-01-03**

The data is **weekly**. One row means: *this player played at least one rated game during
this week.*

| Column | Meaning |
|---|---|
| `date` | The **Saturday that starts the week**. Weeks run Saturday→Friday, anchored to 2024-01-06, so the last week starts 2024-12-28 and covers through 2025-01-03. |
| `user_id` | Stable player identifier, never reissued |
| `event_type` | Always `game_played`. Constant — it labels the grain, it does not vary. |
| `event_count` | How many **days** that week the player was active, 1–7 |

From the note the data engineer wrote for Farkas:

- This is a weekly rollup of a daily log. A player who played on three days that week and a
  player who played on one both get a single row; `event_count` is the only thing that tells
  them apart, and it counts *days*, not games.
- There are no game counts, no session lengths, no ratings, no outcomes. A player who played
  one game on Tuesday and a player who played twenty on Tuesday are identical here.
- There are no attributes. No channel, no country, no device, no plan. There is nothing
  here you can group by except time and the player themselves.
- A player has a row for a week only if they were active in it. An absent row is not a gap
  in the data — it is a week somebody didn't play. There is no such thing as a missing value
  here.
- Because identifiers are never reissued, the earliest week a player appears is their signup
  week.

A missed *day* is not churn on a product like this, which is why the data comes to you
weekly. All 52 weeks are complete — there is no truncated cohort at either end.

---

## Exhibit — product, marketing and operations log, 2024

Reconstructed after the fact from release tags, the marketing calendar, two incident reports
and eleven months of Slack. **This list is not authoritative.** Entries may be missing and
dates may be wrong. Dates marked `*` are approximate.

| Date | Entry |
|---|---|
| Feb 26 | Cross-promotion campaign with a mobile puzzle-game publisher goes live, promoting Tempo to their install base. Marketing note: "installs beat target by ~40%." |
| Mar 4 | Office move. |
| Mar 11 | Logo and colour refresh across app, web and store listings. |
| Mar 25* | Matchmaking queue timeout reduced from 45s to 20s. |
| Apr 2 | Puzzle-game cross-promotion concludes. |
| Apr 3 | All performance-marketing spend paused pending Q2 budget review. Resumed in stages from Apr 18. |
| May 24 | New first-session flow ships to 100% of new players: guided first game, opponent-strength preview before accepting a match, three-game "settling in" period excluded from rating. |
| Jun 3 | First Tempo Open runs. ~4,000 entrants. |
| Jun 17 | Reconnect-on-disconnect released — games no longer forfeited on a dropped connection. |
| Jul 8 | Coach, an AI post-game explanation feature, released to subscribers. |
| Jul 22 | Android stability release; crash rate down ~60%. |
| Aug 1 | Edge/CDN provider consolidated onto a single vendor to cut cost. Second provider contract not renewed. |
| Aug 12 | First-session flow reverted to the previous version following a regression in the Android build. Release notes mark the revert "temporary." No re-ship is recorded for the rest of the year. |
| Aug 19* | A series of small matchmaking latency improvements begins. Continues in most releases through December. |
| Sep 2 | Growth product manager departs. Role unfilled at year end. |
| Sep 17 | Elevated 5xx error rates reported on web and mobile. Traced to the edge provider; intermittent through the week. |
| Sep 21–25 | Cloudflare outage. Tempo is unreachable for most players for four days — the site, the apps and matchmaking all fail at the edge. Status page (externally hosted) updated; no email sent to players. |
| Sep 26 | Service restored. Post-incident review recommends multi-CDN failover. Not implemented in 2024. |

---

## Your questions

### Q1 — Is this product healthy?

Answer before you look at any single week. Where does the retention curve stop falling, and
what does that level tell you? Is Tempo growing on the strength of the product or on the
strength of acquisition? Give the number you are relying on, and say what it would have to
be for you to change your answer.

---

Q2–Q6 are Lindqvist's own questions, in his words. For each: **name the metric you judge it
by and say why**, quantify the effect, say who it hit, and say whether it was temporary or
permanent.

Two warnings. Picking the wrong measure is the most common way to get one of these
confidently wrong. And the questions are his, not the data's — if a question's dates don't
match what you find, say so. That correction is part of the answer.

### Q2 — March 2024

**In March we ran a new marketing campaign. How did it go?**

### Q3 — April 2024

**What was the effect of the marketing budget cut in April?**

Q2 and Q3 are different kinds of event. If the metric you chose for one surfaces nothing in
the other, your method has a hole in it — say what the hole is.

### Q4 — May through July 2024

**How would you evaluate the new onboarding flow we rolled out from May through July?**

### Q5 — Mid-September 2024

**In mid-September a Cloudflare outage took Tempo offline for four days. How did that affect
users?**

Lindqvist's position is that it fixed itself. Test that claim rather than accepting it.

### Q6 — The whole year

**Is there any trend across the year?**

Something moves slowly across all twelve months, underneath everything above. It will not
appear as a spike in any single week, and it is not visible in weekly actives at all.

---

## What you hand in

**Five lines to Lindqvist, answer first** — which option he should defend on the
seventeenth, and why.

Then an appendix listing each finding as:

> **WHEN** · **WHICH** metric · **MAGNITUDE** · **CONFIDENCE**

### What CONFIDENCE means, and why it is here

Lindqvist is going to repeat your findings to a board and spend money on them. He needs to
know which ones he can state as fact and which ones he should describe as a hypothesis. So
mark every finding as one of two things:

| Mark | Means | Typical evidence |
|---|---|---|
| **Established** | Strong enough to act on. If you're wrong, you were unlucky, not careless. | The movement is large relative to normal variation, holds across several cohorts or weeks, starts and stops on clean dates, and something in the log matches those dates. |
| **Worth investigating** | The movement is real, but the *cause* or *how long it lasts* isn't nailed down. Needs another source before anyone spends against it. | You can see the change, but the attribution rests on a single log line, or the window is too short or too recent to know whether it persists. |

A worked pair, using a made-up finding so as not to spoil yours:

> *Established* — "WHEN: weeks of 4–25 Feb · WHICH: week-1 retention of new players ·
> MAGNITUDE: +12pp vs the surrounding weeks · CONFIDENCE: established — it holds across all
> four cohorts, starts and ends on clean weeks, and a release in the log lands two days
> before the first one."
>
> *Worth investigating* — "WHEN: December · WHICH: weekly signups · MAGNITUDE: −15% ·
> CONFIDENCE: worth investigating — the drop is real, but December is three weeks long here
> and seasonality would look identical. I'd want last year's December, or the spend data,
> before calling it."

**This distinction is graded as heavily as the findings.** A confident wrong answer scores
below a hedged right one. Marking everything "established" is itself a failure — it tells
Lindqvist nothing about where to look first.

---

## Reference

### The metrics

If your numbers look off, check these first.

- **Week** — starts Saturday, anchored to 2024-01-06 (pandas `W-FRI`). Already baked into
  the data; don't re-bucket it.
- **WAU** — distinct players with a row in the week.
- **Cohort** — signup week = the week a player first appears.
- **New / Retained / Resurrected / Churned**, for week *W*:
  *new* = first appearance is *W* · *retained* = active in *W* and *W−1* ·
  *resurrected* = active in *W*, absent in *W−1*, not new · *churned* = active in *W−1*,
  absent in *W*.
- **NURR** (new user retention rate) — of the cohort that signed up in *W*, the share active
  again in *W+1*. This is week-1 cohort retention.
- **CURR** (current user retention rate) — of players active in *W−1* who were **not** new in
  *W−1*, the share still active in *W*. Excluding last week's newcomers is what makes this a
  statement about *established* players.
- **Quick ratio** — (new + resurrected) / churned. Above 1 the base grows, below 1 it shrinks.

### The charts

| Chart | X axis | Y axis | One point/cell means | Healthy looks like |
|---|---|---|---|---|
| **Retention curve** | weeks since signup (0, 1, 2 …) | % of the cohort still active | at age *N*, this share of signups is still playing | falls steeply, then **flattens** onto a plateau well above zero — a durable core. A curve still heading to zero at the right edge has no core. |
| **Cohort heatmap** | weeks since signup | one row per signup cohort (oldest at top) | of the cohort in this row, the % still active at this age | rows that look alike, fading gently rightward. Read the grey `Users` column first — a bright cell on a tiny cohort is noise. |
| **Lifecycle bars** | calendar week | players, new/retained/resurrected stacked up, churned down | how the active base was composed that week | the *retained* band growing as a share of the bar. If growth is all new + resurrected while retained stays flat, you are refilling a leaky bucket. |
| **Quick ratio line** | calendar week | (new + resurrected) / churned | how many players you gained for each one you lost | steady and comfortably above 1. The 1.0 line is break-even; 4.0 is the often-quoted strong-growth benchmark. |

Two directions worth knowing on the heatmap, because they mean different things: a **vertical
stripe** — one calendar week bad for every cohort regardless of age — points at something
external that hit everyone at once. A **bad row** — one cohort worse than its neighbours at
every age — points at who you acquired that week.
