"""
app.py - Streamlit dashboard: Factory-to-Customer Shipping Route Efficiency
Nassau Candy Distributor (college project)

Run with:  streamlit run app.py
"""

import inspect
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

import utils

# Default dataset used when no file is uploaded
DATA_PATH = Path(__file__).parent / "data" / "Nassau_Candy.csv"

st.set_page_config(page_title="Nassau Candy - Route Efficiency", layout="wide")

# Newer Streamlit versions use width="stretch"; older ones use use_container_width=True
PLOTLY_HAS_WIDTH = "width" in inspect.signature(st.plotly_chart).parameters


# ----------------------------------------------------------------------
# Small chart helpers (so we do not repeat the same code)
# ----------------------------------------------------------------------

def show_chart(fig):
    """Display a Plotly figure so that it fills the page width."""
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10))
    if PLOTLY_HAS_WIDTH:
        st.plotly_chart(fig, width="stretch")
    else:
        st.plotly_chart(fig, use_container_width=True)


def bar_chart(data, category, value, title, horizontal=False, color=None, colors=None):
    """Bar chart (vertical or horizontal) with value labels on small charts.
    For horizontal bars the first row of `data` is drawn at the top."""
    labels = ".1f" if len(data) <= 15 else False
    if horizontal:
        fig = px.bar(data, x=value, y=category, orientation="h", color=color,
                     color_discrete_sequence=colors, text_auto=labels, title=title)
        fig.update_yaxes(autorange="reversed")
    else:
        fig = px.bar(data, x=category, y=value, color=color,
                     color_discrete_sequence=colors, text_auto=labels, title=title)
    return fig


# ----------------------------------------------------------------------
# Data loading (cached so the app stays fast when filters change)
# ----------------------------------------------------------------------

@st.cache_data(show_spinner="Loading and cleaning data...")
def load_and_prepare(file_bytes):
    """Read the CSV bytes, check columns, clean and add features."""
    raw = utils.read_csv_bytes(file_bytes)
    missing = utils.find_missing_columns(raw)
    if missing:
        raise ValueError("The CSV is missing these required columns: " + ", ".join(missing))
    df, report = utils.prepare_data(raw)
    if df.empty:
        raise ValueError("No valid rows are left after cleaning the data.")
    return raw.shape, raw.head(10), df, report


def get_file_bytes():
    """Use the uploaded CSV if there is one, otherwise the default file in data/."""
    uploaded = st.sidebar.file_uploader("Upload CSV file", type="csv")
    if uploaded is not None:
        return uploaded.getvalue()
    if DATA_PATH.exists():
        st.sidebar.caption("Using the default file: data/Nassau_Candy.csv")
        return DATA_PATH.read_bytes()
    return None


# ----------------------------------------------------------------------
# Sidebar filters
# ----------------------------------------------------------------------

def sidebar_filters(df):
    """Draw the filters and return the filtered data and the route setting."""
    st.sidebar.header("Filters")

    # Date range (the user may have picked only the first date so far)
    min_d, max_d = df["Order Date"].min().date(), df["Order Date"].max().date()
    dates = st.sidebar.date_input("Order date range", value=(min_d, max_d),
                                  min_value=min_d, max_value=max_d)
    if isinstance(dates, (tuple, list)):
        start = dates[0]
        end = dates[1] if len(dates) > 1 else max_d
    else:
        start, end = dates, dates

    # Leave a multiselect empty to include everything
    regions = st.sidebar.multiselect("Region", sorted(df["Region"].unique()))
    state_pool = df[df["Region"].isin(regions)] if regions else df
    states = st.sidebar.multiselect("State / Province", sorted(state_pool["State/Province"].unique()))
    modes = st.sidebar.multiselect("Ship Mode", sorted(df["Ship Mode"].unique()))
    st.sidebar.caption("Leave a filter empty to include all values.")

    st.sidebar.header("Route settings")
    min_orders = st.sidebar.slider("Minimum orders per route", 1, 50, 5,
                                   help="Routes with fewer orders are hidden from rankings.")
    return utils.apply_filters(df, start, end, regions, states, modes), min_orders


