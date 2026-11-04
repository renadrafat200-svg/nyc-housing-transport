"""
Data loading, filtering and all charts for the NYC Affordable Housing & Street Safety website.

HOW TEAMMATES ADD THEIR RESEARCH QUESTIONS
1. Write a function `make_qN(data, measure)` below that returns a Plotly figure.
   - `data` is a dict of already-filtered tables: data['buildings'], data['borough_year']
     (and data['crashes'] if crashes_clean.csv is in the data folder).
   - `measure` is a dict describing the crash measure chosen in the dropdown (see MEASURES).
2. Add one entry to the RESEARCH_QUESTIONS list at the bottom of this file.
The website shows every entry automatically, and every chart updates with the Generate Report button.
"""
import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

BOROUGHS = ['Bronx', 'Brooklyn', 'Manhattan', 'Queens', 'Staten Island']
CONSTRUCTION_TYPES = ['New Construction', 'Preservation']

# Fixed colours: each borough / construction type always keeps the same colour, whatever the filters
BOROUGH_COLORS = {'Bronx': '#2a78d6', 'Brooklyn': '#eb6834', 'Manhattan': '#1baf7a',
                  'Queens': '#eda100', 'Staten Island': '#e87ba4', 'All NYC': '#0b0b0b'}
TYPE_COLORS = {'New Construction': '#2a78d6', 'Preservation': '#eb6834'}
SEQUENTIAL_BLUE = ['#cde2fb', '#86b6ef', '#3987e5', '#256abf', '#104281']

# The crash measure the user can choose (the "transportation category" filter)
MEASURES = {
    'crashes':  {'label': 'Serious crashes', 'building_col': 'nearby_crashes', 'area_col': 'serious_crashes'},
    'severe':   {'label': 'Severe injuries', 'building_col': 'nearby_severe_injuries', 'area_col': 'severe_injuries'},
    'fatal':    {'label': 'Fatalities', 'building_col': 'nearby_fatalities', 'area_col': 'fatalities'},
}

CHART_LAYOUT = dict(
    template='plotly_white',
    paper_bgcolor='#fcfcfb', plot_bgcolor='#fcfcfb',
    font=dict(family='Inter, Segoe UI, Arial, sans-serif', size=13, color='#52514e'),
    title_font=dict(size=16, color='#0b0b0b'),
    margin=dict(l=60, r=20, t=60, b=110),
    hoverlabel=dict(bgcolor='white', font_size=13),
    legend=dict(orientation='h', yanchor='top', y=-0.2, xanchor='left', x=0, title_text=''),
)


# ---------------------------------------------------------------- data
def load_data():
    """Load the integrated tables exported at the end of section 5 of the notebook."""
    buildings = pd.read_csv(os.path.join(DATA_DIR, 'buildings_integrated.csv'),
                            parse_dates=['building_completion_date'])
    borough_year = pd.read_csv(os.path.join(DATA_DIR, 'borough_year.csv'))
    for col in ['serious_crashes', 'local_street_crashes', 'severe_injuries', 'fatalities']:
        borough_year[col] = borough_year[col].astype('Int64')

    # Years of crash data behind the building counts (about 4.5), recovered from the exported columns
    has_crashes = buildings['nearby_crashes_per_year'] > 0
    years_covered = (buildings.loc[has_crashes, 'nearby_crashes']
                     / buildings.loc[has_crashes, 'nearby_crashes_per_year']).median()
    for measure in MEASURES.values():
        buildings[measure['building_col'] + '_per_year'] = buildings[measure['building_col']] / years_covered

    data = {'buildings': buildings, 'borough_year': borough_year, 'years_covered': years_covered}

    # Optional: crash-level data, for research questions that need individual crashes
    crashes_path = os.path.join(DATA_DIR, 'crashes_clean.csv')
    if os.path.exists(crashes_path):
        data['crashes'] = pd.read_csv(crashes_path, parse_dates=['crash_date'])
    return data


