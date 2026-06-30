"""
DataDiner — Retention module
============================
Reusable product analytics functions for retention, churn, and lifecycle analysis.
Part of the `datadiner` package; works on any event log with `date` + `user_id`.

Usage:
    from datadiner.io import load_events
    from datadiner.retention import retention_rate_heatmap, lifecycle_states

    df = load_events('your_data.csv')
    fig, ax = retention_rate_heatmap(df, granularity='weekly')
    states_df, figs = lifecycle_states(df)
"""

import warnings
from contextlib import contextmanager

import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt


# Readability guard: above this many segment groups, overlaid lines / panels
# stop being legible, so warn (the skill should ask the user to narrow down).
_MAX_SEGMENT_GROUPS = 30


# A single interactive view pops a window (plt.show); batch callers that bundle
# many views (report.py) turn this off so they don't flood the screen.
_SHOW_FIGURES = True


def _maybe_show():
    """``plt.show()`` only when figure display is enabled (see ``no_figure_display``)."""
    if _SHOW_FIGURES:
        plt.show()


@contextmanager
def no_figure_display():
    """Suppress ``plt.show()`` for views called inside this block.

    Used by the report bundler so generating a run writes PNGs without opening a
    window per view. Restores the previous setting on exit (re-entrant-safe).
    """
    global _SHOW_FIGURES
    prev = _SHOW_FIGURES
    _SHOW_FIGURES = False
    try:
        yield
    finally:
        _SHOW_FIGURES = prev


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _segment_cols(segment_by):
    """Normalize segment_by (None | str | list) to a list of column names."""
    if segment_by is None:
        return []
    return [segment_by] if isinstance(segment_by, str) else list(segment_by)


def _segment_name(segment_by):
    """Human label for the segment dimension(s), e.g. 'country, platform'."""
    return ", ".join(_segment_cols(segment_by))


def _segment_values(df, segment_by):
    """Yield (label, sub_df) pairs to run a view over.

    With segment_by=None this is a single (None, df) pass — the un-segmented
    behaviour. A single column splits on its values; a list of columns splits on
    the cross-tab of their value combinations. `label` is a ready display string
    like 'country=US, platform=web' (or None when not segmenting).
    """
    cols = _segment_cols(segment_by)
    if not cols:
        return [(None, df)]
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(
            f"segment_by column(s) {missing} not in {list(df.columns)}; "
            f"pass column(s) from the dataset brief's analysis.segment_cols"
        )
    groups = []
    for key, sub in df.groupby(cols, sort=True):
        key = key if isinstance(key, tuple) else (key,)
        label = ", ".join(f"{c}={v}" for c, v in zip(cols, key))
        groups.append((label, sub))
    if len(groups) > _MAX_SEGMENT_GROUPS:
        warnings.warn(
            f"{len(groups)} segment groups for {cols}; this is hard to read — "
            f"consider fewer columns or specific values."
        )
    return groups


def _filter_active(df, active_event):
    """Restrict to rows of the core action, so 'active' = did that event.

    With active_event=None the frame is returned unchanged (any row = active).
    """
    if active_event is None:
        return df
    if "event_type" not in df.columns:
        raise ValueError(
            "active_event was set but there is no 'event_type' column to filter on"
        )
    out = df[df["event_type"] == active_event]
    if out.empty:
        raise ValueError(
            f"no rows with event_type == {active_event!r}; "
            f"present types: {sorted(df['event_type'].unique())[:10]}"
        )
    return out


