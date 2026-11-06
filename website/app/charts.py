"""
Data loading, filtering and all charts for the NYC Affordable Housing & Street Safety website.

Each research question has:
  - a figure function  make_qN(data, measure)  -> Plotly figure
  - a summary function summary_qN(data, measure) -> one sentence with the key numbers for the current filters
and one entry in RESEARCH_QUESTIONS at the bottom of this file (team members can edit the
names in MEMBERS and add their own written interpretation in the 'interpretation' field).

`data` is a dict of tables that are already filtered by the dropdowns:
  data['buildings']    one row per affordable building (buildings_integrated.csv + columns computed below)
  data['borough_year'] one row per borough and year (borough_year.csv)
"""
import os

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
RADIUS_M = 500  # same radius as the spatial join in the notebook (section 4)

# Team members: edit the names here and they update everywhere on the website
MEMBERS = {1: 'Nadeen Yasser', 2: 'Renad Raafat', 3: 'Malak Ehab', 4: 'Joudy Hagar', 5: 'Noor Eldin'}

BOROUGHS = ['Bronx', 'Brooklyn', 'Manhattan', 'Queens', 'Staten Island']
CONSTRUCTION_TYPES = ['New Construction', 'Preservation']
DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
INCOME_GROUPS = {
    'Extremely / very low income': ['extremely_low_income_units', 'very_low_income_units'],
    'Low income': ['low_income_units'],
    'Moderate / middle income': ['moderate_income_units', 'middle_income_units'],
}

# Fixed colours: each borough / type / group always keeps the same colour, whatever the filters
BOROUGH_COLORS = {'Bronx': '#2a78d6', 'Brooklyn': '#eb6834', 'Manhattan': '#1baf7a',
                  'Queens': '#eda100', 'Staten Island': '#e87ba4', 'All NYC': '#0b0b0b'}
TYPE_COLORS = {'New Construction': '#2a78d6', 'Preservation': '#eb6834'}
INCOME_COLORS = dict(zip(INCOME_GROUPS, ['#2a78d6', '#eb6834', '#1baf7a']))
NEAR_COLORS = {'Within 500 m of affordable housing': '#2a78d6', 'Elsewhere': '#eb6834'}
PERIOD_COLORS = {'Before completion': '#86b6ef', 'After completion': '#1c5cab'}
SEQUENTIAL_BLUE = ['#cde2fb', '#86b6ef', '#3987e5', '#256abf', '#104281']

# The crash measure chosen in the dropdown (the "transportation category" filter)
MEASURES = {
    'crashes': {'label': 'Serious crashes', 'building_col': 'nearby_crashes',
                'area_col': 'serious_crashes', 'crash_col': None},
    'severe':  {'label': 'Severe injuries', 'building_col': 'nearby_severe_injuries',
                'area_col': 'severe_injuries', 'crash_col': 'total_severe_injuries'},
    'fatal':   {'label': 'Fatalities', 'building_col': 'nearby_fatalities',
                'area_col': 'fatalities', 'crash_col': 'total_fatalities'},
}

CHART_LAYOUT = dict(
    template='plotly_white',
    paper_bgcolor='#ffffff', plot_bgcolor='#ffffff',
    font=dict(family='Public Sans, Segoe UI, Arial, sans-serif', size=13, color='#5a646b'),
    title_font=dict(family='Barlow Condensed, Arial Narrow, sans-serif', size=20, color='#1b2124'),
    margin=dict(l=60, r=20, t=60, b=110),
    hoverlabel=dict(bgcolor='white', font_size=13),
    legend=dict(orientation='h', yanchor='top', y=-0.2, xanchor='left', x=0, title_text=''),
)


# ================================================================ data
def add_income_group(buildings):
    """The income group with the most affordable units in each building (same rule as the notebook, Q1)."""
    group_units = pd.DataFrame({group: buildings[cols].sum(axis=1) for group, cols in INCOME_GROUPS.items()})
    buildings['main_income_group'] = group_units.idxmax(axis=1).where(group_units.sum(axis=1) > 0)


