"""
Tembo Corridors — Streamlit app

Serves as both the project's dashboard (overview metrics, risk map) and
its interactive web app (filterable map, cell-level score explorer),
combined into one deliverable given the project timeline.

Run with: streamlit run app/streamlit_app.py
"""

import json

import geopandas as gpd
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Tembo Corridors", page_icon="🐘", layout="wide")

DATA_PATH = "data/processed/combined_priority_grid.geojson"
PROTECTED_AREAS_PATH = "data/processed/protected_areas_kenya.geojson"
CORRIDOR_GAPS_PATH = "data/processed/corridor_gaps.csv"


@st.cache_data
def load_data():
    return gpd.read_file(DATA_PATH)


@st.cache_data
def load_corridor_data():
    protected = gpd.read_file(PROTECTED_AREAS_PATH)
    gaps = pd.read_csv(CORRIDOR_GAPS_PATH)
    return protected, gaps


gdf = load_data()

st.title("🐘 Tembo Corridors")
st.caption(
    "Human-Elephant Conflict Risk & Priority Zones — Kenya's "
    "Amboseli–Tsavo–Laikipia–Samburu Corridor Landscape"
)

# --- Looker Studio Analytics Dashboard ---
LOOKER_STUDIO_URL = (
    "https://datastudio.google.com/reporting/"
    "b4b16df4-0a6f-4c18-8b82-787b3470a4e0"
)

st.link_button(
    "📊 Open Looker Studio Analytics Dashboard →",
    LOOKER_STUDIO_URL,
)

st.caption(
    "Use the Streamlit app for interactive spatial exploration and the "
    "Looker Studio dashboard for analytical summaries and key findings."
)

# --- Sidebar filters ---
st.sidebar.header("Filters")
show_only_priority = st.sidebar.checkbox(
    "Show only final priority zones (combined risk + corridor score, unprotected)",
    value=True,
)
settlement_options = sorted(gdf["nearest_settlement"].unique())
settlement_filter = st.sidebar.multiselect(
    "Filter by nearest settlement", options=settlement_options, default=[]
)
min_score = st.sidebar.slider("Minimum combined priority score", 0.0, 1.0, 0.0, 0.05)

filtered = gdf.copy()
if show_only_priority:
    filtered = filtered[filtered["final_priority_zone"]]
if settlement_filter:
    filtered = filtered[filtered["nearest_settlement"].isin(settlement_filter)]
filtered = filtered[filtered["combined_priority_score"] >= min_score]

# --- Top-line metrics ---
col1, col2, col3 = st.columns(3)
col1.metric("Total grid cells", len(gdf))
col2.metric("Final priority zones (risk + corridor, unprotected)",
            int(gdf["final_priority_zone"].sum()))
col3.metric("Cells matching current filters", len(filtered))

# --- Map ---
st.subheader("Combined Priority Map")
st.caption(
    "Color = combined priority score (70% conflict risk + 30% corridor "
    "criticality). This is the single ranked view RQ5 asks for — not just "
    "raw elephant density, and not just corridor fragility, but both "
    "together."
)
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
        color="combined_priority_score",
        color_continuous_scale="OrRd",
        range_color=(0, 1),
        center={"lat": center_lat, "lon": center_lon},
        zoom=6,
        opacity=0.7,
        hover_data=["nearest_settlement", "elephant_count",
                     "conflict_risk_score", "dist_to_critical_corridor_km",
                     "corridor_criticality_score", "inside_protected_area"],
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
with st.expander("How is the combined priority score calculated?"):
    st.markdown(
        """
        Every score here is a **documented, fixed-weight calculation** —
        nothing is trained or learned from the data. It's built in two layers:

        **Layer 1 — Conflict risk score** (per grid cell):
        - **40%** — Elephant presence (normalized occurrence density from GBIF records)
        - **30%** — Proximity to nearest settlement (closer = higher risk)
        - **30%** — Proximity to nearest road (closer = higher risk)

        **Layer 2 — Combined priority score** (this is RQ5's answer):
        - **70%** — Conflict risk score (above)
        - **30%** — Corridor criticality — proximity to a critical
          (≤60km gap) corridor between two protected areas

        A **final priority zone** is a cell in the **top 20%** of the
        combined score that currently sits **outside** any protected area —
        the actionable shortlist where real elephant presence, real human
        exposure, AND corridor fragility all line up.
        """
    )

# --- Ranked table ---
st.subheader("Ranked Zones")
display_cols = ["cell_id", "nearest_settlement", "elephant_count",
                 "conflict_risk_score", "corridor_criticality_score",
                 "combined_priority_score", "inside_protected_area"]
st.dataframe(
    filtered[display_cols].sort_values("combined_priority_score", ascending=False),
    use_container_width=True,
    hide_index=True,
)