def _prepare_cohorts(df, granularity='weekly'):
    """Assign cohorts and compute active users per cohort per period."""
    df = df.copy()
    granularity = granularity.rstrip('ly')  # normalize: weekly->week, monthly->month

    if granularity == 'week':
        df['period'] = df['date'].dt.to_period('W').dt.start_time
        period_col = 'cohort_period'
        first = df.groupby('user_id')['period'].min().reset_index()
        first.columns = ['user_id', period_col]
        df = df.merge(first, on='user_id')

        cohort_data = (
            df.groupby([period_col, 'period'])['user_id']
            .nunique()
            .reset_index()
            .rename(columns={'user_id': 'active_users'})
        )
        cohort_data['periods_since_signup'] = (
            (cohort_data['period'] - cohort_data[period_col]).dt.days / 7
        ).astype(int)
        max_periods = 20
        fmt_index = lambda idx: idx.strftime('%Y-%m-%d')

    else:  # monthly
        df['period'] = df['date'].dt.to_period('M')
        period_col = 'cohort_period'
        first = df.groupby('user_id')['period'].min().reset_index()
        first.columns = ['user_id', period_col]
        df = df.merge(first, on='user_id')

        cohort_data = (
            df.groupby([period_col, 'period'])['user_id']
            .nunique()
            .reset_index()
            .rename(columns={'user_id': 'active_users'})
        )
        cohort_data['periods_since_signup'] = (
            cohort_data['period'] - cohort_data[period_col]
        ).apply(lambda x: x.n)
        max_periods = 12
        fmt_index = lambda idx: idx.astype(str)

    cohort_sizes = (
        cohort_data[cohort_data['periods_since_signup'] == 0]
        [[period_col, 'active_users']]
        .rename(columns={'active_users': 'cohort_size'})
    )
    cohort_data = cohort_data.merge(cohort_sizes, on=period_col)
    cohort_data['retention_pct'] = (
        cohort_data['active_users'] / cohort_data['cohort_size'] * 100
    )

    return cohort_data, cohort_sizes, period_col, max_periods, fmt_index


def _build_pivot(cohort_data, cohort_sizes, period_col, max_periods, fmt_index, values):
    """Build a pivot table with a grey 'Users' column prepended."""
    pivot = cohort_data.pivot_table(
        index=period_col, columns='periods_since_signup', values=values
    )
    pivot = pivot.loc[:, pivot.columns <= max_periods]

    sizes_indexed = cohort_sizes.set_index(period_col)['cohort_size']
    pivot.insert(0, 'Users', sizes_indexed)
    pivot.index = fmt_index(pivot.index)
    return pivot


def _plot_heatmap(pivot, title, annotation_fmt, figsize, save=None):
    """Render a column-normalized RdYlGn heatmap with grey 'Users' column."""
    cmap = sns.color_palette("RdYlGn", as_cmap=True)
    fig, ax = plt.subplots(figsize=figsize)

    # Column-normalize for coloring
    colored = np.zeros_like(pivot.values)
    for col_idx in range(pivot.shape[1]):
        col_vals = pivot.iloc[:, col_idx].values
        valid = ~np.isnan(col_vals)
        if valid.any():
            col_min = np.nanmin(col_vals)
            col_max = np.nanmax(col_vals)
            if col_max > col_min:
                colored[valid, col_idx] = (
                    (col_vals[valid] - col_min) / (col_max - col_min)
                )
            else:
                colored[valid, col_idx] = 0.5
        colored[~valid, col_idx] = np.nan

    sns.heatmap(
        colored, cmap=cmap, vmin=0, vmax=1,
        linewidths=0.5, linecolor='white', ax=ax,
        cbar=False, mask=np.isnan(pivot.values),
        xticklabels=pivot.columns, yticklabels=pivot.index,
    )
    # Compact tick labels so all cohort dates fit a screen without overflowing.
    ax.tick_params(labelsize=6)
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0)

    # Grey "Users" column
    for i in range(pivot.shape[0]):
        val = pivot.iloc[i, 0]
        if not np.isnan(val):
            ax.add_patch(plt.Rectangle(
                (0, i), 1, 1, fill=True, color='#e8e8e8', ec='white', lw=0.5
            ))

    # Annotate cells
    is_diverging = annotation_fmt in ('signed_int', 'signed_pp')
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            val = pivot.iloc[i, j]
            if np.isnan(val):
                continue
            if j == 0:  # Users column
                ax.text(j + 0.5, i + 0.5, f'{int(val):,}',
                        ha='center', va='center', fontsize=5,
                        color='black', fontweight='bold')
            else:
                color_val = colored[i, j]
                if is_diverging:
                    text_color = (
                        'white' if color_val > 0.85 or color_val < 0.15
                        else 'black'
                    )
                else:
                    text_color = 'white' if color_val > 0.6 else 'black'

                if annotation_fmt == 'pct':
                    label = f'{val:.1f}%'
                elif annotation_fmt == 'int':
                    label = f'{int(val):,}'
                elif annotation_fmt == 'signed_int':
                    label = f'{int(val):+,}'
                elif annotation_fmt == 'signed_pp':
                    label = f'{val:+.1f}pp'
                else:
                    label = f'{val:.1f}'

                ax.text(j + 0.5, i + 0.5, label,
                        ha='center', va='center', fontsize=5,
                        color=text_color)

    ax.set_title(title, fontsize=13, fontweight='bold')

    plt.tight_layout()
    if save:
        plt.savefig(save, dpi=150, bbox_inches='tight')
    _maybe_show()

    return fig, ax


