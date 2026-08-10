```
┌─────────────────────────────────────────────────┐
│                                                 │
│  ███  ████ ████ ████ █  █ ████ ███  ██  █  █    │
│  █  █ █     ██  █    ██ █  ██   █  █  █ ██ █    │
│  ███  ███   ██  ███  █ ██  ██   █  █  █ █ ██    │
│  █ █  █     ██  █    █  █  ██   █  █  █ █  █    │
│  █  █ ████  ██  ████ █  █  ██  ███  ██  █  █    │
│                                                 │
│  █  █ ███ ████                                  │
│  █ █   █   ██                                   │
│  ██    █   ██                                   │
│  █ █   █   ██                                   │
│  █  █ ███  ██                                   │
│                                                 │
│                       b y   D a t a d i n e r   │
│                                                 │
└─────────────────────────────────────────────────┘
```

# retentionkit

A minimal retention analyst for **daily-aggregated activity logs**. Point it at a
CSV, answer four questions, get the figures.

```
date, user_id, event_type, event_count, <segment columns...>
```

Only `date` and `user_id` are required.

## Install

```bash
pip install -e .
```

## Use it

```python
from retentionkit import load_activity
from retentionkit.report import run_report

df = load_activity("datasets/mydata/activity.csv")
run_report(df, dataset="mydata", grain="week", active_event="game_played",
           segment_cols=["platform"])
# -> output/mydata/<timestamp>/  report.md + charts/ + data/
```

Or drive the pieces:

```python
from retentionkit.matrix import ActivityMatrix
from retentionkit import metrics, plots

am = ActivityMatrix.build(df, grain="week", active_event="game_played")
fig = plots.cohort_heatmap(metrics.cohort_table(am, kind="retention_rate"), kind="retention_rate")

mobile = am.where(am.attrs["platform"] == "mobile")   # a row mask, not a rebuild
```

## The data you need

Everything is derived from a single **sparse users × periods panel**. An activity
log is active-periods-only — a row exists only where someone did something — but
retention math needs the opposite: an explicit zero for every period a user
*didn't* show up. A sparse matrix over the complete calendar grid is exactly that
panel, and it costs nothing to store the zeros because they aren't stored.

Three things follow, and they're the whole design:

- **The period axis is complete.** Weeks where nobody was active still get a
  column. Build the axis from observed periods instead and every age past a quiet
  week shifts left by one, dating the entire heatmap wrong.
- **Zero ≠ unobservable.** `0` means the user was around and did nothing. `NaN`
  means the cohort hasn't lived that long yet. Collapsing the two drags every
  young cohort's curve to the floor.
- **Segmenting is a row mask.** A user's cohort is their own first active period,
  so it survives subsetting. Cutting by platform doesn't rebuild anything.

On a 3.8 M-row / 129 k-user log the panel builds in about a second, and the full
figure set writes in under ten.

## The figures

| Figure | What it answers |
|---|---|
| Usage frequency | How often does a user show up? Frames what "active" should mean. |
| Retention curve | How fast does the average cohort decay, and where does it flatten? |
| Cohort heatmaps ×5 | rate · counts · churn rate · churn counts · vs average |
| Lifecycle + Quick Ratio | New / Retained / Resurrected / At-Risk / Churned, and whether the base grows on net |

Every figure takes `segment_by=`, and every figure ships with the CSV behind it —
no number is reachable only through a picture.

## Conventions

- **Retention is weekly or monthly**, whatever the input grain. Daily retention on
  a daily log measures noise.
- **The period follows the natural frequency.** `quality_report()` measures the
  median gap between a user's active days and warns when `grain` fights it — a
  period shorter than the rhythm manufactures churn, a longer one hides it.
- **`week_start` is a decision**, not a default to accept. Note that pandas' `W-XXX`
  aliases name the day a week *ends*; this package's parameter names the start.
- **One churn definition**: At-Risk after one missed period, Churned after a
  second. Churn isn't final — returners are Resurrected.
- **No dataset contract.** The four answers live in a ten-line `analysis.yaml`
  next to the CSV. Nothing validates against it; nothing fails a gate.

## Tests

```bash
python -m pytest tests -q
```

The load-bearing one asserts the sparse cohort table matches an independently
written pandas implementation, cell for cell — including which cells are `0` and
which are `NaN`.