def load_data():
    """Load the integrated tables exported at the end of section 5 of the notebook."""
    buildings = pd.read_csv(os.path.join(DATA_DIR, 'buildings_integrated.csv'),
                            parse_dates=['building_completion_date'])
    buildings['postcode'] = buildings['postcode'].astype('Int64').astype('string').str.zfill(5)
    borough_year = pd.read_csv(os.path.join(DATA_DIR, 'borough_year.csv'))
    for col in ['serious_crashes', 'local_street_crashes', 'severe_injuries', 'fatalities']:
        borough_year[col] = borough_year[col].astype('Int64')

    # Years of crash data behind the building counts (about 4.5), recovered from the exported columns
    has_crashes = buildings['nearby_crashes_per_year'] > 0
    years_covered = (buildings.loc[has_crashes, 'nearby_crashes']
                     / buildings.loc[has_crashes, 'nearby_crashes_per_year']).median()
    for measure in MEASURES.values():
        if measure['building_col'] != 'nearby_crashes':
            buildings[measure['building_col'] + '_per_year'] = buildings[measure['building_col']] / years_covered
    add_income_group(buildings)
    return {'buildings': buildings, 'borough_year': borough_year}


def apply_filters(data, boroughs, years, construction_types):
    """Return the data restricted to the selected filters (an empty selection means 'all')."""
    boroughs = boroughs or BOROUGHS
    construction_types = construction_types or CONSTRUCTION_TYPES
    buildings, borough_year = data['buildings'], data['borough_year']
    years = years or sorted(set(buildings['start_year']) | set(borough_year['year']))
    return {
        'buildings': buildings[buildings['borough'].isin(boroughs)
                               & buildings['start_year'].isin(years)
                               & buildings['reporting_construction_type'].isin(construction_types)],
        'borough_year': borough_year[borough_year['borough'].isin(boroughs) & borough_year['year'].isin(years)],
    }


# ================================================================ helpers
def style(fig, height=470):
    fig.update_layout(**CHART_LAYOUT, height=height)
    fig.update_xaxes(showgrid=False, linecolor='#c9d0cd')
    fig.update_yaxes(gridcolor='#e8ecea', zeroline=False)
    return fig


def empty_figure(message='No data matches these filters'):
    fig = go.Figure()
    fig.add_annotation(text=message, showarrow=False, font=dict(size=15, color='#52514e'))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return style(fig, height=300)


def per_year_col(measure):
    return measure['building_col'] + '_per_year'


def rank_correlation(x, y):
    """Spearman's rank correlation (Pearson correlation of the ranks)."""
    return x.rank().corr(y.rank())


# ================================================================ overview
def kpis(data, measure):
    buildings = data['buildings']
    if buildings.empty:
        return {'buildings': '0', 'units': '0', 'median': '–', 'fatal_share': '–'}
    return {
        'buildings': f"{len(buildings):,}",
        'units': f"{int(buildings['all_counted_units'].sum()):,}",
        'median': f"{buildings[per_year_col(measure)].median():.1f}",
        'fatal_share': f"{(buildings['nearby_fatalities'] > 0).mean():.0%}",
    }


def map_figure(data, measure):
    """Overview map: each affordable building, coloured by the crash measure within 500 m."""
    buildings = data['buildings']
    if buildings.empty:
        return empty_figure()
    col = per_year_col(measure)
    fig = px.scatter_mapbox(
        buildings, lat='latitude', lon='longitude', color=col,
        color_continuous_scale=SEQUENTIAL_BLUE, zoom=9.4, center={'lat': 40.71, 'lon': -73.94},
        mapbox_style='open-street-map', hover_name='project_name',
        hover_data={'borough': True, 'all_counted_units': True, 'reporting_construction_type': True,
                    col: ':.1f', 'latitude': False, 'longitude': False},
        labels={col: f'{measure["label"]} within 500 m / year', 'all_counted_units': 'Affordable units',
                'reporting_construction_type': 'Type', 'borough': 'Borough'},
        title=f'Affordable housing buildings coloured by {measure["label"].lower()} within 500 m (per year)')
    fig.update_traces(marker=dict(size=7, opacity=0.85))
    style(fig, height=560)
    fig.update_layout(margin=dict(l=10, r=10, t=60, b=10), coloraxis_colorbar=dict(title='per year', thickness=12))
    return fig