def _safe_label(label):
    """Filesystem-safe version of a segment label, e.g. 'country=US' -> 'country-US'."""
    return label.replace('=', '-').replace(', ', '_').replace(' ', '_')


def _seg_save(save, label):
    """Insert the segment label into a save filename so panels don't collide."""
    if not save or label is None:
        return save
    from pathlib import Path
    p = Path(save)
    return str(p.with_name(f"{p.stem}_{_safe_label(label)}{p.suffix}"))


def _cohort_heatmap(df, granularity, segment_by, active_event, save,
                    transform, title_fn, annotation_fmt):
    """Shared driver for the five cohort heatmaps.

    `transform(cohort_data, sizes, pcol, maxp, fmt) -> pivot` builds the view's
    pivot; `title_fn(granularity) -> str` builds its title. With segment_by set,
    renders one heatmap per segment value (or value-combination) and returns a
    list of (label, fig, ax); otherwise returns a single (fig, ax).
    """
    df = _filter_active(df, active_event)
    results = []
    for label, sub in _segment_values(df, segment_by):
        cohort_data, sizes, pcol, maxp, fmt = _prepare_cohorts(sub, granularity)
        pivot = transform(cohort_data, sizes, pcol, maxp, fmt)

        period_label = 'Weeks' if granularity in ('week', 'weekly') else 'Months'
        figsize = (13, 8) if granularity in ('week', 'weekly') else (11, 6)
        suffix = '' if label is None else f' — {label}'

        fig, ax = _plot_heatmap(
            pivot, title_fn(granularity) + suffix, annotation_fmt,
            figsize, _seg_save(save, label),
        )
        ax.set_xlabel(f'{period_label} Since Signup')
        ax.set_ylabel(f'Cohort {period_label[:-1]}')

        if label is None:
            return fig, ax
        results.append((label, fig, ax))
    return results


def _period_label(granularity):
    return 'Weeks' if granularity in ('week', 'weekly') else 'Months'


def _period_prefix(granularity):
    return '' if granularity in ('week', 'weekly') else 'Monthly '


def _diff_pivot(pivot):
    """Period-over-period diff of a pivot, preserving the grey Users column."""
    users_col = pivot['Users']
    diff = pivot.drop(columns='Users').diff(axis=1).iloc[:, 1:]
    diff.insert(0, 'Users', users_col)
    return diff


# ---------------------------------------------------------------------------
# Public API — Cohort Heatmaps
# ---------------------------------------------------------------------------

def retention_counts_heatmap(df, granularity='weekly', segment_by=None, active_event=None, save=None):
    """
    Cohort heatmap showing raw active user counts per period.

    Parameters
    ----------
    df : DataFrame with 'date' and 'user_id' columns
    granularity : 'weekly' or 'monthly'
    segment_by : optional column or list of columns to split on; renders one
        heatmap per value (or value-combination)
    active_event : optional event_type to count as 'active' (e.g. the brief's
        core_action); defaults to counting any row
    save : optional filename to save the figure (e.g. 'retention_counts.png')

    Returns
    -------
    fig, ax — or, when segment_by is set, a list of (label, fig, ax)
    """
    return _cohort_heatmap(
        df, granularity, segment_by, active_event, save,
        transform=lambda cd, s, p, m, f: _build_pivot(cd, s, p, m, f, 'active_users'),
        title_fn=lambda g: f'Cohort Retention Counts — Active Users per {_period_label(g)[:-1]}',
        annotation_fmt='int',
    )


