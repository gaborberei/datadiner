"""
DataDiner Analytics Module
==========================
Reusable product analytics functions for retention, churn, and lifecycle analysis.

Usage:
    import pandas as pd
    from datadiner import retention_rate_heatmap, lifecycle_states

    df = pd.read_csv('your_data.csv', parse_dates=['date'])
    fig, ax = retention_rate_heatmap(df, granularity='weekly')
    fig, ax = lifecycle_states(df)
"""

import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

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
                        ha='center', va='center', fontsize=7,
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
                        ha='center', va='center', fontsize=7,
                        color=text_color)

    ax.set_title(title, fontsize=16, fontweight='bold')

    plt.tight_layout()
    if save:
        plt.savefig(save, dpi=150, bbox_inches='tight')
    plt.show()

    return fig, ax


# ---------------------------------------------------------------------------
# Public API — Cohort Heatmaps
# ---------------------------------------------------------------------------

def retention_counts_heatmap(df, granularity='weekly', save=None):
    """
    Cohort heatmap showing raw active user counts per period.

    Parameters
    ----------
    df : DataFrame with 'date' and 'user_id' columns
    granularity : 'weekly' or 'monthly'
    save : optional filename to save the figure (e.g. 'retention_counts.png')

    Returns
    -------
    fig, ax
    """
    cohort_data, sizes, pcol, maxp, fmt = _prepare_cohorts(df, granularity)
    pivot = _build_pivot(cohort_data, sizes, pcol, maxp, fmt, 'active_users')

    period_label = 'Weeks' if granularity in ('week', 'weekly') else 'Months'
    title = f'Cohort Retention Counts — Active Users per {period_label[:-1]}'
    figsize = (20, 12) if granularity in ('week', 'weekly') else (16, 8)

    fig, ax = _plot_heatmap(pivot, title, 'int', figsize, save)
    ax.set_xlabel(f'{period_label} Since Signup')
    ax.set_ylabel(f'Cohort {period_label[:-1]}')
    return fig, ax


def retention_rate_heatmap(df, granularity='weekly', save=None):
    """
    Cohort heatmap showing % of each cohort still active.

    Parameters
    ----------
    df : DataFrame with 'date' and 'user_id' columns
    granularity : 'weekly' or 'monthly'
    save : optional filename to save the figure

    Returns
    -------
    fig, ax
    """
    cohort_data, sizes, pcol, maxp, fmt = _prepare_cohorts(df, granularity)
    pivot = _build_pivot(cohort_data, sizes, pcol, maxp, fmt, 'retention_pct')

    period_label = 'Weeks' if granularity in ('week', 'weekly') else 'Months'
    prefix = '' if granularity in ('week', 'weekly') else 'Monthly '
    title = f'{prefix}Cohort Retention Rate — % Still Active (colored per column)'
    figsize = (20, 12) if granularity in ('week', 'weekly') else (16, 8)

    fig, ax = _plot_heatmap(pivot, title, 'pct', figsize, save)
    ax.set_xlabel(f'{period_label} Since Signup')
    ax.set_ylabel(f'Cohort {period_label[:-1]}')
    return fig, ax


def churn_counts_heatmap(df, granularity='weekly', save=None):
    """
    Cohort heatmap showing users lost per period (period-over-period diff).

    Parameters
    ----------
    df : DataFrame with 'date' and 'user_id' columns
    granularity : 'weekly' or 'monthly'
    save : optional filename to save the figure

    Returns
    -------
    fig, ax
    """
    cohort_data, sizes, pcol, maxp, fmt = _prepare_cohorts(df, granularity)
    abs_pivot = _build_pivot(cohort_data, sizes, pcol, maxp, fmt, 'active_users')

    # Diff (skip Users col, then re-add it)
    users_col = abs_pivot['Users']
    data_cols = abs_pivot.drop(columns='Users')
    diff = data_cols.diff(axis=1).iloc[:, 1:]
    diff.insert(0, 'Users', users_col)

    period_label = 'Weeks' if granularity in ('week', 'weekly') else 'Months'
    prefix = '' if granularity in ('week', 'weekly') else 'Monthly '
    title = f'{prefix}Cohort Churn Counts — Users Lost per {period_label[:-1]}'
    figsize = (20, 12) if granularity in ('week', 'weekly') else (16, 8)

    fig, ax = _plot_heatmap(diff, title, 'signed_int', figsize, save)
    ax.set_xlabel(f'{period_label} Since Signup')
    ax.set_ylabel(f'Cohort {period_label[:-1]}')
    return fig, ax


def churn_rate_heatmap(df, granularity='weekly', save=None):
    """
    Cohort heatmap showing pp change in retention rate per period.

    Parameters
    ----------
    df : DataFrame with 'date' and 'user_id' columns
    granularity : 'weekly' or 'monthly'
    save : optional filename to save the figure

    Returns
    -------
    fig, ax
    """
    cohort_data, sizes, pcol, maxp, fmt = _prepare_cohorts(df, granularity)
    pct_pivot = _build_pivot(cohort_data, sizes, pcol, maxp, fmt, 'retention_pct')

    users_col = pct_pivot['Users']
    data_cols = pct_pivot.drop(columns='Users')
    diff = data_cols.diff(axis=1).iloc[:, 1:]
    diff.insert(0, 'Users', users_col)

    period_label = 'Weeks' if granularity in ('week', 'weekly') else 'Months'
    prefix = '' if granularity in ('week', 'weekly') else 'Monthly '
    title = (
        f'{prefix}Cohort Churn Rate — pp Change in Retention '
        f'{period_label[:-1]}-over-{period_label[:-1]}'
    )
    figsize = (20, 12) if granularity in ('week', 'weekly') else (16, 8)

    fig, ax = _plot_heatmap(diff, title, 'signed_pp', figsize, save)
    ax.set_xlabel(f'{period_label} Since Signup')
    ax.set_ylabel(f'Cohort {period_label[:-1]}')
    return fig, ax