def apply_filters(data, boroughs, years, construction_types):
    """Return a copy of the data restricted to the selected filters (an empty selection means 'all')."""
    boroughs = boroughs or BOROUGHS
    construction_types = construction_types or CONSTRUCTION_TYPES
    buildings, borough_year = data['buildings'], data['borough_year']
    years = years or sorted(set(buildings['start_year']) | set(borough_year['year']))

    filtered = {
        'buildings': buildings[buildings['borough'].isin(boroughs)
                               & buildings['start_year'].isin(years)
                               & buildings['reporting_construction_type'].isin(construction_types)],
        'borough_year': borough_year[borough_year['borough'].isin(boroughs) & borough_year['year'].isin(years)],
        'years_covered': data['years_covered'],
    }
    if 'crashes' in data:
        crashes = data['crashes']
        filtered['crashes'] = crashes[crashes['crash_borough'].isin(boroughs) & crashes['crash_year'].isin(years)]
    return filtered


def style(fig, height=470):
    fig.update_layout(**CHART_LAYOUT, height=height)
    fig.update_xaxes(showgrid=False, linecolor='#c3c2b7')
    fig.update_yaxes(gridcolor='#ecebe7', zeroline=False)
    return fig


def empty_figure(message='No data matches these filters'):
    fig = go.Figure()
    fig.add_annotation(text=message, showarrow=False, font=dict(size=15, color='#52514e'))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return style(fig, height=300)


# ---------------------------------------------------------------- overview charts
def kpis(data, measure):
    buildings = data['buildings']
    if buildings.empty:
        return {'buildings': '0', 'units': '0', 'median': '–', 'fatal_share': '–'}
    per_year = buildings[measure['building_col'] + '_per_year']
    return {
        'buildings': f"{len(buildings):,}",
        'units': f"{int(buildings['all_counted_units'].sum()):,}",
        'median': f"{per_year.median():.1f}",
        'fatal_share': f"{(buildings['nearby_fatalities'] > 0).mean():.0%}",
    }


def map_figure(data, measure):
    """Cross-domain map: each affordable building, coloured by the crash measure within 500 m."""
    buildings = data['buildings']
    if buildings.empty:
        return empty_figure()
    col = measure['building_col'] + '_per_year'
    fig = px.scatter_mapbox(
        buildings, lat='latitude', lon='longitude', color=col,
        color_continuous_scale=SEQUENTIAL_BLUE, size_max=8, zoom=9.4,
        center={'lat': 40.71, 'lon': -73.94}, mapbox_style='carto-positron',
        hover_name='project_name',
        hover_data={'borough': True, 'all_counted_units': True, 'reporting_construction_type': True,
                    col: ':.1f', 'latitude': False, 'longitude': False},
        labels={col: f'{measure["label"]} within 500 m / year', 'all_counted_units': 'Affordable units',
                'reporting_construction_type': 'Type', 'borough': 'Borough'},
        title=f'Affordable housing buildings coloured by {measure["label"].lower()} within 500 m (per year)')
    fig.update_traces(marker=dict(size=7, opacity=0.85))
    style(fig, height=560)
    fig.update_layout(margin=dict(l=10, r=10, t=60, b=10),
                      coloraxis_colorbar=dict(title='per year', thickness=12))
    return fig


def size_vs_danger_figure(data, measure):
    """Cross-domain scatter: building size (housing) against nearby crash measure (transportation)."""
    buildings = data['buildings']
    if buildings.empty:
        return empty_figure()
    col = measure['building_col'] + '_per_year'
    plot_data = buildings[buildings['all_counted_units'] > 0]
    fig = px.scatter(plot_data, x='all_counted_units', y=col, color='reporting_construction_type',
                     color_discrete_map=TYPE_COLORS, log_x=True, opacity=0.55,
                     hover_name='project_name', hover_data={'borough': True},
                     labels={'all_counted_units': 'Affordable units in the building (log scale)',
                             col: f'{measure["label"]} within 500 m per year',
                             'reporting_construction_type': 'Type', 'borough': 'Borough'},
                     title=f'Building size vs {measure["label"].lower()} nearby')
    fig.update_traces(marker=dict(size=8, line=dict(width=1, color='#fcfcfb')))
    return style(fig)


