"""Assign per-user `platform` and `acquisition_channel` columns to the weekly CSV.

One-off, seeded provenance script for the two synthetic signup attributes.
Labels are drawn conditioned on each user's *observed* engagement tier, so the
segment cuts carry a realistic (~2-3x) tilt without altering any behavior:
rows, users, and the [date, user_id, event_type] primary key are unchanged.

Rerunning is safe: the tiers are computed from the four base columns only, and
any previously assigned label columns are dropped first.
"""

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
CSV = Path(__file__).parent / "chess_dot_com_retention_article_weekly.csv"
LABEL_COLS = ["platform", "acquisition_channel"]

# tier -> platform -> probability
PLATFORM_MIX = {
    "power": {"mobile": 0.85, "desktop": 0.15},
    "regular_light": {"mobile": 0.30, "desktop": 0.70},
    "casual": {"mobile": 0.75, "desktop": 0.25},
}

# (tier, platform) -> channel -> probability; None platform = any
CHANNEL_MIX = {
    ("power", None): {"organic": 0.60, "social": 0.25, "paid": 0.15},
    ("regular_light", None): {"paid": 0.45, "organic": 0.45, "social": 0.10},
    ("casual", "desktop"): {"paid": 0.45, "organic": 0.40, "social": 0.15},
    ("casual", "mobile"): {"paid": 0.40, "social": 0.38, "organic": 0.22},
}


def tier_users(df: pd.DataFrame) -> pd.DataFrame:
    per_user = df.groupby("user_id").agg(
        weeks_active=("date", "nunique"), mean_days=("event_count", "mean")
    )
    per_user["tier"] = "casual"
    per_user.loc[
        (per_user.weeks_active >= 12) & (per_user.mean_days <= 2.5), "tier"
    ] = "regular_light"
    per_user.loc[per_user.mean_days >= 5, "tier"] = "power"
    return per_user


def draw(rng: np.random.Generator, index: pd.Index, mix: dict[str, float]) -> pd.Series:
    values = list(mix)
    probs = np.array([mix[v] for v in values])
    return pd.Series(rng.choice(values, size=len(index), p=probs / probs.sum()), index=index)


def main() -> None:
    df = pd.read_csv(CSV, parse_dates=["date"])
    df = df.drop(columns=[c for c in LABEL_COLS if c in df.columns])
    per_user = tier_users(df)

    rng = np.random.default_rng(SEED)
    per_user["platform"] = ""
    per_user["acquisition_channel"] = ""
    for tier, mix in PLATFORM_MIX.items():
        idx = per_user.index[per_user.tier == tier]
        per_user.loc[idx, "platform"] = draw(rng, idx, mix)
    for (tier, platform), mix in CHANNEL_MIX.items():
        mask = per_user.tier == tier
        if platform is not None:
            mask &= per_user.platform == platform
        idx = per_user.index[mask]
        per_user.loc[idx, "acquisition_channel"] = draw(rng, idx, mix)

    out = df.merge(per_user[LABEL_COLS], left_on="user_id", right_index=True, how="left")
    assert len(out) == len(df) and not out[LABEL_COLS].isna().any().any()
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    out.to_csv(CSV, index=False)

    print(f"wrote {len(out):,} rows, {out.user_id.nunique():,} users -> {CSV.name}")
    print("\ntier sizes:\n", per_user.tier.value_counts().to_string())
    print("\nplatform mix:\n", per_user.platform.value_counts(normalize=True).round(3).to_string())
    print("\nchannel mix:\n", per_user.acquisition_channel.value_counts(normalize=True).round(3).to_string())
    print(
        "\nengagement by segment (mean weeks_active / mean_days):\n",
        per_user.groupby(["platform", "acquisition_channel"])
        .agg(users=("tier", "size"), weeks=("weeks_active", "mean"), days=("mean_days", "mean"))
        .round(2)
        .to_string(),
    )


if __name__ == "__main__":
    main()
