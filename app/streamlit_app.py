"""
Tembo Corridors — Streamlit app

Serves as both the project's dashboard (overview metrics, risk map) and
its interactive web app (filterable map, cell-level score explorer),
combined into one deliverable given the project timeline.

Run with: streamlit run app/streamlit_app.py
"""

import json

import geopandas as gpd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Tembo Corridors", page_icon="🐘", layout="wide")

DATA_PATH = "data/processed/conflict_risk_grid.geojson"


@st.cache_data
def load_data():
    return gpd.read_file(DATA_PATH)


gdf = load_data()

st.title("🐘 Tembo Corridors")
st.caption(
    "Human-Elephant Conflict Risk & Priority Zones — Kenya's "
    "Amboseli–Tsavo–Laikipia–Samburu Corridor Landscape"
)

# --- Sidebar filters ---
st.sidebar.header("Filters")
show_only_priority = st.sidebar.checkbox(
    "Show only priority zones (high risk & unprotected)", value=True
)
settlement_options = sorted(gdf["nearest_settlement"].unique())
settlement_filter = st.sidebar.multiselect(
    "Filter by nearest settlement", options=settlement_options, default=[]
)
min_risk = st.sidebar.slider("Minimum risk score", 0.0, 1.0, 0.0, 0.05)

filtered = gdf.copy()
if show_only_priority:
    filtered = filtered[filtered["priority_zone"]]
if settlement_filter:
    filtered = filtered[filtered["nearest_settlement"].isin(settlement_filter)]
filtered = filtered[filtered["conflict_risk_score"] >= min_risk]

# --- Top-line metrics ---
col1, col2, col3 = st.columns(3)
col1.metric("Total grid cells", len(gdf))
col2.metric("Priority zones (high risk, unprotected)", int(gdf["priority_zone"].sum()))
col3.metric("Cells matching current filters", len(filtered))

# --- Map ---
st.subheader("Conflict Risk Map")
if len(filtered) > 0:
    geojson = json.loads(filtered.to_json())
    center_lat = filtered.geometry.centroid.y.mean()
    center_lon = filtered.geometry.centroid.x.mean()

    # Plotly renamed choropleth_mapbox -> choropleth_map in newer versions
    # (Mapbox GL license change). Try the new name first, fall back to the
    # old one so this works regardless of which Plotly version is installed.
    map_kwargs = dict(
        data_frame=filtered,
        geojson=geojson,
        locations="cell_id",
        featureidkey="properties.cell_id",
        color="conflict_risk_score",
        color_continuous_scale="OrRd",
        range_color=(0, 1),
        center={"lat": center_lat, "lon": center_lon},
        zoom=6,
        opacity=0.7,
        hover_data=["nearest_settlement", "elephant_count",
                     "dist_to_settlement_km", "dist_to_road_km",
                     "inside_protected_area"],
    )
    try:
        fig = px.choropleth_map(map_style="carto-positron", **map_kwargs)
    except AttributeError:
        fig = px.choropleth_mapbox(mapbox_style="carto-positron", **map_kwargs)
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0}, height=600)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("No cells match the current filters — try loosening them.")

# --- How the score works (transparency, no black box) ---
with st.expander("How is the conflict risk score calculated?"):
    st.markdown(
        """
        Every score here is a **documented, fixed-weight calculation** —
        nothing is trained or learned from the data:

        - **40%** — Elephant presence (normalized occurrence density from GBIF records)
        - **30%** — Proximity to nearest settlement (closer = higher risk)
        - **30%** — Proximity to nearest road (closer = higher risk)

        A **priority zone** is a cell in the **top 20%** of risk scores that
        currently sits **outside** any protected area — these are the cells
        with both real elephant presence and real human exposure, and no
        formal protection. They're the actionable shortlist for mitigation:
        fencing, early-warning systems, or corridor protection easements.
        """
    )

# --- Ranked table ---
st.subheader("Ranked Zones")
display_cols = ["cell_id", "nearest_settlement", "elephant_count",
                 "dist_to_settlement_km", "dist_to_road_km",
                 "inside_protected_area", "conflict_risk_score"]
st.dataframe(
    filtered[display_cols].sort_values("conflict_risk_score", ascending=False),
    use_container_width=True,
    hide_index=True,
)

# --- Single-cell explorer ---
st.subheader("Explore a specific zone")
if len(filtered) > 0:
    selected_cell = st.selectbox(
        "Select a cell ID",
        options=filtered.sort_values("conflict_risk_score", ascending=False)["cell_id"].tolist(),
    )
    cell_row = filtered[filtered["cell_id"] == selected_cell].iloc[0]

    c1, c2, c3 = st.columns(3)
    c1.metric("Conflict Risk Score", f"{cell_row['conflict_risk_score']:.2f}")
    c2.metric("Elephant Occurrences", int(cell_row["elephant_count"]))
    c3.metric("Nearest Settlement", cell_row["nearest_settlement"])

    c4, c5 = st.columns(2)
    c4.metric("Distance to Settlement", f"{cell_row['dist_to_settlement_km']:.1f} km")
    c5.metric("Distance to Road", f"{cell_row['dist_to_road_km']:.1f} km")

    st.write(
        f"**Inside a protected area:** "
        f"{'Yes' if cell_row['inside_protected_area'] else 'No'}"
    )
    if not cell_row["inside_protected_area"] and cell_row["priority_zone"]:
        st.error(
            "⚠️ This is a flagged **priority zone** — high conflict risk, "
            "currently no protection status."
        )