def borough_year_figures(data, measure):
    """Housing produced and crashes per borough and year (2022 onwards). Two charts, not one chart
    with two y-axes, because the two measures have different scales."""
    crash_years = data['borough_year'][data['borough_year']['has_crash_data']]
    if crash_years.empty:
        return empty_figure('No crash data for these years (crash data starts in 2022)'), empty_figure('')
    figures = []
    for col, label, title in [('affordable_units_started', 'Affordable units started', 'Affordable units started per year'),
                              (measure['area_col'], measure['label'], f'{measure["label"]} per year')]:
        fig = px.line(crash_years, x='year', y=col, color='borough', markers=True,
                      color_discrete_map=BOROUGH_COLORS, category_orders={'borough': BOROUGHS},
                      labels={col: label, 'year': 'Year', 'borough': 'Borough'}, title=title)
        fig.update_traces(line=dict(width=2), marker=dict(size=8))
        fig.update_xaxes(dtick=1)
        if crash_years['is_partial_year'].any():
            fig.add_annotation(x=crash_years['year'].max(), y=1.02, yref='paper', text='Jan–Jun only',
                               showarrow=False, font=dict(size=11, color='#52514e'))
        figures.append(style(fig, height=380))
    return figures


# ================================================================ Q3  new construction vs preservation
def make_q3(data, measure):
    buildings = data['buildings']
    if buildings.empty:
        return empty_figure()
    col = per_year_col(measure)
    fig = px.box(buildings, x='borough', y=col, color='reporting_construction_type', points=False,
                 color_discrete_map=TYPE_COLORS,
                 category_orders={'borough': BOROUGHS, 'reporting_construction_type': CONSTRUCTION_TYPES},
                 labels={col: f'{measure["label"]} within 500 m per year', 'borough': 'Borough',
                         'reporting_construction_type': 'Type'},
                 title=f'{measure["label"]} near new vs preserved affordable buildings')
    return style(fig)


def summary_q3(data, measure):
    """Within-borough comparison (the citywide medians alone would mislead, because Manhattan, the most
    exposed borough, is mostly preservation)."""
    medians = (data['buildings'].groupby(['borough', 'reporting_construction_type'])[per_year_col(measure)]
               .median().unstack())
    if medians.shape[1] < 2 or medians.dropna().empty:
        return 'Select both construction types to compare them.'
    medians = medians.dropna()
    higher = medians.index[medians['New Construction'] > medians['Preservation']].tolist()
    return (f'New construction has a higher median {measure["label"].lower()} within 500 m than preservation '
            f'in {len(higher)} of {len(medians)} borough(s)' + (f': {", ".join(higher)}.' if higher else '.'))


# ================================================================ Q4  trend by start year
def make_q4(data, measure):
    buildings = data['buildings']
    if buildings.empty:
        return empty_figure()
    col = per_year_col(measure)
    by_borough = buildings.groupby(['start_year', 'borough'])[col].agg(median='median', buildings='count').reset_index()
    citywide = (buildings.groupby('start_year')[col].agg(median='median', buildings='count')
                .reset_index().assign(borough='All NYC'))
    fig = px.line(pd.concat([by_borough, citywide]), x='start_year', y='median', color='borough', markers=True,
                  color_discrete_map=BOROUGH_COLORS, category_orders={'borough': ['All NYC'] + BOROUGHS},
                  hover_data={'buildings': True},
                  labels={'start_year': 'Project start year', 'median': f'Median {measure["label"].lower()} per year',
                          'borough': 'Borough', 'buildings': 'Buildings started'},
                  title=f'Median {measure["label"].lower()} within 500 m, by project start year')
    fig.update_traces(line=dict(width=2), marker=dict(size=8))
    fig.update_traces(selector=dict(name='All NYC'), line=dict(width=4))
    return style(fig)


