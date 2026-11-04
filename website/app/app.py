"""
NYC Affordable Housing & Street Safety: interactive Dash website.

Run locally:   python app.py   then open http://127.0.0.1:8050
Deploy (Render): start command  gunicorn app:server
"""
import re

from dash import Dash, Input, Output, State, dcc, html

import charts

DATA = charts.load_data()
YEARS = sorted(set(DATA['buildings']['start_year']) | set(DATA['borough_year']['year']))

app = Dash(__name__, title='NYC Affordable Housing & Street Safety')
server = app.server  # used by gunicorn on Render


# ---------------------------------------------------------------- search
def parse_search(text):
    """Turn a free-text query such as 'Brooklyn 2022 new buildings fatal' into filter values."""
    text = (text or '').lower()
    boroughs = [b for b in charts.BOROUGHS if b.lower() in text or (b == 'Staten Island' and 'staten' in text)]
    years = sorted({int(y) for y in re.findall(r'\b(20[12]\d)\b', text) if int(y) in YEARS})

    types = []
    if re.search(r'\bnew\b|construction', text):
        types.append('New Construction')
    if 'preserv' in text:
        types.append('Preservation')

    measure = 'crashes'
    if re.search(r'fatal|death|deaths|killed|dead', text):
        measure = 'fatal'
    elif re.search(r'injur|severe|hurt', text):
        measure = 'severe'
    return boroughs, years, types, measure


# ---------------------------------------------------------------- layout helpers
def dropdown(id_, label, options, value, multi=True, placeholder='All'):
    return html.Div(className='filter', children=[
        html.Label(label, htmlFor=id_),
        dcc.Dropdown(id=id_, options=options, value=value, multi=multi, placeholder=placeholder, clearable=multi),
    ])


def kpi(id_, label):
    return html.Div(className='kpi', children=[html.Div(id=id_, className='kpi-value'), html.Div(label, className='kpi-label')])


def graph(id_):
    return dcc.Graph(id=id_, className='chart', config={'displaylogo': False, 'responsive': True})


app.layout = html.Div(className='page', children=[
    html.Header(className='header', children=[
        html.H1('Is NYC building affordable homes on its most dangerous streets?'),
        html.P('Affordable Housing Production by Building (HPD) linked with serious-injury crashes (NYC DOT SIRTA), '
               '2022–2026. Each building is matched to the serious crashes within 500 m.'),
    ]),

    # Filters
    html.Section(className='card controls', children=[
        html.Div(className='search-row', children=[
            dcc.Input(id='search-box', type='text', debounce=False, className='search-box',
                      placeholder='Search, e.g. "Brooklyn 2022 new buildings fatal" and press Enter'),
            html.Button('Apply search', id='search-button', className='button secondary'),
        ]),
        html.Div(id='search-feedback', className='feedback'),
        html.Div(className='filter-row', children=[
            dropdown('borough-filter', 'Borough', charts.BOROUGHS, []),
            dropdown('year-filter', 'Year (project start / crash year)', YEARS, []),
            dropdown('type-filter', 'Housing: construction type', charts.CONSTRUCTION_TYPES, []),
            dropdown('measure-filter', 'Transportation: crash measure',
                     [{'label': m['label'], 'value': k} for k, m in charts.MEASURES.items()],
                     'crashes', multi=False),
        ]),
        html.Div(className='button-row', children=[
            html.Button('Generate Report', id='generate-button', className='button primary'),
            html.Span(id='report-status', className='feedback'),
        ]),
    ]),

    # Key numbers
    html.Section(className='kpi-row', children=[
        kpi('kpi-buildings', 'affordable buildings'),
        kpi('kpi-units', 'affordable units'),
        kpi('kpi-median', 'median per year within 500 m (selected measure)'),
        kpi('kpi-fatal', 'of buildings have a fatal crash within 500 m'),
    ]),

    # Overview charts
    html.Section(className='card', children=[graph('map-chart')]),
    html.Section(className='card', children=[graph('scatter-chart')]),
    html.Section(className='grid', children=[
        html.Div(className='card', children=[graph('housing-year-chart')]),
        html.Div(className='card', children=[graph('crash-year-chart')]),
    ]),

    # Research questions (filled from charts.RESEARCH_QUESTIONS)
    html.H2('Research questions'),
    html.Div(id='research-questions'),

    # Story
    html.Section(className='card story', children=[
        html.H2('The story'),
        html.H3('Our question'),
        html.P('Affordable housing is home to New York\'s lowest-income residents, who walk and take transit more than '
               'anyone. We asked whether the city is building and preserving these homes near the streets where '
               'people are seriously injured or killed.'),
        html.H3('Key findings'),
        html.Ul([
            html.Li('The typical affordable building has 22 serious crashes within 500 m over 4.5 years (about one '
                    'every two to three months); only 64 of 7,470 buildings have none.'),
            html.Li('The most exposed buildings are all in Manhattan, mostly in Midtown West around Eighth Avenue and '
                    'Times Square.'),
            html.Li('New construction is located near more serious crashes than preserved buildings in four of five '
                    'boroughs, especially Queens.'),
            html.Li('Where the city places affordable projects has hardly changed since 2014.'),
        ]),
        html.H3('Limitations'),
        html.Ul([
            html.Li('SIRTA covers only serious-injury and fatal crashes, and only January 2022 to June 2026.'),
            html.Li('About 20% of buildings are confidential and have no location, so they are not on the map.'),
            html.Li('Nearby buildings share the same crashes, and all results are associations, not causes.'),
        ]),
        html.H3('Why it matters for NYC'),
        html.P('Street-safety improvements such as safer crossings and traffic calming could be planned together with '
               'new affordable developments, so the residents who depend most on walking are not placed on the most '
               'dangerous streets.'),
    ]),
    html.Footer('Data: NYC Open Data, Affordable Housing Production by Building (hg8x-zxpr) and SIRTA (xeqp-qz8h).',
                className='footer'),

    dcc.Store(id='search-trigger'),
])


