# Factory-to-Customer Shipping Route Efficiency Analysis
### Nassau Candy Distributor - Streamlit dashboard (college project)

An interactive dashboard that shows which **factory → state routes** ship fastest or slowest,
and how lead time changes by ship mode, region and state.

Built with only: **Python, Pandas, NumPy, Plotly, Streamlit**.

---

## Project structure

```
project/
├── app.py              # Streamlit page: sidebar, KPI cards, tabs and charts
├── utils.py            # Loading, cleaning, feature engineering, aggregations, insights
├── requirements.txt    # streamlit, pandas, numpy, plotly
├── README.md
└── data/
    └── Nassau_Candy.csv   # default dataset (used when nothing is uploaded)
```

`utils.py` has no Streamlit code, so you can test it in a normal Python shell.
`app.py` only draws things and calls functions from `utils.py`.

## How to run

1. Install Python 3.9 or newer and open a terminal in the `project` folder.
2. (Recommended) create a virtual environment:
   ```
   python -m venv venv
   venv\Scripts\activate          # Windows
   source venv/bin/activate       # macOS / Linux
   ```
3. Install the libraries:
   ```
   pip install -r requirements.txt
   ```
4. Start the app:
   ```
   streamlit run app.py
   ```
5. Your browser opens at http://localhost:8501. Press `Ctrl + C` in the terminal to stop.

The dashboard loads `data/Nassau_Candy.csv` automatically. To analyse another file,
use **Upload CSV file** in the sidebar (it needs the columns listed below).

## What the app does

| Feature | Where to find it |
|---|---|
| Upload CSV, data preview, dataset dimensions, cleaning report | **Data** tab |
| KPI cards: total orders, average lead time, total sales, total profit | top of the page |
| Filters: date range, region, state, ship mode (+ minimum orders per route) | sidebar |
| Top 10 fastest / bottom 10 slowest routes, route table, volume-vs-lead-time scatter | **Route Efficiency** tab |
| Lead time, order count and order share by ship mode | **Ship Modes** tab |
| State-wise map and bar chart, region-wise chart, factory map | **Geography** tab |
| Pick a route, see its statistics, timeline and shipment records | **Route Drilldown** tab |
| Fastest route, slowest route, best ship mode, worst region (automatic) | **Insights** tab |

Leave a sidebar filter empty to include everything.

## How the analysis works

* **Lead time** = `Ship Date - Order Date` (in days).
* **Factory** = looked up from the product name (mapping is in `utils.py`).
* **Route** = `Factory → State/Province`, e.g. `Sugar Shack → Texas`.
* **Orders** = number of unique Order IDs. **Avg Lead Time** is averaged over shipment rows.
* **Std Dev** = how much lead time varies on a route (higher = less predictable).
* **Efficiency Score** = `100 × (slowest − route) / (slowest − fastest)`. 100 is the fastest
  route, 0 the slowest, among the routes currently shown.
* **Minimum orders per route** (sidebar) hides routes with very few orders so a single
  lucky or unlucky shipment does not top the rankings.

### Cleaning rules (`utils.clean_data` / `utils.prepare_data`)

1. Remove exact duplicate rows.
2. Trim spaces in text columns; blank text becomes `Unknown`.
3. Fix product names such as `Wonka Bar -Scrumdiddlyumptious` to `Wonka Bar - Scrumdiddlyumptious`.
4. Missing/invalid numbers (Sales, Units, Cost, Gross Profit) become 0.
5. Dates are read as `DD-MM-YYYY` (also `YYYY-MM-DD` and `DD/MM/YYYY`); rows with unreadable dates are removed.
6. Rows whose product is not in the factory mapping are removed.
7. Rows with a negative lead time (shipped before ordered) are removed.

The Data tab shows how many rows each step removed.

### Required CSV columns

`Order Date, Ship Date, Ship Mode, Region, State/Province, City, Product Name, Division, Sales, Units, Cost, Gross Profit`
(`Order ID` is used to count orders; if it is missing, row numbers are used instead.)

## Important note about this dataset

In the supplied file, Ship Dates are **hundreds of days after** Order Dates (median about
1,274 days; values cluster around 910, 1,275 and 1,640 days - gaps of exactly one year).
Real candy shipping does not take years, so the Ship Date column looks shifted by whole
years. The app still follows the project formula and shows a warning banner. Because of this:

* Compare routes **relative to each other**; do not quote the numbers as real delivery times.
* Differences between ship modes are small (all about 1,310-1,340 days), so "best ship mode"
  is not strongly supported by this data. Mention this in your report.

Example output on the supplied file (routes with at least 5 orders):
fastest route `Secret Factory → Virginia` (1053 days, 5 orders), slowest route
`Wicked Choccy's → New Mexico` (1489 days, 14 orders), best ship mode `Standard Class`,
worst region `Interior`.

## Troubleshooting

* **`streamlit` is not recognised** - run `python -m streamlit run app.py` instead.
* **The US map is blank** - the map needs an internet connection; the bar charts always work.
* **"No data matches the current filters"** - widen the date range or clear a filter.
* **"Could not load the file"** - check the CSV has the required columns listed above.

## Possible improvements

Delay-frequency KPI with a lead-time threshold slider, route distance from the factory
coordinates, downloadable CSV of the route table.