def retention_rate_heatmap(df, granularity='weekly', segment_by=None, active_event=None, save=None):
    """
    Cohort heatmap showing % of each cohort still active.

    Parameters
    ----------
    df : DataFrame with 'date' and 'user_id' columns
    granularity : 'weekly' or 'monthly'
    segment_by : optional column or list of columns to split on; renders one
        heatmap per value (or value-combination)
    active_event : optional event_type to count as 'active' (e.g. the brief's
        core_action); defaults to counting any row
    save : optional filename to save the figure

    Returns
    -------
    fig, ax — or, when segment_by is set, a list of (label, fig, ax)
    """
    return _cohort_heatmap(
        df, granularity, segment_by, active_event, save,
        transform=lambda cd, s, p, m, f: _build_pivot(cd, s, p, m, f, 'retention_pct'),
        title_fn=lambda g: f'{_period_prefix(g)}Cohort Retention Rate — % Still Active (colored per column)',
        annotation_fmt='pct',
    )


def churn_counts_heatmap(df, granularity='weekly', segment_by=None, active_event=None, save=None):
    """
    Cohort heatmap showing users lost per period (period-over-period diff).

    Parameters
    ----------
    df : DataFrame with 'date' and 'user_id' columns
    granularity : 'weekly' or 'monthly'
    segment_by : optional column or list of columns to split on; renders one
        heatmap per value (or value-combination)
    active_event : optional event_type to count as 'active' (e.g. the brief's
        core_action); defaults to counting any row
    save : optional filename to save the figure

    Returns
    -------
    fig, ax — or, when segment_by is set, a list of (label, fig, ax)
    """
    return _cohort_heatmap(
        df, granularity, segment_by, active_event, save,
        transform=lambda cd, s, p, m, f: _diff_pivot(_build_pivot(cd, s, p, m, f, 'active_users')),
        title_fn=lambda g: f'{_period_prefix(g)}Cohort Churn Counts — Users Lost per {_period_label(g)[:-1]}',
        annotation_fmt='signed_int',
    )


def churn_rate_heatmap(df, granularity='weekly', segment_by=None, active_event=None, save=None):
    """
    Cohort heatmap showing pp change in retention rate per period.

    Parameters
    ----------
    df : DataFrame with 'date' and 'user_id' columns
    granularity : 'weekly' or 'monthly'
    segment_by : optional column or list of columns to split on; renders one
        heatmap per value (or value-combination)
    active_event : optional event_type to count as 'active' (e.g. the brief's
        core_action); defaults to counting any row
    save : optional filename to save the figure

    Returns
    -------
    fig, ax — or, when segment_by is set, a list of (label, fig, ax)
    """
    def _title(g):
        pl = _period_label(g)[:-1]
        return f'{_period_prefix(g)}Cohort Churn Rate — pp Change in Retention {pl}-over-{pl}'

    return _cohort_heatmap(
        df, granularity, segment_by, active_event, save,
        transform=lambda cd, s, p, m, f: _diff_pivot(_build_pivot(cd, s, p, m, f, 'retention_pct')),
        title_fn=_title,
        annotation_fmt='signed_pp',
    )


def vs_average_heatmap(df, granularity='weekly', segment_by=None, active_event=None, save=None):
    """
    Cohort heatmap showing each cohort's deviation from average retention.

    Parameters
    ----------
    df : DataFrame with 'date' and 'user_id' columns
    granularity : 'weekly' or 'monthly'
    segment_by : optional column or list of columns to split on; renders one
        heatmap per value (or value-combination)
    active_event : optional event_type to count as 'active' (e.g. the brief's
        core_action); defaults to counting any row
    save : optional filename to save the figure

    Returns
    -------
    fig, ax — or, when segment_by is set, a list of (label, fig, ax)
    """
    def _title(g):
        tail = f' per {_period_label(g)[:-1]}' if g in ('week', 'weekly') else ''
        return f'{_period_prefix(g)}Cohort vs Average — Deviation from Average Retention{tail}'

    return _cohort_heatmap(
        df, granularity, segment_by, active_event, save,
        transform=_vs_average_pivot, title_fn=_title, annotation_fmt='signed_pp',
    )


# ---------------------------------------------------------------------------
# Public API — Cohort matrix (data only, for export)
# ---------------------------------------------------------------------------

def _vs_average_pivot(cohort_data, sizes, pcol, maxp, fmt):
    """Deviation-from-average pivot (same transform as vs_average_heatmap)."""
    pivot = _build_pivot(cohort_data, sizes, pcol, maxp, fmt, 'retention_pct')
    users_col = pivot['Users']
    data_cols = pivot.drop(columns='Users')
    deviation = data_cols.subtract(data_cols.mean(axis=0), axis=1)
    deviation.insert(0, 'Users', users_col)
    return deviation