def summary_q4(data, measure):
    buildings = data['buildings']
    if buildings['start_year'].nunique() < 2:
        return 'Select more than one year to see a trend.'
    rho = rank_correlation(buildings['start_year'], buildings[per_year_col(measure)])
    direction = 'no clear trend' if abs(rho) < 0.1 else ('more exposed' if rho > 0 else 'less exposed')
    return f'Spearman correlation between start year and exposure: {rho:.3f} ({direction} over time).'



# ================================================================ Q1  equity by income group
def make_q1(data, measure):
    buildings = data['buildings'].dropna(subset=['main_income_group'])
    if buildings.empty:
        return empty_figure()
    table = (buildings.pivot_table(index='main_income_group', columns='borough', values=per_year_col(measure),
                                   aggfunc='median')
             .reindex(index=list(INCOME_GROUPS), columns=[b for b in BOROUGHS if b in set(buildings['borough'])]))
    fig = px.imshow(table.round(2), text_auto=True, color_continuous_scale=SEQUENTIAL_BLUE, aspect='auto',
                    labels={'x': 'Borough', 'y': '', 'color': 'Median / year'},
                    title=f'Median {measure["label"].lower()} within 500 m per year, by income group served')
    style(fig, height=380)
    fig.update_layout(margin=dict(l=200, r=20, t=60, b=50))
    return fig


def summary_q1(data, measure):
    buildings = data['buildings'].dropna(subset=['main_income_group'])
    if buildings.empty:
        return ''
    table = buildings.pivot_table(index='borough', columns='main_income_group', values=per_year_col(measure),
                                  aggfunc='median')
    lowest = 'Extremely / very low income'
    if lowest not in table or table.shape[1] < 2:
        return ''
    others = table.drop(columns=lowest).max(axis=1)
    worse = table.index[table[lowest] > others].tolist()
    return (f'The lowest-income buildings are the most exposed group in {len(worse)} of {len(table)} borough(s)'
            + (f': {", ".join(worse)}.' if worse else '.'))


# ================================================================ Q2  double-burden ZIP codes
def zip_summary(buildings, measure):
    zips = (buildings.dropna(subset=['postcode'])
            .groupby(['postcode', 'borough'])
            .agg(buildings=('building_id', 'count'), affordable_units=('all_counted_units', 'sum'),
                 median_per_year=(per_year_col(measure), 'median'))
            .reset_index())
    zips = zips[zips['buildings'] >= 5]
    if zips.empty:
        return zips, None, None
    units_cut, crash_cut = zips['affordable_units'].quantile(0.75), zips['median_per_year'].quantile(0.75)
    zips['double_burden'] = (zips['affordable_units'] >= units_cut) & (zips['median_per_year'] >= crash_cut)
    return zips, units_cut, crash_cut


def make_q2(data, measure):
    zips, units_cut, crash_cut = zip_summary(data['buildings'], measure)
    if zips.empty:
        return empty_figure('No ZIP code with at least 5 buildings matches these filters')
    fig = px.scatter(zips, x='affordable_units', y='median_per_year', size='buildings', color='borough',
                     color_discrete_map=BOROUGH_COLORS, category_orders={'borough': BOROUGHS},
                     hover_name='postcode', size_max=30, opacity=0.75,
                     labels={'affordable_units': 'Affordable units in the ZIP code',
                             'median_per_year': f'Median {measure["label"].lower()} within 500 m per year',
                             'borough': 'Borough', 'buildings': 'Buildings'},
                     title='ZIP codes by affordable housing and exposure (top-right = double burden)')
    fig.add_vline(x=units_cut, line_dash='dash', line_color='#8a8984')
    fig.add_hline(y=crash_cut, line_dash='dash', line_color='#8a8984')
    return style(fig)