def borough_year_figures(data, measure):
    """Two small charts on the same borough-year table: housing produced and crashes, 2022 onwards.
    Kept as two charts (not one with two y-axes) because the two measures have different scales."""
    borough_year = data['borough_year']
    crash_years = borough_year[borough_year['has_crash_data']]
    if crash_years.empty:
        return empty_figure('No crash data for these years (crash data starts in 2022)'), empty_figure('')

    housing_fig = px.line(crash_years, x='year', y='affordable_units_started', color='borough', markers=True,
                          color_discrete_map=BOROUGH_COLORS, category_orders={'borough': BOROUGHS},
                          labels={'affordable_units_started': 'Affordable units started', 'year': 'Year',
                                  'borough': 'Borough'},
                          title='Affordable units started per year')
    crash_fig = px.line(crash_years, x='year', y=measure['area_col'], color='borough', markers=True,
                        color_discrete_map=BOROUGH_COLORS, category_orders={'borough': BOROUGHS},
                        labels={measure['area_col']: measure['label'], 'year': 'Year', 'borough': 'Borough'},
                        title=f'{measure["label"]} per year')
    for fig in (housing_fig, crash_fig):
        fig.update_traces(line=dict(width=2), marker=dict(size=8))
        fig.update_xaxes(dtick=1)
        if crash_years['is_partial_year'].any():
            fig.add_annotation(x=crash_years['year'].max(), y=1.02, yref='paper', text='Jan–Jun only',
                               showarrow=False, font=dict(size=11, color='#52514e'))
        style(fig, height=380)
    return housing_fig, crash_fig


# ---------------------------------------------------------------- research questions
def make_q3(data, measure):
    """Q3: crash exposure of new construction vs preserved buildings, within each borough."""
    buildings = data['buildings']
    if buildings.empty:
        return empty_figure()
    col = measure['building_col'] + '_per_year'
    fig = px.box(buildings, x='borough', y=col, color='reporting_construction_type',
                 color_discrete_map=TYPE_COLORS, points=False,
                 category_orders={'borough': BOROUGHS, 'reporting_construction_type': CONSTRUCTION_TYPES},
                 labels={col: f'{measure["label"]} within 500 m per year', 'borough': 'Borough',
                         'reporting_construction_type': 'Type'},
                 title=f'{measure["label"]} near new vs preserved affordable buildings')
    fig.update_traces(line=dict(width=2))
    return style(fig)


def make_q4(data, measure):
    """Q4: median crash exposure of projects by the year they started, per borough and citywide."""
    buildings = data['buildings']
    if buildings.empty:
        return empty_figure()
    col = measure['building_col'] + '_per_year'
    by_borough = (buildings.groupby(['start_year', 'borough'])[col]
                  .agg(median='median', buildings='count').reset_index())
    citywide = (buildings.groupby('start_year')[col]
                .agg(median='median', buildings='count').reset_index().assign(borough='All NYC'))
    trend = pd.concat([by_borough, citywide])
    fig = px.line(trend, x='start_year', y='median', color='borough', markers=True,
                  color_discrete_map=BOROUGH_COLORS, category_orders={'borough': ['All NYC'] + BOROUGHS},
                  hover_data={'buildings': True},
                  labels={'start_year': 'Project start year', 'median': f'Median {measure["label"].lower()} per year',
                          'borough': 'Borough', 'buildings': 'Buildings started'},
                  title=f'Median {measure["label"].lower()} within 500 m, by project start year')
    fig.update_traces(line=dict(width=2), marker=dict(size=8))
    fig.update_traces(selector=dict(name='All NYC'), line=dict(width=4))
    return style(fig)


# One entry per research question. Teammates: add yours here (number, member, question, takeaway, figure).
RESEARCH_QUESTIONS = [
    {
        'number': 3,
        'member': 'Malak Ehab',
        'question': 'Is new affordable housing being built in safer areas than the existing buildings the city preserves?',
        'takeaway': ('No. In four of the five boroughs, new construction has more serious crashes nearby than '
                     'preserved buildings; the gap is largest in Queens (median 2.67 vs 0.89 per year). The Bronx '
                     'is the exception, with identical medians.'),
        'figure': make_q3,
    },
    {
        'number': 4,
        'member': 'Malak Ehab',
        'question': 'Over time, has the city been placing new affordable projects in safer or more dangerous areas?',
        'takeaway': ('Citywide, the location pattern has been stable since 2014 (median about 4.5–5.4 serious crashes '
                     'per year nearby). Only Brooklyn shows a small upward trend; the Bronx dip in 2020 comes from '
                     'Co-op City.'),
        'figure': make_q4,
    },
]
