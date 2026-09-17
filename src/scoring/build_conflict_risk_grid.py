"""
Build a grid over the elephant corridor study area and compute a
transparent, hand-weighted conflict-risk score per cell.

No model is trained here — every number is a documented calculation:
  1. Count elephant occurrences per grid cell (density signal)
  2. Measure distance from each cell to the nearest settlement and road
     (human-pressure signal)
  3. Flag whether each cell falls inside a protected area
  4. Combine into risk_score = 0.4*elephant + 0.3*settlement_proximity
     + 0.3*road_proximity — weights are fixed and documented, not fitted.

Distance note: this uses plain EPSG:4326 (lat/lon) coordinates and
converts degrees to kilometers with the standard ~111 km/degree
approximation. This region sits close to the equator (latitude roughly
-4.6 to 1.2), where that approximation holds reasonably well in both
directions — good enough for this analytics-level scoring, not intended
as survey-grade precision.

Inputs:
  data/raw/elephant_occurrences_kenya.csv
  data/processed/protected_areas_kenya.geojson
  data/processed/settlements_corridor.geojson
  data/processed/roads_corridor.geojson

Output:
  data/processed/conflict_risk_grid.geojson
  data/processed/conflict_risk_grid.csv   (same data, no geometry, for BigQuery load)
"""

import os

import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import box

KM_PER_DEGREE = 111.0  # equator-region approximation, documented above

ELEPHANTS_PATH = "data/raw/elephant_occurrences_kenya.csv"
PROTECTED_AREAS_PATH = "data/processed/protected_areas_kenya.geojson"
SETTLEMENTS_PATH = "data/processed/settlements_corridor.geojson"
ROADS_PATH = "data/processed/roads_corridor.geojson"

OUT_GEOJSON = "data/processed/conflict_risk_grid.geojson"
OUT_CSV = "data/processed/conflict_risk_grid.csv"

CELL_SIZE_DEG = 0.1        # ~11km cells — coarse enough to run fast, fine enough to be useful
STUDY_BUFFER_DEG = 0.5      # same buffer used when pulling roads/settlements

# --- Documented, fixed weights (NOT fitted to data) ---
WEIGHT_ELEPHANT = 0.4
WEIGHT_SETTLEMENT_PROXIMITY = 0.3
WEIGHT_ROAD_PROXIMITY = 0.3


def load_inputs():
    elephants_df = pd.read_csv(ELEPHANTS_PATH)
    elephants_gdf = gpd.GeoDataFrame(
        elephants_df,
        geometry=gpd.points_from_xy(
            elephants_df["decimalLongitude"], elephants_df["decimalLatitude"]
        ),
        crs="EPSG:4326",
    )
    protected = gpd.read_file(PROTECTED_AREAS_PATH)
    settlements = gpd.read_file(SETTLEMENTS_PATH)
    roads = gpd.read_file(ROADS_PATH)
    return elephants_gdf, protected, settlements, roads