# Maps a `kind` to the transform that builds its pivot. These mirror exactly the
# transforms the five heatmap functions use, so the CSV matches the chart.
_MATRIX_TRANSFORMS = {
    'counts': lambda cd, s, p, m, f: _build_pivot(cd, s, p, m, f, 'active_users'),
    'rate': lambda cd, s, p, m, f: _build_pivot(cd, s, p, m, f, 'retention_pct'),
    'churn_counts': lambda cd, s, p, m, f: _diff_pivot(
        _build_pivot(cd, s, p, m, f, 'active_users')),
    'churn_rate': lambda cd, s, p, m, f: _diff_pivot(
        _build_pivot(cd, s, p, m, f, 'retention_pct')),
    'vs_average': _vs_average_pivot,
}


def cohort_matrix(df, granularity='weekly', kind='rate', segment_by=None,
                  active_event=None):
    """Return the cohort pivot table behind a heatmap, as data (no chart).

    The five `*_heatmap` views return only `fig, ax`; use this to get the same
    numbers as a DataFrame for export or inspection. The pivot has the cohort
    period as the index, a leading grey-column-equivalent `Users` (cohort size),
    and one column per period-since-signup.

    Parameters
    ----------
    df : DataFrame with 'date' and 'user_id' columns
    granularity : 'weekly' or 'monthly'
    kind : 'rate' | 'counts' | 'churn_rate' | 'churn_counts' | 'vs_average'
        Which heatmap's matrix to build (matches the same-named view).
    segment_by : optional column or list of columns to split on
    active_event : optional event_type to count as 'active'

    Returns
    -------
    DataFrame — or, when segment_by is set, a list of (label, DataFrame).
    """
    if kind not in _MATRIX_TRANSFORMS:
        raise ValueError(
            f"kind must be one of {sorted(_MATRIX_TRANSFORMS)}, got {kind!r}"
        )
    transform = _MATRIX_TRANSFORMS[kind]
    df = _filter_active(df, active_event)
    results = []
    for label, sub in _segment_values(df, segment_by):
        cohort_data, sizes, pcol, maxp, fmt = _prepare_cohorts(sub, granularity)
        pivot = transform(cohort_data, sizes, pcol, maxp, fmt)
        if label is None:
            return pivot
        results.append((label, pivot))
    return results


# Below this many contributing cohorts, a calendar-period signal is too thin to
# call "simultaneous across cohorts" — so the diagonal scan ignores it.
_MIN_DIAGONAL_COHORTS = 3