# ---------------------------------------------------------------- callbacks
@app.callback(
    Output('borough-filter', 'value'), Output('year-filter', 'value'),
    Output('type-filter', 'value'), Output('measure-filter', 'value'),
    Output('search-feedback', 'children'), Output('search-trigger', 'data'),
    Input('search-button', 'n_clicks'), Input('search-box', 'n_submit'),
    State('search-box', 'value'),
    prevent_initial_call=True,
)
def apply_search(_clicks, _submits, text):
    """Search mode: read the query, set the dropdowns, and trigger a new report."""
    boroughs, years, types, measure = parse_search(text)
    found = []
    if boroughs:
        found.append('borough: ' + ', '.join(boroughs))
    if years:
        found.append('year: ' + ', '.join(map(str, years)))
    if types:
        found.append('type: ' + ', '.join(types))
    found.append('measure: ' + charts.MEASURES[measure]['label'])
    return boroughs, years, types, measure, 'Search applied → ' + ' | '.join(found), text


@app.callback(
    Output('kpi-buildings', 'children'), Output('kpi-units', 'children'),
    Output('kpi-median', 'children'), Output('kpi-fatal', 'children'),
    Output('map-chart', 'figure'), Output('scatter-chart', 'figure'),
    Output('housing-year-chart', 'figure'), Output('crash-year-chart', 'figure'),
    Output('research-questions', 'children'), Output('report-status', 'children'),
    Input('generate-button', 'n_clicks'), Input('search-trigger', 'data'),
    State('borough-filter', 'value'), State('year-filter', 'value'),
    State('type-filter', 'value'), State('measure-filter', 'value'),
)
def generate_report(_clicks, _search, boroughs, years, types, measure_key):
    """Generate Report: rebuild every number and chart from the selected filters."""
    measure = charts.MEASURES[measure_key or 'crashes']
    data = charts.apply_filters(DATA, boroughs, years, types)

    numbers = charts.kpis(data, measure)
    housing_fig, crash_fig = charts.borough_year_figures(data, measure)

    question_cards = [
        html.Section(className='card question', children=[
            html.Div(f"Question {q['number']} · {q['member']}", className='question-meta'),
            html.H3(q['question']),
            dcc.Graph(figure=q['figure'](data, measure), className='chart', config={'displaylogo': False, 'responsive': True}),
            html.P(q['takeaway'], className='takeaway'),
        ])
        for q in sorted(charts.RESEARCH_QUESTIONS, key=lambda q: q['number'])
    ]

    status = f"Report generated for {numbers['buildings']} buildings."
    return (numbers['buildings'], numbers['units'], numbers['median'], numbers['fatal_share'],
            charts.map_figure(data, measure), charts.size_vs_danger_figure(data, measure),
            housing_fig, crash_fig, question_cards, status)


if __name__ == '__main__':
    app.run(debug=True)
