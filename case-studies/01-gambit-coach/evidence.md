# Evidence tables — Gambit case

⚠️ **Instructor only.** Computed directly from
`datasets/chess_growth/chess_growth_analyst_daily.csv`, not from the dataset's
`solutions.yaml`. Week 0 = week of 2024-01-01, Monday-start.

Reproduce everything below with the scripts at the bottom.

## Week → date reference

| Week | Starts | Week | Starts |
|---|---|---|---|
| 0 | 2024-01-01 | 31 | 2024-08-05 |
| 9 | 2024-03-04 | 35 | 2024-09-02 |
| 12 | 2024-03-25 | **36** | **2024-09-09** ← v3.0 ships Tue 10 Sep |
| 13 | 2024-04-01 | 37 | 2024-09-16 |
| 17 | 2024-04-29 | 38 | 2024-09-30 |
| 18 | 2024-05-06 | 39 | 2024-10-07 |
| 30 | 2024-07-29 | 51 | 2024-12-23 |

## A. Weekly signups (first active week)

```
wk  0-8 :  264 251 271 289 254 242 253 255 259          (mean ~260)
wk  9-12:  249 267 277 271                              (normal volume)
wk 13-17:  141 139 126 126 116                          ← DIP, ~52% below trend
wk 18-29:  243 237 230 219 237 231 225 223 237 247 258 270
wk 30-39:  315 305 302 300 331 373 383 380 385 431
wk 40-51:  477 513 510 542 569 600 653 673 712 719 739 772   ← acceleration
```

## B. WAU / games / games-per-active

| wk | WAU | games | g/active | WAU Δ% |
|---|---|---|---|---|
| 29 | 1644 | 7033 | 4.28 | +2.5 |
| 30 | 1797 | 8689 | 4.84 | +9.3 |
| 33 | 1897 | 8002 | 4.22 | −1.7 |
| 34 | 1971 | 8538 | 4.33 | +3.9 |
| **35** | **2116** | 9811 | 4.64 | +7.4 |
| **36** | **1533** | 6928 | 4.52 | **−27.6** |
| **37** | **1277** | 5653 | 4.43 | **−16.7** |
| 38 | 1710 | 7183 | 4.20 | +33.9 |
| 39 | 2007 | 9102 | 4.54 | +17.4 |
| 40 | 2242 | 11068 | 4.94 | +11.7 |
| 51 | 4920 | 27742 | 5.64 | +7.2 |

Pre-shock growth rate wk 29-35 ≈ **+5-7 %/wk**. Extrapolating from wk 35:
expected wk 36 ≈ 2 240, wk 37 ≈ 2 380, wk 38 ≈ 2 520.
**Trough (wk 37) is ~46 % below trend.** Cumulative deficit wk 36-38 ≈ **2 600
user-weeks** and **~13 000 games**.

**Games-per-active is flat through the shock** (4.64 → 4.52 → 4.43). The drop is
*fewer players*, not *less play per player*.

### Seasonality (games per active player)

```
Jan (wk 0-3)    4.90 5.22 5.56 …     high
May-Jul (17-29) 3.81-4.12            trough  ← summer
Nov-Dec (44-51) 5.00-5.69            high
```
v3.0 launched in **September, while seasonality was rising**. Seasonality therefore
cannot explain the September drop — it works *against* it.

## C. NURR — week-1 retention by **signup cohort** (%)

```
cohort  0-8 : 46.2 39.0 43.9 44.6 42.9 39.3 42.7 38.8 45.6    baseline ~42%
cohort 9-12 : 12.0  8.6 11.2 10.0                             ← COLLAPSE (−75% rel.)
cohort13-17 : 51.1 41.7 41.3 47.6 44.0                        normal (low volume)
cohort18-30 : 50.2 62.4 55.7 65.3 57.0 55.0 57.3 52.0 54.0 53.4 51.6 61.5 59.4  ← ELEVATED
cohort31-34 : 41.6 40.4 41.3 45.3                             back to baseline
cohort35-36 : 25.7 21.9                                       ← v3.0 shock hits new users too
cohort37-50 : 38.7 41.3 44.5 42.3 43.9 38.8 42.3 43.8 45.7 45.0 45.3 41.7 42.1 43.8
```