def summary_q2(data, measure):
    zips, _, _ = zip_summary(data['buildings'], measure)
    if zips.empty:
        return ''
    double = zips[zips['double_burden']]
    return (f'{len(double)} of {len(zips)} ZIP codes are in the top quarter for both affordable units and exposure; '
            f'they hold {double["affordable_units"].sum():,} affordable units '
            f'({double["affordable_units"].sum() / zips["affordable_units"].sum():.0%}).')


# ================================================================ Q5  fatal crash nearby
def make_q5(data, measure):
    buildings = data['buildings']
    if buildings.empty:
        return empty_figure()
    fatal = buildings['nearby_fatalities'] > 0
    occupied = buildings['occupied_whole_period']
    shares = pd.DataFrame({
        'All buildings': fatal.groupby(buildings['borough']).mean(),
        'Occupied for the whole period': fatal[occupied].groupby(buildings.loc[occupied, 'borough']).mean(),
    }).mul(100).reset_index().melt(id_vars='borough', var_name='group', value_name='pct')
    fig = px.bar(shares, x='borough', y='pct', color='group', barmode='group', text_auto='.0f',
                 color_discrete_sequence=['#2a78d6', '#eb6834'], category_orders={'borough': BOROUGHS},
                 labels={'pct': '% of buildings with a fatal crash within 500 m', 'borough': 'Borough', 'group': ''},
                 title='Affordable buildings with at least one fatal crash within 500 m (2022–2026)')
    fig.update_traces(marker_line_width=2, marker_line_color='#ffffff')
    return style(fig)


def summary_q5(data, measure):
    buildings = data['buildings']
    if buildings.empty:
        return ''
    fatal = buildings['nearby_fatalities'] > 0
    return (f'{fatal.mean():.1%} of these buildings had a fatal crash within 500 m; they hold '
            f'{int(buildings.loc[fatal, "all_counted_units"].sum()):,} of '
            f'{int(buildings["all_counted_units"].sum()):,} affordable units.')


# ================================================================ Q6  units by danger band
DANGER_BANDS = [-0.01, 2, 5, 8, float('inf')]
BAND_LABELS = ['Low (0–2 per year)', 'Moderate (2–5)', 'High (5–8)', 'Very high (8+)']


def units_by_band(buildings):
    """The bands are defined on serious crashes per year (as in the notebook), whatever measure is selected."""
    bands = pd.cut(buildings['nearby_crashes_per_year'], bins=DANGER_BANDS, labels=BAND_LABELS)
    return buildings.assign(danger_band=bands).pivot_table(index='borough', columns='danger_band',
                                                           values='all_counted_units', aggfunc='sum', observed=False)


def make_q6(data, measure):
    buildings = data['buildings']
    if buildings.empty:
        return empty_figure()
    long = units_by_band(buildings).reset_index().melt(id_vars='borough', var_name='danger_band',
                                                                value_name='affordable_units')
    fig = px.bar(long, x='borough', y='affordable_units', color='danger_band',
                 category_orders={'danger_band': BAND_LABELS, 'borough': BOROUGHS},
                 color_discrete_sequence=['#cde2fb', '#86b6ef', '#2a78d6', '#104281'],
                 labels={'affordable_units': 'Affordable units', 'borough': 'Borough',
                         'danger_band': 'Serious crashes within 500 m'},
                 title='Affordable units by danger band (serious crashes within 500 m per year)')
    fig.update_traces(marker_line_width=2, marker_line_color='#ffffff')
    return style(fig)


def summary_q6(data, measure):
    buildings = data['buildings']
    if buildings.empty or buildings['all_counted_units'].sum() == 0:
        return ''
    totals = units_by_band(buildings).sum()
    high = totals['High (5–8)'] + totals['Very high (8+)']
    return (f'{int(high):,} affordable units ({high / totals.sum():.0%}) are in high or very high bands '
            f'(5+ per year), including {int(totals["Very high (8+)"]):,} in the very high band (8+).')