# ----------------------------------------------------------------------
# Page sections
# ----------------------------------------------------------------------

def show_kpis(df):
    """Four KPI cards."""
    k = utils.calc_kpis(df)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Orders", f"{k['Total Orders']:,}")
    c2.metric("Average Lead Time", f"{k['Average Lead Time']:.1f} days")
    c3.metric("Total Sales", f"${k['Total Sales']:,.0f}")
    c4.metric("Total Profit", f"${k['Total Profit']:,.0f}")


def tab_data(raw_shape, raw_preview, df, report):
    """Data preview, dimensions and cleaning report."""
    c1, c2 = st.columns(2)
    c1.metric("Uploaded file size", f"{raw_shape[0]:,} rows x {raw_shape[1]} columns")
    c2.metric("After cleaning", f"{len(df):,} rows x {df.shape[1]} columns")
    st.subheader("Data preview (first 10 rows of the file)")
    st.dataframe(raw_preview, hide_index=True)
    st.subheader("Cleaned data with new columns (Lead Time, Factory, Route)")
    st.dataframe(df.head(10), hide_index=True)
    with st.expander("Cleaning report"):
        st.dataframe(pd.DataFrame(list(report.items()), columns=["Step", "Rows"]), hide_index=True)


def tab_routes(df, min_orders):
    """Route efficiency dashboard."""
    routes = utils.route_summary(df, min_orders)
    if routes.empty:
        st.info("No routes have enough orders. Lower 'Minimum orders per route' in the sidebar.")
        return

    left, right = st.columns(2)
    with left:
        show_chart(bar_chart(routes.head(10), "Route", "Avg Lead Time",
                             "Top 10 fastest routes (avg days)", horizontal=True, colors=["#2e8b57"]))
    with right:
        show_chart(bar_chart(routes.tail(10).iloc[::-1], "Route", "Avg Lead Time",
                             "Bottom 10 slowest routes (avg days)", horizontal=True, colors=["#c0392b"]))

    st.subheader("Average lead time by route")
    st.caption("All routes, fastest first. Efficiency Score: 100 = fastest route, 0 = slowest route. "
               "Std Dev shows how much the lead time varies.")
    st.dataframe(routes, hide_index=True)

    left, right = st.columns(2)
    with left:
        fig = px.scatter(routes, x="Orders", y="Avg Lead Time", color="Factory",
                         hover_name="Route", hover_data=["Std Dev"],
                         title="Route volume vs. average lead time")
        show_chart(fig)
        st.caption("Routes in the top-right corner have many orders AND long lead times (bottlenecks).")
    with right:
        factories = utils.group_stats(df, "Factory").sort_values("Avg Lead Time")
        show_chart(bar_chart(factories, "Factory", "Avg Lead Time", "Average lead time by factory (days)"))


def tab_ship_modes(df):
    """Lead time and order count by ship mode."""
    modes = utils.group_stats(df, "Ship Mode").sort_values("Avg Lead Time")
    left, right = st.columns(2)
    with left:
        show_chart(bar_chart(modes, "Ship Mode", "Avg Lead Time", "Average lead time by ship mode (days)"))
    with right:
        show_chart(bar_chart(modes, "Ship Mode", "Orders", "Order count by ship mode"))

    left, right = st.columns(2)
    with left:
        show_chart(px.pie(modes, names="Ship Mode", values="Orders", title="Share of orders by ship mode"))
    with right:
        st.subheader("Ship mode summary")
        st.dataframe(modes, hide_index=True)


