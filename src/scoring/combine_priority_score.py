"""
Close RQ5: combine the conflict-risk score with corridor criticality into
one composite priority score — previously these were two separate outputs
(conflict_risk_grid and corridor_gaps).

Method (documented, fixed weights — no fitting):
  1. Build a line segment between each pair of protected areas flagged
     "critical" in corridor_gaps.csv (gap <= 60km).
  2. For each grid cell, measure distance to the nearest critical-corridor
     line segment.
  3. corridor_criticality_score = inverse-normalized distance (closer = higher)
  4. combined_priority_score = 0.6 * conflict_risk_score
                              + 0.4 * corridor_criticality_score
  5. top_priority_zone = top 20% of combined_priority_score AND
                          currently outside a protected area

Inputs:
  data/processed/conflict_risk_grid.geojson
  data/processed/protected_areas_kenya.geojson
  data/processed/corridor_gaps.csv

Outputs:
  data/processed/combined_priority_grid.geojson
  data/processed/combined_priority_grid.csv
"""

import os

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString

KM_PER_DEGREE = 111.0  # same equator-region approximation used throughout

RISK_GRID_PATH = "data/processed/conflict_risk_grid.geojson"
PROTECTED_AREAS_PATH = "data/processed/protected_areas_kenya.geojson"
CORRIDOR_GAPS_PATH = "data/processed/corridor_gaps.csv"

OUT_GEOJSON = "data/processed/combined_priority_grid.geojson"
OUT_CSV = "data/processed/combined_priority_grid.csv"

WEIGHT_CONFLICT_RISK = 0.6
WEIGHT_CORRIDOR_CRITICALITY = 0.4


def build_critical_corridor_lines(protected: gpd.GeoDataFrame, gaps: pd.DataFrame):
    name_col = "name" if "name" in protected.columns else "query_name"
    protected = protected.copy()
    protected["centroid"] = protected.geometry.centroid
    centroid_lookup = {row[name_col]: row["centroid"] for _, row in protected.iterrows()}

    lines = []
    for _, row in gaps[gaps["critical"]].iterrows():
        a, b = row["reserve_a"], row["reserve_b"]
        if a in centroid_lookup and b in centroid_lookup:
            lines.append(LineString([centroid_lookup[a], centroid_lookup[b]]))
    print(f"Built {len(lines)} critical corridor line segments.")
    return lines


def normalize(series: pd.Series, invert: bool = False) -> pd.Series:
    lo, hi = series.min(), series.max()
    if hi == lo:
        return pd.Series(0.5, index=series.index)
    norm = (series - lo) / (hi - lo)
    return 1 - norm if invert else norm


def main() -> None:
    grid = gpd.read_file(RISK_GRID_PATH)
    protected = gpd.read_file(PROTECTED_AREAS_PATH)
    gaps = pd.read_csv(CORRIDOR_GAPS_PATH)
    print(f"Loaded {len(grid)} grid cells, {len(protected)} protected areas, "
          f"{len(gaps)} reserve-pair gaps ({gaps['critical'].sum()} critical).")

    corridor_lines = build_critical_corridor_lines(protected, gaps)
    if not corridor_lines:
        print("No critical corridor lines found — check corridor_gaps.csv.")
        return

    centroids = grid.geometry.centroid
    dist_to_corridor_km = centroids.apply(
        lambda pt: min(pt.distance(line) for line in corridor_lines) * KM_PER_DEGREE
    )
    grid["dist_to_critical_corridor_km"] = dist_to_corridor_km
    grid["corridor_criticality_score"] = normalize(dist_to_corridor_km, invert=True)

    grid["combined_priority_score"] = (
        WEIGHT_CONFLICT_RISK * grid["conflict_risk_score"]
        + WEIGHT_CORRIDOR_CRITICALITY * grid["corridor_criticality_score"]
    )

    threshold = grid["combined_priority_score"].quantile(0.8)
    grid["top_priority_zone"] = (
        (~grid["inside_protected_area"]) & (grid["combined_priority_score"] >= threshold)
    )

    os.makedirs("data/processed", exist_ok=True)
    grid.to_file(OUT_GEOJSON, driver="GeoJSON")
    grid.drop(columns="geometry").to_csv(OUT_CSV, index=False)

    print(f"\nSaved {len(grid)} cells with combined scores to:")
    print(f"  {OUT_GEOJSON}")
    print(f"  {OUT_CSV}")

    n_top = grid["top_priority_zone"].sum()
    print(f"\n{n_top} cells flagged as TOP PRIORITY "
          f"(top 20% combined score, currently unprotected).")

    print("\nTop 15 combined priority zones:")
    top15 = grid[grid["top_priority_zone"]].sort_values(
        "combined_priority_score", ascending=False
    ).head(15)
    print(top15[["cell_id", "nearest_settlement", "conflict_risk_score",
                  "dist_to_critical_corridor_km", "corridor_criticality_score",
                  "combined_priority_score"]].to_string(index=False))


if __name__ == "__main__":
    main()