def cohort_patterns(df, granularity='weekly', active_event=None, top=3):
    """Surface the strongest read-the-heatmap signals, as data (no chart).

    A reading aid for the three cohort lenses — it points at *where* the matrix
    moves so an analyst (or the tutor) can ask "what happened here?". It does not
    conclude a cause.

    Returns a dict with three lists, each sorted strongest-first, of
    ``{'where', 'magnitude', ..., 'lens_hint'}``:

    - ``horizontal`` — a **cohort** that beats/lags its peers on average (pp vs the
      same-age average), with its ``size``. A small cohort that retains strongly is
      the "low volume, high quality" signature (e.g. a leaner acquisition push).
    - ``diagonal`` — a **calendar period** where many cohorts move together (mean pp
      deviation across the anti-diagonal); the signature of a simultaneous,
      all-cohort event (feature launch, bug, outage).
    - ``vertical`` — a **tenure age** with an unusually steep cross-cohort drop above
      the smooth decay (``excess`` pp); the survival-moment signature (trial end,
      renewal).

    Parameters
    ----------
    df : DataFrame with 'date' and 'user_id' columns
    granularity : 'weekly' or 'monthly'
    active_event : optional event_type to count as 'active'
    top : how many signals to return per lens
    """
    dev = cohort_matrix(df, granularity, 'vs_average', active_event=active_event)
    rate = cohort_matrix(df, granularity, 'rate', active_event=active_event)
    ages = [c for c in dev.columns if c != 'Users']
    index_labels = list(dev.index)

    # --- Horizontal: per-cohort average deviation from its same-age peers ---
    row_dev = dev[ages].mean(axis=1)
    global_mean = row_dev.mean()
    sizes = dev['Users']
    size_median = sizes.median()
    horizontal = []
    for label in index_labels:
        mag = row_dev[label] - global_mean
        if np.isnan(mag):
            continue
        size = sizes[label]
        small = not np.isnan(size) and size <= size_median
        if mag > 0:
            hint = ('horizontal — this cohort retains above its peers'
                    + (' despite a small size (low volume, high quality)'
                       if small else ''))
        else:
            hint = 'horizontal — this cohort retains below its peers'
        horizontal.append({
            'where': label,
            'magnitude': round(float(mag), 1),
            'size': None if np.isnan(size) else int(size),
            'lens_hint': hint,
        })
    horizontal.sort(key=lambda d: abs(d['magnitude']), reverse=True)

    # --- Diagonal: group deviations by calendar period (row pos + age) ---
    buckets = {}
    vals = dev[ages].values
    for i in range(vals.shape[0]):
        for j, age in enumerate(ages):
            v = vals[i, j]
            if not np.isnan(v):
                buckets.setdefault(i + age, []).append(v)
    diagonal = []
    for cal_key, vlist in buckets.items():
        if len(vlist) < _MIN_DIAGONAL_COHORTS:
            continue
        mean_dev = float(np.mean(vlist))
        where = index_labels[min(cal_key, len(index_labels) - 1)]
        diagonal.append({
            'where': where,
            'magnitude': round(mean_dev, 1),
            'n_cohorts': len(vlist),
            'lens_hint': ('diagonal — many cohorts move together here: a '
                          'simultaneous, all-cohort event (launch, bug, outage)'),
        })
    diagonal.sort(key=lambda d: abs(d['magnitude']), reverse=True)

    # --- Vertical: tenure ages whose drop exceeds the smooth decay ---
    avg_by_age = rate[ages].mean(axis=0)
    drops = {}
    prev = None
    for age in ages:
        cur = avg_by_age[age]
        if prev is not None and not np.isnan(cur) and not np.isnan(prev):
            drops[age] = prev - cur
        prev = cur
    baseline = float(np.median(list(drops.values()))) if drops else 0.0
    vertical = []
    for age, drop in drops.items():
        vertical.append({
            'where': f'age {age}',
            'magnitude': round(float(drop), 1),
            'excess': round(float(drop - baseline), 1),
            'n_cohorts': int(rate[age].notna().sum()),
            'lens_hint': ('vertical — an unusually steep drop at this tenure: a '
                          'survival moment (trial end, renewal)'),
        })
    vertical.sort(key=lambda d: d['excess'], reverse=True)

    return {
        'horizontal': horizontal[:top],
        'diagonal': diagonal[:top],
        'vertical': vertical[:top],
    }


# ---------------------------------------------------------------------------
# Public API — Retention Curve
# ---------------------------------------------------------------------------

def retention_curve(df, max_periods=40, segment_by=None, active_event=None, save=None):
    """
    Average retention curve across all weekly cohorts.

    Parameters
    ----------
    df : DataFrame with 'date' and 'user_id' columns
    max_periods : max weeks to show on x-axis
    segment_by : optional column or list of columns to split on; overlays one
        line per value (or value-combination)
    active_event : optional event_type to count as 'active' (e.g. the brief's
        core_action); defaults to counting any row
    save : optional filename to save the figure

    Returns
    -------
    fig, ax
    """
    sns.set_theme(style="whitegrid")
    palette = sns.color_palette("muted")

    df = _filter_active(df, active_event)

    def _avg_curve(sub):
        cohort_data, *_ = _prepare_cohorts(sub, 'weekly')
        avg = (
            cohort_data.groupby('periods_since_signup')['retention_pct']
            .mean().reset_index()
        )
        return avg[avg['periods_since_signup'] <= max_periods]

    fig, ax = plt.subplots(figsize=(12, 6))
    xmax = 0
    for i, (label, sub) in enumerate(_segment_values(df, segment_by)):
        avg = _avg_curve(sub)
        color = palette[i % len(palette)]
        sns.lineplot(
            data=avg, x='periods_since_signup', y='retention_pct',
            color=color, linewidth=2.5, ax=ax, label=label,
        )
        if label is None:  # keep the single-curve look unchanged
            ax.fill_between(
                avg['periods_since_signup'], avg['retention_pct'],
                alpha=0.15, color=color,
            )
        xmax = max(xmax, int(avg['periods_since_signup'].max()))

    title = 'Overall Retention Curve'
    if segment_by is not None:
        seg_name = _segment_name(segment_by)
        title += f' by {seg_name}'
        ax.legend(title=seg_name)
    ax.set_title(title, fontsize=16, fontweight='bold')
    ax.set_xlabel('Weeks Since First Activity')
    ax.set_ylabel('% of Cohort Still Active')
    ax.set_ylim(0, 105)
    ax.set_xlim(0, xmax)

    plt.tight_layout()
    if save:
        plt.savefig(save, dpi=150, bbox_inches='tight')
    _maybe_show()

    return fig, ax


