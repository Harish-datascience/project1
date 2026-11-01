"""
utils.py - Data loading, cleaning, feature engineering and analysis helpers
for the Nassau Candy shipping route efficiency project.

This file has NO Streamlit / Plotly code, so every function here can be
tested on its own with plain Python.
"""

import io

import numpy as np
import pandas as pd

# ----------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------

# Factory name -> (latitude, longitude)
FACTORY_COORDS = {
    "Lot's O' Nuts": (32.881893, -111.768036),
    "Wicked Choccy's": (32.076176, -81.088371),
    "Sugar Shack": (48.11914, -96.18115),
    "Secret Factory": (41.446333, -90.565487),
    "The Other Factory": (35.1175, -89.971107),
}

# Product name -> factory that makes it
PRODUCT_FACTORY = {
    "Wonka Bar - Nutty Crunch Surprise": "Lot's O' Nuts",
    "Wonka Bar - Fudge Mallows": "Lot's O' Nuts",
    "Wonka Bar - Scrumdiddlyumptious": "Lot's O' Nuts",
    "Wonka Bar - Milk Chocolate": "Wicked Choccy's",
    "Wonka Bar - Triple Dazzle Caramel": "Wicked Choccy's",
    "Laffy Taffy": "Sugar Shack",
    "SweeTARTS": "Sugar Shack",
    "Nerds": "Sugar Shack",
    "Fun Dip": "Sugar Shack",
    "Fizzy Lifting Drinks": "Sugar Shack",
    "Everlasting Gobstopper": "Secret Factory",
    "Lickable Wallpaper": "Secret Factory",
    "Wonka Gum": "Secret Factory",
    "Hair Toffee": "The Other Factory",
    "Kazookles": "The Other Factory",
}

# Columns the uploaded CSV must contain
REQUIRED_COLUMNS = [
    "Order Date", "Ship Date", "Ship Mode", "Region", "State/Province",
    "City", "Product Name", "Division", "Sales", "Units", "Cost", "Gross Profit",
]
TEXT_COLUMNS = ["Order ID", "Ship Mode", "Region", "State/Province", "City",
                "Product Name", "Division"]
NUMBER_COLUMNS = ["Sales", "Units", "Cost", "Gross Profit"]
DATE_FORMATS = ["%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y"]  # accepted date formats, tried in order

# US state name -> 2-letter code (needed for the choropleth map)
STATE_ABBR = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "District of Columbia": "DC", "Florida": "FL", "Georgia": "GA", "Hawaii": "HI",
    "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI",
    "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX",
    "Utah": "UT", "Vermont": "VT", "Virginia": "VA", "Washington": "WA",
    "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
}


# ----------------------------------------------------------------------
# 1. Data loading
# ----------------------------------------------------------------------

def read_csv_bytes(file_bytes):
    """Read a CSV from raw bytes. Tries UTF-8 first, then Latin-1."""
    try:
        df = pd.read_csv(io.BytesIO(file_bytes))
    except UnicodeDecodeError:
        df = pd.read_csv(io.BytesIO(file_bytes), encoding="latin-1")
    df.columns = df.columns.str.strip()  # remove accidental spaces in headers
    return df


def find_missing_columns(df):
    """Return the list of required columns that are not in the file."""
    return [col for col in REQUIRED_COLUMNS if col not in df.columns]


# ----------------------------------------------------------------------
# 2. Data cleaning
# ----------------------------------------------------------------------

def parse_dates(series):
    """Convert text to dates. The dataset uses DD-MM-YYYY; a few other clear formats are
    tried for rows that do not match. Anything unreadable becomes NaT (missing date)."""
    parsed = pd.to_datetime(series, format=DATE_FORMATS[0], errors="coerce")
    for fmt in DATE_FORMATS[1:]:
        parsed = parsed.fillna(pd.to_datetime(series, format=fmt, errors="coerce"))
    return parsed


