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

FONTS = ('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700'
         '&family=Public+Sans:wght@400;500;600;700&display=swap')
app = Dash(__name__, title='NYC Affordable Housing & Street Safety', external_stylesheets=[FONTS])
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


def street_sign(text):
    """Section heading styled like an NYC street name sign."""
    return html.H2(html.Span(text, className='sign'), className='section-heading')


def graph(id_):
    return dcc.Graph(id=id_, className='chart', config={'displaylogo': False, 'responsive': True})


app.layout = html.Div(className='site', children=[
    html.Header(className='hero', children=[
        html.Div(className='hero-inner', children=[
            html.H1('Is NYC building affordable homes on its most dangerous streets?'),
            html.P('We matched every affordable housing building the city financed or preserved since 2014 with the '
                   'serious-injury and fatal crashes within 500 m of it, a six-minute walk, from January 2022 to June 2026.',
                   className='hero-lede'),
            html.P('Sources: Affordable Housing Production by Building (HPD) and the Serious Injury Response, Tracking '
                   '& Analysis Program (NYC DOT).', className='hero-source'),
        ]),
        html.Div(className='crosswalk', **{'aria-hidden': 'true'}),
    ]),

    html.Main(className='page', children=[
    # Filters
    html.Section(className='controls', children=[
        html.Div(className='search-row', children=[
            dcc.Input(id='search-box', type='text', debounce=False, className='search-box',
                      placeholder='Search, e.g. "Brooklyn 2022 new buildings fatal", then press Enter'),
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
    street_sign('Overview'),
    html.Section(className='card', children=[graph('map-chart')]),
    html.Section(className='grid', children=[
        html.Div(className='card', children=[graph('housing-year-chart')]),
        html.Div(className='card', children=[graph('crash-year-chart')]),
    ]),

    # Research questions (filled from charts.RESEARCH_QUESTIONS)
    street_sign('Research questions'),
    html.P('Ten questions, two per team member. Every chart and summary updates with the filters and the '
           'Generate Report button.', className='section-intro'),
    html.Div(id='research-questions'),

    # Story
    street_sign('The story'),
    html.Section(className='story', children=[
        html.H3('Our question'),
        html.P('Affordable housing is home to New York\'s lowest-income residents, who walk and take transit more than '
               'anyone. We asked whether the city is building and preserving these homes near the streets where '
               'people are seriously injured or killed.'),
        html.H3('Key findings'),
        html.Ul([
            html.Li('The typical affordable building has 22 serious crashes within 500 m over 4.5 years (about one '
                    'every two to three months); only 64 of 7,470 buildings have none.'),
            html.Li('Almost half of all affordable units (47%) are in high or very high exposure, and one in four '
                    'buildings had a fatal crash within 500 m.'),
            html.Li('Exposure is concentrated in the Bronx and Manhattan: 15 ZIP codes, mainly in the South and West '
                    'Bronx and East Harlem, combine the most affordable housing with the most dangerous streets.'),
            html.Li('New construction is located near more serious crashes than preserved buildings in four of five '
                    'boroughs, especially Queens.'),
            html.Li('In the Bronx, the deepest-affordability housing is the most exposed; in Brooklyn and Queens it is '
                    'the least exposed.'),
            html.Li('Where the city places affordable projects has hardly changed since 2014, and rising housing '
                    'production since 2022 has not come with more serious crashes (except in Queens).'),
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
    Output('map-chart', 'figure'),
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

    question_cards = []
    for q in sorted(charts.RESEARCH_QUESTIONS, key=lambda q: q['number']):
        meta = html.Div(className='question-meta', children=[
            html.Span(f"Q{q['number']}", className='q-sign'),
            html.Span(charts.MEMBERS[q['member']], className='q-member'),
        ])
        if q['figure'] is None:
            question_cards.append(html.Section(className='card question placeholder', children=[
                meta, html.P('To be added.', className='takeaway')]))
            continue
        summary = q['summary'](data, measure) if q['summary'] else ''
        question_cards.append(html.Section(className='card question', children=[
            meta,
            html.H3(q['question']),
            dcc.Graph(figure=q['figure'](data, measure), className='chart',
                      config={'displaylogo': False, 'responsive': True}),
            html.P(summary, className='summary') if summary else None,
            html.P(q['interpretation'], className='takeaway') if q['interpretation'] else None,
        ]))

    status = f"Report generated for {numbers['buildings']} buildings."
    return (numbers['buildings'], numbers['units'], numbers['median'], numbers['fatal_share'],
            charts.map_figure(data, measure),
            housing_fig, crash_fig, question_cards, status)


if __name__ == '__main__':
    app.run(debug=True)