# ================================================================ Q7  borough shares
def full_crash_years(borough_year):
    return borough_year[borough_year['has_crash_data'] & ~borough_year['is_partial_year']]


def make_q7(data, measure):
    rows = full_crash_years(data['borough_year'])
    if rows.empty or rows['borough'].nunique() < 2:
        return empty_figure('Select at least two boroughs and a full year (2022–2025)')
    col = 'local_street_crashes' if measure['area_col'] == 'serious_crashes' else measure['area_col']
    label = 'serious local-street crashes' if col == 'local_street_crashes' else measure['label'].lower()
    totals = rows.groupby('borough')[['affordable_units_started', col]].sum().astype(float)
    shares = (totals / totals.sum() * 100).reset_index().melt(id_vars='borough', var_name='measure', value_name='share')
    shares['measure'] = shares['measure'].map({'affordable_units_started': 'Share of affordable units started',
                                               col: f'Share of {label}'})
    fig = px.bar(shares, x='borough', y='share', color='measure', barmode='group', text_auto='.0f',
                 color_discrete_sequence=['#2a78d6', '#eb6834'], category_orders={'borough': BOROUGHS},
                 labels={'share': '% of the selected total (2022–2025)', 'borough': 'Borough', 'measure': ''},
                 title=f"Each borough's share of new affordable housing vs share of {label}")
    fig.update_traces(marker_line_width=2, marker_line_color='#ffffff')
    return style(fig)


def summary_q7(data, measure):
    rows = full_crash_years(data['borough_year'])
    if rows.empty or rows['borough'].nunique() < 2:
        return ''
    totals = rows.groupby('borough')[['affordable_units_started', 'local_street_crashes']].sum().astype(float)
    ratio = (totals['affordable_units_started'] / totals['local_street_crashes']).sort_values()
    return (f'Affordable units started per serious local-street crash: highest in {ratio.index[-1]} '
            f'({ratio.iloc[-1]:.1f}), lowest in {ratio.index[0]} ({ratio.iloc[0]:.1f}).')


# ================================================================ Q8  borough paths 2022–2025
def make_q8(data, measure):
    rows = full_crash_years(data['borough_year']).sort_values(['borough', 'year'])
    if rows.empty:
        return empty_figure('No full years of crash data match these filters (2022–2025)')
    col = 'local_street_crashes' if measure['area_col'] == 'serious_crashes' else measure['area_col']
    label = 'Serious local-street crashes' if col == 'local_street_crashes' else measure['label']
    fig = px.line(rows, x='affordable_units_started', y=col, color='borough', markers=True, text='year',
                  color_discrete_map=BOROUGH_COLORS, category_orders={'borough': BOROUGHS},
                  labels={'affordable_units_started': 'Affordable units started in the year',
                          col: f'{label} in the year', 'borough': 'Borough'},
                  title=f"Each borough's path, 2022–2025: housing produced vs {label.lower()}")
    fig.update_traces(line=dict(width=2), marker=dict(size=9), textposition='top center',
                      textfont=dict(size=10, color='#52514e'))
    return style(fig)


def summary_q8(data, measure):
    rows = full_crash_years(data['borough_year']).sort_values(['borough', 'year'])
    if rows['year'].nunique() < 2:
        return 'Select at least two full years (2022–2025) to compare.'
    parts = []
    for borough, group in rows.groupby('borough'):
        first, last = group.iloc[0], group.iloc[-1]
        change = (last['local_street_crashes'] / first['local_street_crashes'] - 1) * 100
        parts.append(f'{borough} {change:+.0f}%')
    return f'Change in serious local-street crashes, {rows["year"].min()}–{rows["year"].max()}: ' + ', '.join(parts) + '.'