def tab_geography(df):
    """State-wise and region-wise average lead time."""
    st.subheader("State-wise average lead time")
    us_states = utils.state_map_data(df)
    if us_states.empty:
        st.info("No US states in the current selection, so the map is skipped.")
    else:
        fig = px.choropleth(us_states, locations="State Code", locationmode="USA-states",
                            color="Avg Lead Time", hover_name="State/Province", scope="usa",
                            color_continuous_scale="RdYlGn_r", title="Average lead time by US state (days)")
        show_chart(fig)
        st.caption("The map shows US states only and needs an internet connection. "
                   "The bar chart below also includes Canadian provinces.")

    states = utils.group_stats(df, "State/Province").sort_values("Avg Lead Time", ascending=False)
    show_chart(bar_chart(states, "State/Province", "Avg Lead Time", "Average lead time by state / province (days)"))

    left, right = st.columns(2)
    with left:
        regions = utils.group_stats(df, "Region").sort_values("Avg Lead Time", ascending=False)
        show_chart(bar_chart(regions, "Region", "Avg Lead Time", "Average lead time by region (days)"))
    with right:
        fig = px.scatter_geo(utils.factory_summary(df), lat="Latitude", lon="Longitude",
                             size="Orders", color="Avg Lead Time", hover_name="Factory",
                             scope="usa", title="Factory locations (size = orders)")
        show_chart(fig)


def tab_drilldown(df):
    """Pick one route and look at its statistics and shipment records."""
    routes = sorted(df["Route"].unique())
    route = st.selectbox("Select a route", routes)
    sub = df[df["Route"] == route]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Orders", f"{sub['Order ID'].nunique():,}")
    c2.metric("Average lead time", f"{sub['Lead Time'].mean():.1f} days")
    c3.metric("Fastest / slowest", f"{sub['Lead Time'].min()} / {sub['Lead Time'].max()} days")
    c4.metric("Std deviation", f"{sub['Lead Time'].std(ddof=0):.1f} days")
    c5, c6 = st.columns(2)
    c5.metric("Total sales", f"${sub['Sales'].sum():,.2f}")
    c6.metric("Total profit", f"${sub['Gross Profit'].sum():,.2f}")

    fig = px.scatter(sub, x="Order Date", y="Lead Time", color="Ship Mode",
                     hover_name="Order ID", title="Lead time of each shipment on this route")
    show_chart(fig)

    st.subheader("Shipment records")
    columns = ["Order ID", "Order Date", "Ship Date", "Ship Mode", "City", "State/Province",
               "Product Name", "Lead Time", "Sales", "Gross Profit"]
    st.dataframe(sub[columns].sort_values("Order Date"), hide_index=True)


def tab_insights(df, min_orders):
    """Automatically generated insights."""
    for label, headline, detail in utils.get_insights(df, min_orders):
        st.info(f"**{label}:** {headline}\n\n{detail}")
    st.caption("Insights follow the sidebar filters. Route insights ignore routes with fewer "
               "orders than 'Minimum orders per route'.")


# ----------------------------------------------------------------------
# Main program
# ----------------------------------------------------------------------

def main():
    st.title("Factory-to-Customer Shipping Route Efficiency")
    st.caption("Nassau Candy Distributor - route-level lead time analysis")

    file_bytes = get_file_bytes()
    if file_bytes is None:
        st.info("Upload a CSV file in the sidebar to begin.")
        st.stop()

    try:
        raw_shape, raw_preview, df_all, report = load_and_prepare(file_bytes)
    except Exception as error:  # show a friendly message instead of a crash
        st.error(f"Could not load the file: {error}")
        st.stop()

    df, min_orders = sidebar_filters(df_all)
    if df.empty:
        st.warning("No data matches the current filters. Please widen your selection.")
        st.stop()

    warning = utils.lead_time_warning(df_all)
    if warning:
        st.warning(warning)

    show_kpis(df)
    st.caption(f"Showing {len(df):,} of {len(df_all):,} rows after filters.")

    tabs = st.tabs(["Data", "Route Efficiency", "Ship Modes", "Geography", "Route Drilldown", "Insights"])
    with tabs[0]:
        tab_data(raw_shape, raw_preview, df_all, report)
    with tabs[1]:
        tab_routes(df, min_orders)
    with tabs[2]:
        tab_ship_modes(df)
    with tabs[3]:
        tab_geography(df)
    with tabs[4]:
        tab_drilldown(df)
    with tabs[5]:
        tab_insights(df, min_orders)


main()