# --- Single-cell explorer ---
st.subheader("Explore a specific zone")
if len(filtered) > 0:
    selected_cell = st.selectbox(
        "Select a cell ID",
        options=filtered.sort_values(
            "combined_priority_score", ascending=False
        )["cell_id"].tolist(),
    )
    cell_row = filtered[filtered["cell_id"] == selected_cell].iloc[0]

    c1, c2, c3 = st.columns(3)
    c1.metric("Combined Priority Score", f"{cell_row['combined_priority_score']:.2f}")
    c2.metric("Conflict Risk Score", f"{cell_row['conflict_risk_score']:.2f}")
    c3.metric("Corridor Criticality Score", f"{cell_row['corridor_criticality_score']:.2f}")

    c4, c5, c6 = st.columns(3)
    c4.metric("Elephant Occurrences", int(cell_row["elephant_count"]))
    c5.metric("Nearest Settlement", cell_row["nearest_settlement"])
    c6.metric("Distance to Critical Corridor",
              f"{cell_row['dist_to_critical_corridor_km']:.1f} km")

    st.write(
        f"**Inside a protected area:** "
        f"{'Yes' if cell_row['inside_protected_area'] else 'No'}"
    )
    if not cell_row["inside_protected_area"] and cell_row["final_priority_zone"]:
        st.error(
            "⚠️ This is a **final priority zone** — high combined risk + "
            "corridor criticality, currently no protection status."
        )

# --- Corridor Connectivity ---
st.divider()
st.subheader("Corridor Connectivity")
st.caption(
    "A simplified stand-in for full graph-theory corridor analysis: "
    "straight-line gaps between each pair of the 13 protected areas, "
    "flagging the narrowest as the most fragile/critical connections. "
    "See the README for why this was scoped down from a full "
    "betweenness-centrality network."
)

protected, gaps = load_corridor_data()

n_critical = int(gaps["critical"].sum())
col_a, col_b = st.columns(2)
col_a.metric("Reserve pairs analyzed", len(gaps))
col_b.metric("Critical corridors (≤60km gap)", n_critical)

# Bar chart of all gaps, narrowest first
gaps_sorted = gaps.sort_values("gap_km").copy()
gaps_sorted["pair_label"] = gaps_sorted["reserve_a"].str.replace(", Kenya", "") + \
    " ↔ " + gaps_sorted["reserve_b"].str.replace(", Kenya", "")

fig_gaps = px.bar(
    gaps_sorted,
    x="gap_km",
    y="pair_label",
    color="critical",
    color_discrete_map={True: "#d62728", False: "#c7c7c7"},
    orientation="h",
    height=max(400, len(gaps_sorted) * 18),
    labels={"gap_km": "Gap distance (km)", "pair_label": "", "critical": "Critical (≤60km)"},
)
fig_gaps.update_layout(yaxis={"categoryorder": "total descending"})
st.plotly_chart(fig_gaps, use_container_width=True)

# Map of reserves with lines drawn between critical-gap pairs
name_col = "name" if "name" in protected.columns else "query_name"
protected = protected.copy()
protected["centroid"] = protected.geometry.centroid
centroid_lookup = {
    row[name_col]: (row["centroid"].y, row["centroid"].x)
    for _, row in protected.iterrows()
}

fig_map_kwargs = dict(
    lat=[c[0] for c in centroid_lookup.values()],
    lon=[c[1] for c in centroid_lookup.values()],
    text=list(centroid_lookup.keys()),
    mode="markers+text",
    textposition="top center",
    marker=dict(size=10, color="#2ca02c"),
    name="Reserves",
)
try:
    reserve_trace = go.Scattermap(**fig_map_kwargs)
    line_trace_cls = go.Scattermap
    layout_kwargs = {
        "map_style": "carto-positron",
        "map_center": {"lat": -1.0, "lon": 37.0},
        "map_zoom": 5.5,
    }
except AttributeError:
    reserve_trace = go.Scattermapbox(**fig_map_kwargs)
    line_trace_cls = go.Scattermapbox
    layout_kwargs = {
        "mapbox_style": "carto-positron",
        "mapbox_center": {"lat": -1.0, "lon": 37.0},
        "mapbox_zoom": 5.5,
    }

corridor_fig = go.Figure()
for _, row in gaps[gaps["critical"]].iterrows():
    if row["reserve_a"] in centroid_lookup and row["reserve_b"] in centroid_lookup:
        lat_a, lon_a = centroid_lookup[row["reserve_a"]]
        lat_b, lon_b = centroid_lookup[row["reserve_b"]]
        corridor_fig.add_trace(line_trace_cls(
            lat=[lat_a, lat_b], lon=[lon_a, lon_b],
            mode="lines", line=dict(width=2, color="#d62728"),
            showlegend=False, hoverinfo="skip",
        ))
corridor_fig.add_trace(reserve_trace)
corridor_fig.update_layout(
    height=550,
    margin={"r": 0, "t": 0, "l": 0, "b": 0},
    **layout_kwargs,
)
st.plotly_chart(corridor_fig, use_container_width=True)

st.dataframe(
    gaps[gaps["critical"]].sort_values("gap_km"),
    use_container_width=True,
    hide_index=True,
)