"""
RQ5: Combine conflict-risk score (per grid cell) with corridor
criticality (from the pairwise reserve-gap analysis) into ONE composite
priority score — this was the missing link between the two previously
separate outputs.

Method (documented, fixed weights, no fitting):
  1. For each pair of protected areas flagged "critical" (gap <= 60km in
     corridor_gap_analysis.py), draw a straight line between their
     centroids as an approximate corridor path.
  2. For each grid cell, measure distance to the nearest critical
     corridor line. Closer = higher corridor_criticality_score.
  3. combined_priority_score = 0.7 * conflict_risk_score
                              + 0.3 * corridor_criticality_score
  4. final_priority_zone = top 20% of combined_priority_score AND
     currently outside a protected area — this is the true, single
     ranked shortlist RQ5 asks for.

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

KM_PER_DEGREE = 111.0  # same equator-region approximation used elsewhere

RISK_GRID_PATH = "data/processed/conflict_risk_grid.geojson"
PROTECTED_AREAS_PATH = "data/processed/protected_areas_kenya.geojson"
CORRIDOR_GAPS_PATH = "data/processed/corridor_gaps.csv"

OUT_GEOJSON = "data/processed/combined_priority_grid.geojson"
OUT_CSV = "data/processed/combined_priority_grid.csv"

WEIGHT_RISK = 0.7
WEIGHT_CORRIDOR = 0.3


def normalize(series: pd.Series, invert: bool = False) -> pd.Series:
    lo, hi = series.min(), series.max()
    if hi == lo:
        return pd.Series(0.5, index=series.index)
    norm = (series - lo) / (hi - lo)
    return 1 - norm if invert else norm


def build_critical_corridor_lines(protected: gpd.GeoDataFrame, gaps: pd.DataFrame):
    name_col = "name" if "name" in protected.columns else "query_name"
    protected = protected.copy()
    protected["centroid"] = protected.geometry.centroid
    centroid_lookup = {row[name_col]: row["centroid"] for _, row in protected.iterrows()}

    lines = []
    for _, row in gaps[gaps["critical"]].iterrows():
        a, b = row["reserve_a"], row["reserve_b"]
        if a in centroid_lookup and b in centroid_lookup:
            pt_a, pt_b = centroid_lookup[a], centroid_lookup[b]
            lines.append(LineString([pt_a, pt_b]))
    print(f"Built {len(lines)} critical corridor line segments.")
    return lines


def main() -> None:
    grid = gpd.read_file(RISK_GRID_PATH)
    protected = gpd.read_file(PROTECTED_AREAS_PATH)
    gaps = pd.read_csv(CORRIDOR_GAPS_PATH)
    print(f"Loaded {len(grid)} scored cells, {len(protected)} protected areas, "
          f"{len(gaps)} reserve-pair gaps.")

    corridor_lines = build_critical_corridor_lines(protected, gaps)
    if not corridor_lines:
        print("No critical corridor lines found — check corridor_gaps.csv.")
        return

    from shapely.ops import unary_union
    corridor_union = unary_union(corridor_lines)

    centroids = grid.geometry.centroid
    grid["dist_to_critical_corridor_km"] = centroids.distance(corridor_union) * KM_PER_DEGREE

    grid["corridor_criticality_score"] = normalize(
        grid["dist_to_critical_corridor_km"], invert=True
    )

    grid["combined_priority_score"] = (
        WEIGHT_RISK * grid["conflict_risk_score"]
        + WEIGHT_CORRIDOR * grid["corridor_criticality_score"]
    )

    grid["final_priority_zone"] = (
        (~grid["inside_protected_area"])
        & (grid["combined_priority_score"] >= grid["combined_priority_score"].quantile(0.8))
    )

    # Force clean boolean dtype before writing — GeoJSON/pyogrio can
    # otherwise mishandle pandas boolean columns on write, silently
    # dropping or corrupting them.
    grid["inside_protected_area"] = grid["inside_protected_area"].astype(bool)
    grid["final_priority_zone"] = grid["final_priority_zone"].astype(bool)

    os.makedirs("data/processed", exist_ok=True)
    print(f"\nColumns about to be saved: {grid.columns.tolist()}")
    grid.to_file(OUT_GEOJSON, driver="GeoJSON")
    grid.drop(columns="geometry").to_csv(OUT_CSV, index=False)

    n_final = grid["final_priority_zone"].sum()
    print(f"\nSaved {len(grid)} cells with combined scoring to:")
    print(f"  {OUT_GEOJSON}")
    print(f"  {OUT_CSV}")
    print(f"\n{n_final} cells flagged as FINAL priority zones "
          f"(top 20% combined risk+corridor score, unprotected).")

    print("\nTop 10 FINAL priority zones (this is your RQ5 answer):")
    top10 = grid[grid["final_priority_zone"]].sort_values(
        "combined_priority_score", ascending=False
    ).head(10)
    cols = ["cell_id", "nearest_settlement", "elephant_count",
            "conflict_risk_score", "dist_to_critical_corridor_km",
            "corridor_criticality_score", "combined_priority_score"]
    print(top10[cols].to_string(index=False))


if __name__ == "__main__":
    main()