# ================================================================ Q9  building size
def make_q9(data, measure):
    buildings = data['buildings']
    buildings = buildings[buildings['all_counted_units'] > 0]
    if buildings.empty:
        return empty_figure()
    col = per_year_col(measure)
    fig = px.scatter(buildings, x='all_counted_units', y=col, color='borough', log_x=True, opacity=0.5,
                     color_discrete_map=BOROUGH_COLORS, category_orders={'borough': BOROUGHS},
                     hover_name='project_name',
                     labels={'all_counted_units': 'Affordable units in the building (log scale)',
                             col: f'{measure["label"]} within 500 m per year', 'borough': 'Borough'},
                     title=f'Building size vs {measure["label"].lower()} nearby')
    fig.update_traces(marker=dict(size=8, line=dict(width=1, color='#ffffff')))
    if len(buildings) > 2 and buildings['all_counted_units'].nunique() > 1:
        log_units = np.log10(buildings['all_counted_units'])
        slope, intercept = np.polyfit(log_units, buildings[col], 1)
        xs = np.logspace(log_units.min(), log_units.max(), 50)
        fig.add_trace(go.Scatter(x=xs, y=slope * np.log10(xs) + intercept, mode='lines', name='Trend (all boroughs)',
                                 line=dict(color='#0b0b0b', width=2, dash='dash'), hoverinfo='skip'))
    return style(fig)


def summary_q9(data, measure):
    buildings = data['buildings']
    buildings = buildings[buildings['all_counted_units'] > 0]
    if len(buildings) < 3:
        return ''
    rho = rank_correlation(buildings['all_counted_units'], buildings[per_year_col(measure)])
    large = buildings['all_counted_units'] > 100
    return (f'Spearman correlation between size and exposure: {rho:.2f}. Median for buildings with 100+ affordable '
            f'units: {buildings.loc[large, per_year_col(measure)].median():.2f} per year vs '
            f'{buildings.loc[~large, per_year_col(measure)].median():.2f} for smaller ones.')


# ================================================================ Q10  most exposed buildings
def most_exposed(buildings, measure):
    col = per_year_col(measure)
    return buildings[buildings[col] >= buildings[col].quantile(0.90)]


def make_q10(data, measure):
    buildings = data['buildings']
    if buildings.empty:
        return empty_figure()
    top = most_exposed(buildings, measure)
    col = per_year_col(measure)
    fig = px.scatter_mapbox(top, lat='latitude', lon='longitude', color='borough', size='all_counted_units',
                            size_max=18, zoom=10, center={'lat': 40.75, 'lon': -73.92}, mapbox_style='open-street-map',
                            color_discrete_map=BOROUGH_COLORS, category_orders={'borough': BOROUGHS},
                            hover_name='project_name',
                            hover_data={col: ':.1f', 'all_counted_units': True, 'latitude': False, 'longitude': False},
                            labels={col: f'{measure["label"]} / year within 500 m', 'all_counted_units': 'Affordable units',
                                    'borough': 'Borough'},
                            title=f'The 10% most exposed buildings ({measure["label"].lower()} within 500 m)')
    style(fig, height=560)
    fig.update_layout(margin=dict(l=10, r=10, t=60, b=10),
                      legend=dict(orientation='h', yanchor='bottom', y=0.01, x=0.01, bgcolor='rgba(255,255,255,0.8)'))
    return fig


def summary_q10(data, measure):
    buildings = data['buildings']
    if buildings.empty:
        return ''
    top = most_exposed(buildings, measure)
    by_borough = top['borough'].value_counts()
    return (f'{len(top):,} buildings ({measure["label"].lower()} ≥ {top[per_year_col(measure)].min():.2f} per year) '
            f'holding {int(top["all_counted_units"].sum()):,} affordable units; by borough: '
            + ', '.join(f'{b} {n}' for b, n in by_borough.items()) + '.')