def vs_average_heatmap(df, granularity='weekly', save=None):
    """
    Cohort heatmap showing each cohort's deviation from average retention.

    Parameters
    ----------
    df : DataFrame with 'date' and 'user_id' columns
    granularity : 'weekly' or 'monthly'
    save : optional filename to save the figure

    Returns
    -------
    fig, ax
    """
    cohort_data, sizes, pcol, maxp, fmt = _prepare_cohorts(df, granularity)
    pct_pivot = _build_pivot(cohort_data, sizes, pcol, maxp, fmt, 'retention_pct')

    users_col = pct_pivot['Users']
    data_cols = pct_pivot.drop(columns='Users')
    col_means = data_cols.mean(axis=0)
    deviation = data_cols.subtract(col_means, axis=1)
    deviation.insert(0, 'Users', users_col)

    period_label = 'Weeks' if granularity in ('week', 'weekly') else 'Months'
    prefix = '' if granularity in ('week', 'weekly') else 'Monthly '
    title = (
        f'{prefix}Cohort vs Average — Deviation from Average Retention'
        + (f' per {period_label[:-1]}' if granularity in ('week', 'weekly') else '')
    )
    figsize = (20, 12) if granularity in ('week', 'weekly') else (16, 8)

    fig, ax = _plot_heatmap(deviation, title, 'signed_pp', figsize, save)
    ax.set_xlabel(f'{period_label} Since Signup')
    ax.set_ylabel(f'Cohort {period_label[:-1]}')
    return fig, ax


# ---------------------------------------------------------------------------
# Public API — Retention Curve
# ---------------------------------------------------------------------------

def retention_curve(df, max_periods=40, save=None):
    """
    Average retention curve across all weekly cohorts.

    Parameters
    ----------
    df : DataFrame with 'date' and 'user_id' columns
    max_periods : max weeks to show on x-axis
    save : optional filename to save the figure

    Returns
    -------
    fig, ax
    """
    sns.set_theme(style="whitegrid")
    palette = sns.color_palette("muted")

    cohort_data, sizes, pcol, maxp, fmt = _prepare_cohorts(df, 'weekly')

    avg_retention = (
        cohort_data
        .groupby('periods_since_signup')['retention_pct']
        .mean()
        .reset_index()
    )
    avg_retention = avg_retention[avg_retention['periods_since_signup'] <= max_periods]

    fig, ax = plt.subplots(figsize=(12, 6))

    sns.lineplot(
        data=avg_retention, x='periods_since_signup', y='retention_pct',
        color=palette[0], linewidth=2.5, ax=ax,
    )
    ax.fill_between(
        avg_retention['periods_since_signup'],
        avg_retention['retention_pct'],
        alpha=0.15, color=palette[0],
    )

    ax.set_title('Overall Retention Curve', fontsize=16, fontweight='bold')
    ax.set_xlabel('Weeks Since First Activity')
    ax.set_ylabel('% of Cohort Still Active')
    ax.set_ylim(0, 105)
    ax.set_xlim(0, avg_retention['periods_since_signup'].max())

    plt.tight_layout()
    if save:
        plt.savefig(save, dpi=150, bbox_inches='tight')
    plt.show()

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
    plt.show()

    return fig, ax, avg_days_per_user


# ---------------------------------------------------------------------------
# Public API — Lifecycle States
# ---------------------------------------------------------------------------

def lifecycle_states(df, save_prefix=None):
    """
    Classify users into lifecycle states and produce 2 charts:
    1. Stacked bar (bridge chart)
    2. Quick Ratio line

    Parameters
    ----------
    df : DataFrame with 'date' and 'user_id' columns
    save_prefix : optional prefix for saving 2 PNGs
                  (e.g. 'output' → output_bars.png, output_quick_ratio.png)

    Returns
    -------
    states_df : DataFrame with weekly lifecycle state counts
    figs : tuple of (fig1, fig2)
    """
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
    ax3.set_title('User Lifecycle Buckets — Weekly Breakdown',
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
    plt.show()

    # --- Plot 2: Quick Ratio ---
    states_df['Quick Ratio'] = (
        (states_df['New'] + states_df['Resurrected'])
        / states_df['Churned'].replace(0, np.nan)
    )
    fig2, ax4 = plt.subplots(figsize=(14, 6))
    sns.lineplot(data=states_df, x='week', y='Quick Ratio',
                 color=palette[0], linewidth=2.5, ax=ax4)
    ax4.axhline(y=1, color='grey', linewidth=1, linestyle='--')
    ax4.set_title('Quick Ratio — (New + Resurrected) / Churned',
                  fontsize=16, fontweight='bold')
    ax4.set_xlabel('Week')
    ax4.set_ylabel('Quick Ratio')
    plt.xticks(rotation=45)
    plt.tight_layout()
    if save_prefix:
        plt.savefig(f'{save_prefix}_quick_ratio.png', dpi=150, bbox_inches='tight')
    plt.show()

    return states_df, (fig1, fig2)