def clean_data(df):
    """Fix types and missing values. Returns (clean_df, report_dict)."""
    df = df.copy()
    report = {"Rows loaded": len(df)}

    # Order ID is only used for counting orders; make one if it is missing
    if "Order ID" not in df.columns:
        df["Order ID"] = df.index.astype(str)

    # Remove exact duplicate rows
    before = len(df)
    df = df.drop_duplicates()
    report["Duplicate rows removed"] = before - len(df)

    # Text columns: fill blanks, trim spaces
    for col in TEXT_COLUMNS:
        df[col] = df[col].fillna("Unknown").astype(str).str.strip().replace("", "Unknown")

    # Standardize product names: "Wonka Bar -Scrumdiddlyumptious" -> "Wonka Bar - Scrumdiddlyumptious"
    df["Product Name"] = df["Product Name"].str.replace(r"\s*-\s*", " - ", regex=True)

    # Numeric columns: bad or missing values become 0
    for col in NUMBER_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    report["Missing numbers filled with 0"] = int(df[NUMBER_COLUMNS].isna().sum().sum())
    df[NUMBER_COLUMNS] = df[NUMBER_COLUMNS].fillna(0)

    # Dates are in DD-MM-YYYY format; unreadable dates become NaT and are dropped
    for col in ["Order Date", "Ship Date"]:
        df[col] = parse_dates(df[col])
    before = len(df)
    df = df.dropna(subset=["Order Date", "Ship Date"])
    report["Rows with invalid/missing dates removed"] = before - len(df)

    return df, report


# ----------------------------------------------------------------------
# 3. Feature engineering
# ----------------------------------------------------------------------

def add_features(df):
    """Add Lead Time, Factory and Route columns."""
    df = df.copy()
    df["Lead Time"] = (df["Ship Date"] - df["Order Date"]).dt.days
    df["Factory"] = df["Product Name"].map(PRODUCT_FACTORY)
    df["Route"] = df["Factory"] + " → " + df["State/Province"]
    return df


def prepare_data(raw_df):
    """Run the whole pipeline: clean -> add features -> remove invalid rows.
    Returns (ready_df, report_dict)."""
    df, report = clean_data(raw_df)
    df = add_features(df)

    # Products we cannot map to a factory have no route, so drop them
    before = len(df)
    df = df.dropna(subset=["Factory"])
    report["Rows with unknown product/factory removed"] = before - len(df)

    # A shipment cannot leave before it was ordered -> negative lead time is invalid
    before = len(df)
    df = df[df["Lead Time"] >= 0]
    report["Rows with negative lead time removed"] = before - len(df)

    report["Rows after cleaning"] = len(df)
    return df.reset_index(drop=True), report


def lead_time_warning(df):
    """Return a warning text if lead times look unrealistic, else None."""
    median = df["Lead Time"].median()
    if median > 60:
        return (f"Data note: the median lead time in this file is {median:,.0f} days, far longer "
                "than real candy shipping. The Ship Date values look offset from the Order Date "
                "values (by whole years), so read the numbers as comparisons between routes, "
                "not as real delivery times.")
    return None


# ----------------------------------------------------------------------
# 4. Filtering and KPIs
# ----------------------------------------------------------------------

def apply_filters(df, start, end, regions, states, modes):
    """Filter by order date range and (optional) lists. An empty list means 'all'."""
    mask = (df["Order Date"] >= pd.Timestamp(start)) & (df["Order Date"] <= pd.Timestamp(end))
    if regions:
        mask &= df["Region"].isin(regions)
    if states:
        mask &= df["State/Province"].isin(states)
    if modes:
        mask &= df["Ship Mode"].isin(modes)
    return df[mask]


def calc_kpis(df):
    """Headline numbers for the KPI cards."""
    return {
        "Total Orders": int(df["Order ID"].nunique()),
        "Average Lead Time": float(np.mean(df["Lead Time"])),
        "Total Sales": float(df["Sales"].sum()),
        "Total Profit": float(df["Gross Profit"].sum()),
    }