# ---------------------------------------------------------------------------
# Public API — Usage Frequency Histogram
# ---------------------------------------------------------------------------

def usage_frequency(df, save=None):
    """
    Histogram of average days active per month per user.
    Shows how frequently users engage — daily, weekly, or monthly.

    Parameters
    ----------
    df : DataFrame with 'date' and 'user_id' columns
    save : optional filename to save the figure (e.g. 'usage_frequency.png')

    Returns
    -------
    fig, ax
    avg_days_per_user : DataFrame with 'user_id' and 'avg_days_active_per_month'
    """
    sns.set_theme(style="whitegrid")

    df = df.copy()
    df['month'] = df['date'].dt.to_period('M')

    # Count unique active days per user per month
    active_days = (
        df.groupby(['user_id', 'month'])['date']
        .nunique()
        .reset_index(name='days_active')
    )

    # Average active days per user across all their active months
    avg_days_per_user = (
        active_days.groupby('user_id')['days_active']
        .mean()
        .reset_index(name='avg_days_active_per_month')
    )

    # Plot
    fig, ax = plt.subplots(figsize=(12, 7))

    sns.histplot(
        avg_days_per_user['avg_days_active_per_month'],
        discrete=True,
        kde=True,
        color='#3498db',
        alpha=0.6,
        label='Your Users',
        ax=ax,
    )

    # Target zone references
    ax.axvline(x=20, color='#1b5e20', linestyle='--', linewidth=2,
               label='Daily Target (20+)')
    ax.axvline(x=4, color='#0d47a1', linestyle='--', linewidth=2,
               label='Weekly Target (4+)')
    ax.axvline(x=1, color='#b71c1c', linestyle=':', linewidth=2,
               label='Monthly Target (1+)')

    ax.set_title('Product Usage Frequency — Avg Days Active per Month per User',
                 fontsize=16, fontweight='bold')
    ax.set_xlabel('Average Days Active per Month', fontsize=12)
    ax.set_ylabel('Number of Users', fontsize=12)
    ax.set_xlim(0, 32)
    ax.set_xticks(np.arange(0, 32, 2))
    ax.legend(loc='upper right')
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    if save:
        plt.savefig(save, dpi=150, bbox_inches='tight')
    _maybe_show()

    return fig, ax, avg_days_per_user


# ---------------------------------------------------------------------------
# Public API — Lifecycle States
# ---------------------------------------------------------------------------

def lifecycle_states(df, segment_by=None, active_event=None, save_prefix=None):
    """
    Classify users into lifecycle states and produce 2 charts:
    1. Stacked bar (bridge chart)
    2. Quick Ratio line

    Parameters
    ----------
    df : DataFrame with 'date' and 'user_id' columns
    segment_by : optional column or list of columns to split on; renders the
        pair of charts per value (or value-combination)
    active_event : optional event_type to count as 'active' (e.g. the brief's
        core_action); defaults to counting any row
    save_prefix : optional prefix for saving 2 PNGs
                  (e.g. 'output' → output_bars.png, output_quick_ratio.png)

    Returns
    -------
    When segment_by is None: (states_df, (fig1, fig2)).
    When segment_by is set: a list of (label, states_df, (fig1, fig2)).
    """
    df = _filter_active(df, active_event)
    results = []
    for label, sub in _segment_values(df, segment_by):
        suffix = '' if label is None else f' — {label}'
        if save_prefix and label is not None:
            prefix = f'{save_prefix}_{_safe_label(label)}'
        else:
            prefix = save_prefix
        out = _lifecycle_one(sub, prefix, suffix)
        if label is None:
            return out
        results.append((label, *out))
    return results