def build_grid(protected: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    study_area = protected.geometry.union_all().buffer(STUDY_BUFFER_DEG)
    minx, miny, maxx, maxy = study_area.bounds

    xs = np.arange(minx, maxx, CELL_SIZE_DEG)
    ys = np.arange(miny, maxy, CELL_SIZE_DEG)

    cells = []
    for x in xs:
        for y in ys:
            cell = box(x, y, x + CELL_SIZE_DEG, y + CELL_SIZE_DEG)
            if cell.centroid.within(study_area):
                cells.append(cell)

    grid = gpd.GeoDataFrame(
        {"cell_id": range(len(cells))}, geometry=cells, crs="EPSG:4326"
    )
    print(f"Built grid: {len(grid)} cells within the study area "
          f"(cell size ~{CELL_SIZE_DEG * KM_PER_DEGREE:.0f}km).")
    return grid


def compute_features(grid, elephants, protected, settlements, roads) -> gpd.GeoDataFrame:
    grid = grid.copy()
    centroids = grid.geometry.centroid

    # 1. Elephant occurrence count per cell
    joined = gpd.sjoin(elephants, grid, how="left", predicate="within")
    counts = joined.groupby("cell_id").size()
    grid["elephant_count"] = grid["cell_id"].map(counts).fillna(0)

    # 2. Inside a protected area?
    protected_union = protected.geometry.union_all()
    grid["inside_protected_area"] = centroids.within(protected_union)

    # 3. Distance to nearest settlement (km)
    settlement_union = settlements.geometry.union_all()
    grid["dist_to_settlement_km"] = centroids.distance(settlement_union) * KM_PER_DEGREE

    # 4. Distance to nearest road (km)
    road_union = roads.geometry.union_all()
    grid["dist_to_road_km"] = centroids.distance(road_union) * KM_PER_DEGREE

    return grid


def normalize(series: pd.Series, invert: bool = False) -> pd.Series:
    """Min-max normalize to 0-1. If invert=True, closer/smaller becomes higher score."""
    lo, hi = series.min(), series.max()
    if hi == lo:
        return pd.Series(0.5, index=series.index)  # no variation — neutral score
    norm = (series - lo) / (hi - lo)
    return 1 - norm if invert else norm


def compute_risk_score(grid: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    grid = grid.copy()
    grid["elephant_score"] = normalize(grid["elephant_count"])
    grid["settlement_proximity_score"] = normalize(grid["dist_to_settlement_km"], invert=True)
    grid["road_proximity_score"] = normalize(grid["dist_to_road_km"], invert=True)

    grid["conflict_risk_score"] = (
        WEIGHT_ELEPHANT * grid["elephant_score"]
        + WEIGHT_SETTLEMENT_PROXIMITY * grid["settlement_proximity_score"]
        + WEIGHT_ROAD_PROXIMITY * grid["road_proximity_score"]
    )

    # Highest-priority zones: high risk AND currently outside protection
    grid["priority_zone"] = (
        (~grid["inside_protected_area"]) & (grid["conflict_risk_score"] >= grid["conflict_risk_score"].quantile(0.8))
    )

    return grid


def attach_nearest_settlement(grid: gpd.GeoDataFrame, settlements: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Tag each cell with the name of its nearest settlement, for readability
    in tables/maps — there are only 15 settlements, so a simple loop is fine."""
    grid = grid.copy()
    centroids = grid.geometry.centroid
    names = []
    for pt in centroids:
        dists = settlements.geometry.distance(pt)
        nearest_idx = dists.idxmin()
        names.append(settlements.loc[nearest_idx, "name"])
    grid["nearest_settlement"] = names
    return grid


def main() -> None:
    print("Loading inputs ...")
    elephants, protected, settlements, roads = load_inputs()
    print(f"  {len(elephants)} elephant points, {len(protected)} protected areas, "
          f"{len(settlements)} settlements, {len(roads)} road routes.")

    grid = build_grid(protected)
    grid = compute_features(grid, elephants, protected, settlements, roads)
    grid = compute_risk_score(grid)
    grid = attach_nearest_settlement(grid, settlements)

    os.makedirs("data/processed", exist_ok=True)
    grid.to_file(OUT_GEOJSON, driver="GeoJSON")
    grid.drop(columns="geometry").to_csv(OUT_CSV, index=False)

    print(f"\nSaved {len(grid)} scored cells to:")
    print(f"  {OUT_GEOJSON}")
    print(f"  {OUT_CSV}")

    n_priority = grid["priority_zone"].sum()
    print(f"\n{n_priority} cells flagged as top-priority "
          f"(top 20% conflict risk, currently outside protection).")

    print("\nTop 10 PRIORITY ZONES (high risk AND unprotected — the actionable list):")
    top_priority = grid[grid["priority_zone"]].sort_values(
        "conflict_risk_score", ascending=False
    ).head(10)
    print(top_priority[["cell_id", "nearest_settlement", "elephant_count",
                         "dist_to_settlement_km", "dist_to_road_km",
                         "conflict_risk_score"]].to_string(index=False))

    print("\n(For reference) Top 10 by raw risk score, including protected interior:")
    top10 = grid.sort_values("conflict_risk_score", ascending=False).head(10)
    print(top10[["cell_id", "nearest_settlement", "elephant_count",
                  "dist_to_settlement_km", "dist_to_road_km",
                  "inside_protected_area", "conflict_risk_score"]].to_string(index=False))


if __name__ == "__main__":
    main()