# ----------------------------------------------------------------------
# 5. Aggregations
# ----------------------------------------------------------------------

def group_stats(df, column):
    """Orders, average lead time, sales and profit for each value of `column`
    (used for ship mode, state, region and factory)."""
    stats = df.groupby(column).agg(**{
        "Orders": ("Order ID", "nunique"),
        "Avg Lead Time": ("Lead Time", "mean"),
        "Total Sales": ("Sales", "sum"),
        "Total Profit": ("Gross Profit", "sum"),
    }).reset_index()
    return stats.round(2)


def route_summary(df, min_orders=1):
    """One row per route (Factory → State), sorted fastest to slowest.
    Efficiency Score: 100 = fastest route, 0 = slowest route."""
    routes = df.groupby(["Route", "Factory", "State/Province"]).agg(**{
        "Orders": ("Order ID", "nunique"),
        "Avg Lead Time": ("Lead Time", "mean"),
        "Std Dev": ("Lead Time", "std"),   # variability (NaN if only one shipment)
    }).reset_index()
    routes["Std Dev"] = routes["Std Dev"].fillna(0)
    routes = routes[routes["Orders"] >= min_orders].copy()
    if routes.empty:
        return routes

    fastest, slowest = routes["Avg Lead Time"].min(), routes["Avg Lead Time"].max()
    if slowest == fastest:
        routes["Efficiency Score"] = 100.0
    else:
        score = 100 * (slowest - routes["Avg Lead Time"]) / (slowest - fastest)
        routes["Efficiency Score"] = np.clip(score, 0, 100)

    routes = routes.round(2).sort_values(["Avg Lead Time", "Route"])
    return routes.reset_index(drop=True)


def factory_summary(df):
    """Factory stats plus latitude/longitude (for the factory map)."""
    stats = group_stats(df, "Factory")
    coords = pd.DataFrame(
        [(name, lat, lon) for name, (lat, lon) in FACTORY_COORDS.items()],
        columns=["Factory", "Latitude", "Longitude"],
    )
    return stats.merge(coords, on="Factory", how="left")


def state_map_data(df):
    """State stats with 2-letter codes. Canadian provinces have no code, so they are dropped."""
    stats = group_stats(df, "State/Province")
    stats["State Code"] = stats["State/Province"].map(STATE_ABBR)
    return stats.dropna(subset=["State Code"])


# ----------------------------------------------------------------------
# 6. Automatic insights
# ----------------------------------------------------------------------

def orders_text(n):
    """1 order / 5 orders"""
    return f"{n} order" + ("" if n == 1 else "s")


def get_insights(df, min_orders=1):
    """Return a list of (label, headline, detail) tuples for the Insights tab."""
    routes = route_summary(df, min_orders)
    if routes.empty:  # min_orders too high -> use all routes
        routes = route_summary(df, 1)
    modes = group_stats(df, "Ship Mode").sort_values("Avg Lead Time")
    regions = group_stats(df, "Region").sort_values("Avg Lead Time")

    fast, slow = routes.iloc[0], routes.iloc[-1]
    best_mode, worst_region = modes.iloc[0], regions.iloc[-1]
    return [
        ("Fastest route", fast["Route"],
         f"{fast['Avg Lead Time']:.1f} days on average across {orders_text(fast['Orders'])}"),
        ("Slowest route", slow["Route"],
         f"{slow['Avg Lead Time']:.1f} days on average across {orders_text(slow['Orders'])}"),
        ("Best ship mode", best_mode["Ship Mode"],
         f"lowest average lead time: {best_mode['Avg Lead Time']:.1f} days ({orders_text(best_mode['Orders'])})"),
        ("Worst-performing region", worst_region["Region"],
         f"highest average lead time: {worst_region['Avg Lead Time']:.1f} days ({orders_text(worst_region['Orders'])})"),
    ]