# ================================================================ the list shown on the website
RESEARCH_QUESTIONS = [
    {'number': 1, 'member': 1, 'figure': make_q1, 'summary': summary_q1,
     'question': 'Within the same borough, do buildings serving the lowest-income residents face more serious '
                 'crashes nearby than buildings serving moderate/middle-income residents?',
     'interpretation': 'It depends on the borough. In the Bronx the lowest-income buildings are the most exposed '
                       '(median 6.34 vs 5.34–5.79 per year), while in Brooklyn and Queens they are the least exposed, '
                       'because moderate/middle-income units there are mostly in new developments on busier streets.'},
    {'number': 2, 'member': 1, 'figure': make_q2, 'summary': summary_q2,
     'question': 'Which neighbourhoods carry a "double burden" of a large amount of affordable housing and high '
                 'crash exposure?',
     'interpretation': '15 of 126 ZIP codes hold 30% of the affordable units in the top quarter of exposure: 9 in the '
                       'South and West Bronx, 4 in Manhattan (East Harlem, Harlem, Lower East Side) and 2 in Brooklyn.'},
    {'number': 3, 'member': 2, 'figure': make_q3, 'summary': summary_q3,
     'question': 'Is new affordable housing being built in safer areas than the existing buildings the city preserves?',
     'interpretation': 'No. In four of the five boroughs, new construction has more serious crashes nearby than '
                       'preserved buildings; the gap is largest in Queens (median 2.67 vs 0.89 per year). The Bronx '
                       'is the exception, with identical medians.'},
    {'number': 4, 'member': 2, 'figure': make_q4, 'summary': summary_q4,
     'question': 'Over time, has the city been placing new affordable projects in safer or more dangerous areas?',
     'interpretation': 'Citywide, the location pattern has been stable since 2014 (median about 4.5–5.4 serious '
                       'crashes per year nearby). Only Brooklyn shows a small upward trend; the Bronx dip in 2020 '
                       'comes from Co-op City.'},
    {'number': 5, 'member': 3, 'figure': make_q5, 'summary': summary_q5,
     'question': 'How many affordable-housing residents live within 500 m of a crash that killed someone, and does '
                 'this differ by borough?',
     'interpretation': 'About one in four buildings (26%) had a fatal crash within 500 m, rising to 36% in Manhattan; '
                       'these buildings hold 76,546 affordable units. Buildings occupied for the whole period show '
                       'almost the same picture.'},
    {'number': 6, 'member': 3, 'figure': make_q6, 'summary': summary_q6,
     'question': 'How many affordable homes are located in high-danger surroundings, and in which boroughs?',
     'interpretation': 'Almost half of all affordable units (47%) are in high or very high exposure; Manhattan (73%) '
                       'and the Bronx (55%) are most affected and together hold 84% of the very-high-exposure units.'},
    {'number': 7, 'member': 4, 'figure': make_q7, 'summary': summary_q7,
     'question': "Does each borough's share of new affordable housing match its share of the city's serious crashes?",
     'interpretation': 'The Bronx received 31% of new affordable units but had 19% of serious local-street crashes; '
                       'Queens is the opposite, with 23% of the crashes but only 13% of the new units.'},
    {'number': 8, 'member': 4, 'figure': make_q8, 'summary': summary_q8,
     'question': 'From 2022 to 2025, did boroughs that produced more affordable housing see serious crashes rise, '
                 'fall, or stay flat?',
     'interpretation': 'Housing production rose in every borough, but serious local-street crashes did not rise with '
                       'it (only Queens +23%). Within boroughs, year-to-year changes are not correlated (rho = 0.19, '
                       'p = 0.50).'},
    {'number': 9, 'member': 5, 'figure': make_q9, 'summary': summary_q9,
     'question': 'Are the largest affordable developments exposed to more serious crashes than small buildings?',
     'interpretation': 'Not really: the citywide correlation is weak (0.16) and mostly reflects differences between '
                       'boroughs; buildings with 100+ units have the same median as buildings with 1–10 units (4.45).'},
    {'number': 10, 'member': 5, 'figure': make_q10, 'summary': summary_q10,
     'question': 'Where are the most exposed affordable buildings, and how many affordable homes do they contain?',
     'interpretation': 'The 825 most exposed buildings (9.13+ serious crashes per year nearby) hold 36,969 units and '
                       'are all in the Bronx, Manhattan and Brooklyn, clustered in the West Bronx, Harlem and East '
                       'Harlem, and central Brooklyn.'},
]