## D. NURR by cohort band × acquisition channel (%) — **the trap**

| band | organic | paid_search | referral | social |
|---|---|---|---|---|
| wk 0-8 | 45.3 | 34.8 | 56.8 | 39.0 |
| **wk 9-12** | **10.8** | **9.1** | **13.6** | **9.8** |
| wk 13-17 | 47.6 | 40.1 | 54.4 | 42.9 |
| wk 18-30 | 60.3 | 49.4 | 68.0 | 50.7 |
| wk 31-51 | 41.0 | 32.8 | 47.3 | 34.7 |

**All four channels collapse together in wk 9-12.** The "we bought bad traffic"
hypothesis is falsified by this table. Channel *ranking* is stable all year:
`referral > organic > social ≈ paid_search`.

Signup counts wk 9-12: organic 499 · paid_search 219 · referral 81 · social 265 —
no meaningful mix shift either.

## E. CURR — week-over-week retention of **established** players (%)

*(active in week w and not new that week → active in w+1)*

```
wk  2-20 : 76.2 75.1 70.2 60.8 70.1 64.6 67.5 65.1 67.6 69.3 62.5 66.5 62.5 62.5
           63.4 61.6 64.8 65.0 64.8          → ~62-66% band
wk 21-35 : 62.5 65.5 67.8 64.6 64.1 66.0 67.1 68.2 66.0 69.4 68.2 70.2 66.6 67.7 69.0
                                             → ~66-70% band
wk 36-37 : 42.1 41.7                         ← COLLAPSE, ~26 pts below trend
wk 38-40 : 61.9 58.6 61.2                    recovery
wk 41-51 : 66.0 67.3 69.2 68.9 70.4 70.5 72.3 73.1 72.4 73.8 74.3
                                             → ~70-74% band
```

**Drift: ~64% → ~73% across the year, ≈ +9 points**, monotone once the wk 36-37
shock is excluded.

## Reproduction

```bash
# A, B — signups, WAU, games
PYTHONPATH=. python3 - <<'PY'
import pandas as pd
from datadiner.io import load_events
df = load_events("datasets/chess_growth/chess_growth_analyst_daily.csv")
d = df[df.event_type=="game_played"].copy()
d["wk"] = ((d["date"]-pd.Timestamp("2024-01-01")).dt.days//7).astype(int)
first = d.groupby("user_id")["wk"].min()
print(first.value_counts().sort_index().to_string())
o = pd.DataFrame({"WAU":d.groupby("wk")["user_id"].nunique(),
                  "games":d.groupby("wk")["event_count"].sum()})
o["gpa"]=(o.games/o.WAU).round(2); o["chg"]=(o.WAU.pct_change()*100).round(1)
print(o.to_string())
PY

# C, E — NURR by cohort, CURR by week
PYTHONPATH=. python3 - <<'PY'
import pandas as pd
from datadiner.io import load_events
df = load_events("datasets/chess_growth/chess_growth_analyst_daily.csv")
d = df[df.event_type=="game_played"].copy()
d["wk"] = ((d["date"]-pd.Timestamp("2024-01-01")).dt.days//7).astype(int)
first = d.groupby("user_id")["wk"].min().rename("cohort")
act = d[["user_id","wk"]].drop_duplicates().join(first, on="user_id")
act["age"] = act.wk - act.cohort
size = first.value_counts()
print((act[act.age==1].groupby("cohort")["user_id"].nunique()/size*100).round(1).to_string())
s = set(zip(act.user_id, act.wk))
for w in range(0,51):
    prev = act[(act.wk==w)&(act.cohort<w)]
    if len(prev): print(w+1, round(sum((u,w+1) in s for u in prev.user_id)/len(prev)*100,1))
PY
```
