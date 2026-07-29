# Case study — "Is the board still growing?"

*Companion exercise to article #6 — how to actually read retention curves, lifecycle
charts and cohorts · full-year 2024 · beginner–intermediate · budget 60 minutes*

---

## The situation

You have just joined a **chess platform** as its first analyst. Players sign up,
get matched, and play rated games. That is the entire product.

The company grew fast through 2024 and ended the year with **124,333 players** who
played at least one game. Nobody has ever looked at retention properly. The weekly
report has exactly one number on it — *active players* — and it went up almost every
week, so nobody asked further questions.

Your manager is preparing next year's plan and sends you this:

> Our active-player number tripled this year and I've been telling everyone we're
> in great shape. Before I put that in the plan I want someone to actually look.
>
> Three things. **Is the product healthy** — do people stick, or are we just
> refilling a leaky bucket? **Did anything happen** during the year that we missed
> because we only ever looked at one number? And **is the underlying trend getting
> better or worse**, separately from any one-off events?
>
> Nobody has named anything for you. I don't know what's in there either.

---

## The data

`../../datasets/chess_dot_com_article/chess_dot_com_retention_article.csv`

3,589,248 rows · 124,333 players · **2024-01-06 → 2025-01-03**

Two columns. That is all you get.

| Column | Meaning |
|---|---|
| `date` | Calendar day |
| `user_id` | Stable player identifier |

**Read the grain carefully — it decides what you can and cannot claim:**

- **One row = that player played at least one game that day.** Activity is
  *presence*, nothing more. A player who played one game and a player who played
  twenty produce the identical row.
- **There are no game counts**, so you cannot separate "fewer players" from "less
  play per player." Any movement in activity *is* a movement in player count.
- **There are no segments** — no channel, country, or platform. You cannot cut this
  by anything except time and cohort.
- **A player appears on a day only if they were active.** A missing row means no
  activity, not missing data.
- **First observed date = signup day.**

A missed *day* is not churn on a product like this. Build the lifecycle on **weeks**.

⚠️ *This is a synthetic dataset modelled on a chess platform. The numbers are
generated, not a real company's reported figures.*

---

## Your questions

**Q1 — Is this product healthy?**
Use the retention curve and the lifecycle / Quick Ratio view. Where does the curve
stop falling, and what does that level tell you? Is the company growing on the
strength of the product, or on the strength of acquisition? Give the number you are
relying on.

**Q2 — What happened during the year?**
Find every anomaly you can defend. For each one: **WHEN**, **WHICH** metric moved,
**MAGNITUDE**, whether it hit **new players, established players, or both**, and
whether it was **temporary or permanent**. The number of events is not given — there
may be one, there may be several.

**Q3 — What is the underlying trend?**
Separately from the one-offs: is retention improving or degrading across the year,
and by how much? Then check your own answer — **is every movement you can see in
this data a real movement?** Say which of your findings you would bet on and which
you would want to verify first.

---

## What you hand in

**Five lines to your manager**, answer first. Then a short appendix listing each
finding as:

> **WHEN** · **WHICH** metric · **MAGNITUDE** · **CONFIDENCE** — would you bet on it?

Mark anything you consider *worth investigating* rather than established. You are
graded on that distinction as much as on the findings.
