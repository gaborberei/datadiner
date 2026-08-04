"""The sparse activity matrix — the one structure every figure is derived from.

An activity log is *active-periods-only*: a row exists only where a user did
something, so inactivity is implicit. Retention math needs the opposite — an
explicit zero for every (user, period) pair the user did not show up for. A
sparse matrix over the **complete** period grid is exactly that panel: the
stored entries are the activity, and every unstored cell is a true zero that
costs nothing to keep.

    from retentionkit.io import load_activity
    from retentionkit.matrix import ActivityMatrix

    df = load_activity("activity.csv")
    am = ActivityMatrix.build(df, grain="week", active_event="game_played",
                              segment_cols=["platform"])
    am.density          # how sparse the panel actually is
    mobile = am.where(am.attrs["platform"] == "mobile")   # a row mask, not a rebuild
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import warnings

import numpy as np
import pandas as pd
from scipy import sparse


_FREQ = {"day": "D", "week": "W", "month": "MS"}

_WEEKDAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]

# Which weekday a week starts on. It shifts every cohort boundary, so it is an
# explicit decision rather than an accident of the default. Match the source
# system: a product whose weeks close on Friday wants week_start='SAT'.
DEFAULT_WEEK_START = "MON"


def _week_anchor(week_start):
    """pandas ``W-XXX`` alias whose periods *start* on ``week_start``.

    pandas anchors a weekly period on the day it **ends**, so a week starting
    Monday is ``W-SUN``. Taking the alias at face value is an easy way to shift
    every cohort by a day, which is why the package's parameter names the start
    day and does the translation here.
    """
    day = str(week_start).upper()[:3]
    if day not in _WEEKDAYS:
        raise ValueError(f"week_start must be one of {_WEEKDAYS}, got {week_start!r}")
    return "W-" + _WEEKDAYS[(_WEEKDAYS.index(day) - 1) % 7]


def _period_start(dates, grain, week_start):
    """Map timestamps to the start date of the period each one falls in."""
    if grain == "day":
        return dates.dt.normalize()
    if grain == "month":
        return dates.dt.to_period("M").dt.start_time
    if grain != "week":
        raise ValueError(f"grain must be one of {sorted(_FREQ)}, got {grain!r}")
    return dates.dt.to_period(_week_anchor(week_start)).dt.start_time


def period_axis(dates, grain, week_start=DEFAULT_WEEK_START):
    """Every period between the first and last activity — including empty ones.

    This is the load-bearing detail of the whole package. Factorizing the
    *observed* periods would silently drop a week in which nobody was active,
    and every cohort's ages past that point would shift left by one, dating the
    entire heatmap wrong. A complete calendar axis keeps age == elapsed time.
    """
    starts = _period_start(dates, grain, week_start)
    first, last = starts.min(), starts.max()
    if grain == "week":
        # date_range on a W-XXX freq yields period *end* labels; step in days so
        # the axis carries the same period-start values the rows were mapped to.
        return pd.DatetimeIndex(pd.date_range(first, last, freq="7D"))
    return pd.DatetimeIndex(pd.date_range(first, last, freq=_FREQ[grain]))


def _user_attrs(df, user_codes, n_users, segment_cols):
    """One row per user holding its segment values (first value wins).

    Segments are expected to be user-level (platform, acquisition channel). When
    one varies within a user the first observed value is used and a warning names
    the column, so a per-event dimension can't quietly masquerade as a cohort
    attribute.
    """
    attrs = pd.DataFrame(index=pd.RangeIndex(n_users))
    for col in segment_cols:
        if col not in df.columns:
            raise ValueError(
                f"segment column {col!r} not in the log; found {list(df.columns)}"
            )
        values = df[col].to_numpy()
        out = np.empty(n_users, dtype=object)
        # Reverse order so the *first* row per user is the last one written.
        out[user_codes[::-1]] = values[::-1]
        attrs[col] = out

        first_per_row = out[user_codes]
        differs = pd.Series(values).ne(pd.Series(first_per_row)).to_numpy()
        differs &= ~(pd.isna(values) & pd.isna(first_per_row))  # NaN == NaN here
        if differs.any():
            n = len(np.unique(user_codes[differs]))
            warnings.warn(
                f"segment column {col!r} varies within {n:,} user(s); using each "
                f"user's first value. Segments are treated as user-level."
            )
    return attrs


@dataclass(frozen=True)
class ActivityMatrix:
    """A users x periods activity panel, held sparse.

    Attributes
    ----------
    presence : csr_matrix of int8
        1 where the user was active in the period, implicit 0 everywhere else.
    volume : csr_matrix
        Summed ``event_count`` per (user, period). Carried as data — no figure
        reads it — because it is the intermediate ``presence`` is derived from.
    users : pd.Index
        Row index -> user_id.
    periods : pd.DatetimeIndex
        Column index -> period start. Complete: no calendar gaps.
    cohort : np.ndarray
        Per-user column index of first activity (the signup cohort).
    grain : str
        'day' | 'week' | 'month'.
    week_start : str
        The weekday a week starts on, e.g. 'MON'.
    attrs : pd.DataFrame
        One row per user, aligned with ``presence`` rows, holding segment values.
    """

    presence: sparse.csr_matrix
    volume: sparse.csr_matrix
    users: pd.Index
    periods: pd.DatetimeIndex
    cohort: np.ndarray
    grain: str
    week_start: str
    attrs: pd.DataFrame

    # -- construction -------------------------------------------------------

    @classmethod
    def build(cls, df, grain="week", active_event=None, segment_cols=(),
              count_col="event_count", week_start=DEFAULT_WEEK_START):
        """Build the panel from a daily activity log.

        Parameters
        ----------
        df : DataFrame with 'date' (datetime64) and 'user_id'.
        grain : 'day' | 'week' | 'month' — the period one column spans.
        active_event : optional event_type that counts as "active". Rows of any
            other type are dropped before the panel is built, so retention means
            "did the core action" rather than "showed up".
        segment_cols : columns to carry as user-level attributes for cutting.
        count_col : column holding per-row event volume; ignored when absent.
        week_start : the weekday a week starts on, 'MON'..'SUN' (grain='week'
            only). Match the source system rather than accepting the default.
        """
        for required in ("date", "user_id"):
            if required not in df.columns:
                raise ValueError(
                    f"missing required column {required!r}; found {list(df.columns)}"
                )
        if active_event is not None:
            if "event_type" not in df.columns:
                raise ValueError(
                    "active_event was set but the log has no 'event_type' column"
                )
            df = df[df["event_type"] == active_event]
            if df.empty:
                raise ValueError(f"no rows with event_type == {active_event!r}")

        user_codes, users = pd.factorize(df["user_id"], sort=True)
        n_users = len(users)

        periods = period_axis(df["date"], grain, week_start)
        row_period = _period_start(df["date"], grain, week_start)
        period_codes = periods.get_indexer(row_period)
        if (period_codes < 0).any():
            raise ValueError(
                "some rows fall outside the period axis — check for unparsed dates"
            )

        counts = (
            pd.to_numeric(df[count_col], errors="coerce").fillna(0).to_numpy()
            if count_col and count_col in df.columns
            else np.ones(len(df))
        )
        shape = (n_users, len(periods))
        volume = sparse.coo_matrix(
            (counts, (user_codes, period_codes)), shape=shape
        ).tocsr()
        volume.sum_duplicates()

        presence = volume.copy()
        presence.data = (presence.data > 0).astype(np.int8)
        presence.eliminate_zeros()

        cohort = np.full(n_users, len(periods), dtype=np.int64)
        np.minimum.at(cohort, user_codes, period_codes)

        return cls(
            presence=presence,
            volume=volume,
            users=pd.Index(users, name="user_id"),
            periods=periods,
            cohort=cohort,
            grain=grain,
            week_start=week_start,
            attrs=_user_attrs(df, user_codes, n_users, list(segment_cols)),
        )

    # -- shape --------------------------------------------------------------

    @property
    def n_users(self):
        return self.presence.shape[0]

    @property
    def n_periods(self):
        return self.presence.shape[1]

    @property
    def density(self):
        """Share of (user, period) cells that carry activity.

        The sparsity read: how much of the panel is genuine zero. A low density
        with a weekly grain is the signal to ask whether monthly is the honest
        period for this product.
        """
        cells = self.n_users * self.n_periods
        return float(self.presence.nnz / cells) if cells else float("nan")

    def __repr__(self):
        return (
            f"ActivityMatrix({self.n_users:,} users x {self.n_periods} "
            f"{self.grain}s, density={self.density:.1%}, "
            f"{self.periods[0]:%Y-%m-%d}..{self.periods[-1]:%Y-%m-%d})"
        )

    # -- slicing ------------------------------------------------------------

    def where(self, mask):
        """A new matrix over the subset of users selected by ``mask``.

        Segmenting is a row mask, never a rebuild: a user's cohort is their own
        first active period and does not depend on who else is in the frame, so
        the cohort vector and the period axis carry over untouched. That makes a
        segment cut essentially free once the panel exists — and keeps every cut
        on the *same* calendar axis, so segments are directly comparable.
        """
        mask = np.asarray(mask, dtype=bool)
        if mask.shape != (self.n_users,):
            raise ValueError(
                f"mask must have one entry per user ({self.n_users}), "
                f"got shape {mask.shape}"
            )
        if not mask.any():
            raise ValueError("mask selects no users")
        return replace(
            self,
            presence=self.presence[mask],
            volume=self.volume[mask],
            users=self.users[mask],
            cohort=self.cohort[mask],
            attrs=self.attrs.loc[mask].reset_index(drop=True),
        )

    def segment_masks(self, segment_by):
        """``(label, boolean mask)`` per value of the segment column(s).

        Returned as masks rather than matrices so the *same* mask can be applied
        to several matrices built from the same log — the weekly panel and the
        daily one share a user axis, because both factorize the same user set in
        the same sorted order.

        With ``segment_by=None`` this yields a single ``(None, all-True)`` pass,
        so callers treat the overall and segmented cases identically. Labels read
        ``platform=mobile`` (or ``platform=mobile, channel=paid``).
        """
        cols = _as_list(segment_by)
        if not cols:
            return [(None, np.ones(self.n_users, dtype=bool))]
        missing = [c for c in cols if c not in self.attrs.columns]
        if missing:
            raise ValueError(
                f"segment column(s) {missing} were not carried into the matrix; "
                f"pass them as segment_cols= when building. "
                f"Available: {list(self.attrs.columns)}"
            )
        out = []
        by = cols[0] if len(cols) == 1 else cols  # avoid pandas' 1-tuple key warning
        for key, idx in self.attrs.groupby(by, sort=True).groups.items():
            key = key if isinstance(key, tuple) else (key,)
            label = ", ".join(f"{c}={v}" for c, v in zip(cols, key))
            mask = np.zeros(self.n_users, dtype=bool)
            mask[np.asarray(idx)] = True
            out.append((label, mask))
        return out

    def segments(self, segment_by):
        """``(label, ActivityMatrix)`` per value of the segment column(s)."""
        return [(label, self if label is None else self.where(mask))
                for label, mask in self.segment_masks(segment_by)]

    # -- primitives the metrics build on ------------------------------------

    def active_per_period(self):
        """Distinct active users per period (the WAU/MAU series)."""
        return np.asarray(self.presence.sum(axis=0)).ravel()

    def cohort_sizes(self):
        """Users per signup cohort, indexed by period column."""
        return np.bincount(self.cohort, minlength=self.n_periods)

    def cohort_period_counts(self):
        """Active users per (cohort, calendar period), as a dense array.

        Built with one sparse product: an indicator matrix mapping cohorts to
        users, times the panel. The result is at most n_periods x n_periods
        (about 52x52 for a year of weeks), so it is small enough to go dense
        here even when the panel behind it has millions of rows.
        """
        rows = np.arange(self.n_users)
        indicator = sparse.csr_matrix(
            (np.ones(self.n_users, dtype=np.int64), (self.cohort, rows)),
            shape=(self.n_periods, self.n_users),
        )
        return np.asarray((indicator @ self.presence).todense())

    def cohort_age_counts(self):
        """Active users per (cohort, age), with unobservable cells as NaN.

        Shifts each cohort's calendar row left by its own start so column *a* is
        "a periods after signup" for every cohort. Two kinds of empty cell must
        stay distinguishable past this point:

        - **0** — the cohort was observable at that age and nobody came back.
        - **NaN** — the cohort has not lived that long yet (``cohort + age``
          falls past the end of the data). This is the right-censoring triangle;
          reading it as 0 would drag every young cohort's curve to the floor.
        """
        counts = self.cohort_period_counts().astype(float)
        n = self.n_periods
        aged = np.full((n, n), np.nan)
        for c in range(n):
            width = n - c
            aged[c, :width] = counts[c, c:]
        # A cohort with no members is not "0% retained", it is absent.
        aged[self.cohort_sizes() == 0] = np.nan
        return aged

    def period_labels(self):
        """Period starts as display strings ('2024-01-08' / '2024-01')."""
        fmt = "%Y-%m" if self.grain == "month" else "%Y-%m-%d"
        return [p.strftime(fmt) for p in self.periods]


def _as_list(value):
    """Normalize None | str | sequence to a list of column names."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return list(value)