def _lifecycle_one(df, save_prefix, title_suffix=''):
    """Build the lifecycle states table + the two charts for one (sub)frame."""
    sns.set_theme(style="whitegrid")
    palette = sns.color_palette("muted")

    df = df.copy()
    df['week'] = df['date'].dt.to_period('W').dt.start_time
    weekly_active = df.groupby(['user_id', 'week']).size().reset_index(name='events')

    first_week = weekly_active.groupby('user_id')['week'].min().reset_index()
    first_week.columns = ['user_id', 'first_week']
    weekly_active = weekly_active.merge(first_week, on='user_id')

    all_weeks = sorted(weekly_active['week'].unique())
    active_sets = {}
    for week in all_weeks:
        active_sets[week] = set(
            weekly_active[weekly_active['week'] == week]['user_id']
        )

    first_week_map = first_week.set_index('user_id')['first_week'].to_dict()

    # Classify
    records = []
    churned_pool = set()
    at_risk_pool = set()

    for i, week in enumerate(all_weeks):
        current_active = active_sets[week]
        prev_active = active_sets[all_weeks[i - 1]] if i > 0 else set()

        new = {u for u in current_active if first_week_map[u] == week}
        retained = current_active - new
        resurrected = retained & (churned_pool | at_risk_pool)
        retained = retained - resurrected

        newly_inactive = prev_active - current_active
        newly_churned = at_risk_pool - current_active
        churned_pool = (churned_pool | newly_churned) - current_active
        at_risk_pool = newly_inactive

        records.append({
            'week': week,
            'New': len(new),
            'Retained': len(retained),
            'Resurrected': len(resurrected),
            'At-Risk': len(at_risk_pool),
            'Churned': len(newly_churned),
        })

    states_df = pd.DataFrame(records)

    # --- Plot 1: Stacked bar ---
    fig1, ax3 = plt.subplots(figsize=(14, 6))
    x = range(len(states_df))
    width = 0.8
    ax3.bar(x, states_df['New'], width, label='New', color=palette[0])
    ax3.bar(x, states_df['Retained'], width, bottom=states_df['New'],
            label='Retained', color=palette[2])
    ax3.bar(x, states_df['Resurrected'], width,
            bottom=states_df['New'] + states_df['Retained'],
            label='Resurrected', color=palette[4])
    ax3.bar(x, -states_df['At-Risk'], width,
            label='At-Risk', color=palette[1], alpha=0.7)
    ax3.bar(x, -states_df['Churned'], width, bottom=-states_df['At-Risk'],
            label='Churned', color=palette[3], alpha=0.7)
    ax3.axhline(y=0, color='grey', linewidth=0.8)
    ax3.set_title('User Lifecycle Buckets — Weekly Breakdown' + title_suffix,
                  fontsize=16, fontweight='bold')
    ax3.set_xlabel('Week')
    ax3.set_ylabel('Users')
    ax3.legend(loc='lower left')
    tick_positions = list(range(0, len(states_df), 4))
    tick_labels = [states_df['week'].iloc[i].strftime('%Y-%m-%d')
                   for i in tick_positions]
    ax3.set_xticks(tick_positions)
    ax3.set_xticklabels(tick_labels, rotation=45)
    plt.tight_layout()
    if save_prefix:
        plt.savefig(f'{save_prefix}_bars.png', dpi=150, bbox_inches='tight')
    _maybe_show()

    # --- Plot 2: Quick Ratio ---
    states_df['Quick Ratio'] = (
        (states_df['New'] + states_df['Resurrected'])
        / states_df['Churned'].replace(0, np.nan)
    )
    fig2, ax4 = plt.subplots(figsize=(14, 6))
    sns.lineplot(data=states_df, x='week', y='Quick Ratio',
                 color=palette[0], linewidth=2.5, ax=ax4)
    ax4.axhline(y=1, color='grey', linewidth=1, linestyle='--')
    ax4.set_title('Quick Ratio — (New + Resurrected) / Churned' + title_suffix,
                  fontsize=16, fontweight='bold')
    ax4.set_xlabel('Week')
    ax4.set_ylabel('Quick Ratio')
    plt.xticks(rotation=45)
    plt.tight_layout()
    if save_prefix:
        plt.savefig(f'{save_prefix}_quick_ratio.png', dpi=150, bbox_inches='tight')
    _maybe_show()

    return states_df, (fig1, fig2)
