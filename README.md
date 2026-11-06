# NYC Affordable Housing & Street Safety

**Data Engineering and Visualization — Winter 2026, Milestone 1**

Is New York City building and preserving affordable homes near its most dangerous streets? This project links
NYC's **Affordable Housing Production by Building** (HPD) with **serious-injury and fatal crashes** (NYC DOT SIRTA)
by counting the serious crashes within 500 m of every affordable building, and presents the results in an
interactive Dash website.

- **Live website:** https://renadraafat.pythonanywhere.com
- **Notebook:** [`nootebook/milestone1.ipynb`](nootebook/milestone1.ipynb)

## Datasets

| Domain | Dataset | Link |
|---|---|---|
| Housing | Affordable Housing Production by Building (NYC HPD) | https://data.cityofnewyork.us/d/hg8x-zxpr |
| Transportation | Serious Injury Response, Tracking & Analysis Program, SIRTA (NYC DOT) | https://data.cityofnewyork.us/d/xeqp-qz8h |

## Repository structure

```
nyc-housing-transport/
├── nootebook/
│   └── milestone1.ipynb            # EDA, cleaning, integration, post-integration cleaning, research questions
├── website/app/
│   ├── app.py                      # Dash layout, filters, search mode, Generate Report button
│   ├── charts.py                   # data loading, filtering and all charts (overview + 10 research questions)
│   ├── requirements.txt            # Python libraries
│   ├── assets/style.css            # website styling (loaded automatically by Dash)
│   └── data/
│       ├── buildings_integrated.csv    # one row per affordable building, with crashes within 500 m
│       └── borough_year.csv            # housing and crashes per borough and year
└── README.md
```

The two CSV files are exported at the end of section 5 of the notebook. The website only reads them; all cleaning
and integration happen in the notebook.

## Setup: running the notebook

1. Open `nootebook/milestone1.ipynb` in Google Colab (File → Upload notebook, or open it from GitHub).
2. Run **Runtime → Run all**. The datasets are downloaded directly from NYC Open Data using their dataset IDs,
   so no files need to be uploaded. If NYC Open Data is temporarily unavailable (HTTP 503), wait a few minutes and
   run again.
3. Section 5 writes `buildings_integrated.csv` and `borough_year.csv`; download them from the Files panel
   (folder icon on the left) to update the website data.

## Setup: running the website locally

Requires Python 3.10 or newer.

```bash
git clone https://github.com/renadrafat200-svg/nyc-housing-transport.git
cd nyc-housing-transport/website/app
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:8050 in a browser.

## Deployment (PythonAnywhere, free account)

The website is deployed on PythonAnywhere's free Beginner plan.

1. In a PythonAnywhere **Bash console**, clone the repository and create a virtual environment that reuses the
   libraries PythonAnywhere already provides (this keeps the account within its 512 MB disk quota):
   ```bash
   git clone https://github.com/renadrafat200-svg/nyc-housing-transport.git
   mkvirtualenv --system-site-packages --python=$(which python3.11) dashenv
   pip install --no-cache-dir dash==2.18.2
   ```
2. On the **Web** tab: *Add a new web app* → *Manual configuration* → *Python 3.11*.
3. Set **Virtualenv** to `/home/<username>/.virtualenvs/dashenv`.
4. Replace the contents of the **WSGI configuration file** with:
   ```python
   import os
   import sys

   path = '/home/<username>/nyc-housing-transport/website/app'
   if path not in sys.path:
       sys.path.insert(0, path)
   os.chdir(path)

   from app import server as application
   ```
5. Click **Reload** and open `https://<username>.pythonanywhere.com`.

**Updating the live site:** after pushing changes to GitHub, run
`cd ~/nyc-housing-transport && git pull` in a Bash console and click **Reload** on the Web tab.
Free sites must be renewed once a month with the **Run until 1 month from today** button on the Web tab.

The website can also be deployed on Render or any host that runs Python: the start command is
`gunicorn app:server` from the `website/app` folder.

## Website features

- **Dropdown filters:** borough, year, housing construction type, and transportation crash measure
  (serious crashes, severe injuries, fatalities).
- **Search mode:** typing a query such as `Brooklyn 2022 new buildings fatal` sets the filters automatically.
- **Generate Report button:** updates every number, chart and summary from the selected filters.
- **Charts:** map, line charts, heatmap, bubble chart, box plots, bar and stacked bar charts, scatter plot,
  all interactive (hover, zoom, filter updates).
- **10 research questions**, two per team member, and a **story section** with the question, key findings,
  limitations and why it matters for NYC.

## Team members and contributions

Member	Name	ID	Research questions	Contributions
1	Nadeen Yasser	16007617	Q1, Q2	Section 4: Spatial integration using a 500-metre radius, filtering highway-related crashes, creating the borough–year dataset; research questions 1 and 2, including income-group crash exposure and identifying double-burden ZIP codes.
2	Renad Raafat	16002716	Q3, Q4	Dataset selection; notebook sections 1–3 (dataset overview, EDA and pre-integration cleaning); research questions 3 and 4; Dash website development; deployment on PythonAnywhere; GitHub repository management; documentation and notebook sections 7 and 8.
3	Malak Ehab	16004428	Q5, Q6	Section 5: Post-integration data validation and cleaning, checking missing values, aggregate totals and unusual records; research questions 5 and 6, analysing fatal-crash exposure and comparing affordable housing across danger categories.
4	Joudy Hagar	16001246	Q7, Q8	Research questions 7 and 8: Comparing affordable housing production shares with serious-crash shares across boroughs, and analysing year-to-year changes in housing production and crash numbers from 2022 to 2025.
5	Noor Eldin	[16009523]	Q9, Q10	Research questions 9 and 10: Examining the relationship between building size and nearby crash exposure using Spearman correlation, identifying the top 10% most exposed buildings and visualising their geographical locations.
AI assistance used in the project is documented in section 7 of the notebook.
