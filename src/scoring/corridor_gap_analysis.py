"""
Simplified corridor-criticality analysis: for each pair of protected areas,
measure the straight-line gap between them and flag the narrowest gaps as
the most critical/fragile corridors.

This is a deliberately simplified stand-in for a full graph-theory
betweenness-centrality analysis (which needs a much denser habitat-patch
network than the 13 named reserves this project has time to build) — it
answers the same underlying question ("which corridors are narrowest and
most at risk of being severed?") with a much smaller, faster calculation.
Document this scope decision explicitly in the README/article.

Input:  data/processed/protected_areas_kenya.geojson
Output: data/processed/corridor_gaps.csv
"""

import os
from itertools import combinations

import geopandas as gpd
import pandas as pd

KM_PER_DEGREE = 111.0  # same equator-region approximation used elsewhere

INPUT_PATH = "data/processed/protected_areas_kenya.geojson"
OUTPUT_PATH = "data/processed/corridor_gaps.csv"

# A corridor gap under this width is flagged as critical/at-risk —
# adjust based on what the actual distribution of gaps looks like.
CRITICAL_GAP_KM = 60


def main() -> None:
    protected = gpd.read_file(INPUT_PATH)
    print(f"Loaded {len(protected)} protected areas.")

    name_col = "name" if "name" in protected.columns else "query_name"

    results = []
    for (i, row_a), (j, row_b) in combinations(protected.iterrows(), 2):
        gap_deg = row_a.geometry.distance(row_b.geometry)
        gap_km = gap_deg * KM_PER_DEGREE
        results.append({
            "reserve_a": row_a[name_col],
            "reserve_b": row_b[name_col],
            "gap_km": round(gap_km, 1),
            "critical": gap_km <= CRITICAL_GAP_KM,
        })

    gaps_df = pd.DataFrame(results).sort_values("gap_km")

    os.makedirs("data/processed", exist_ok=True)
    gaps_df.to_csv(OUTPUT_PATH, index=False)
    print(f"\nSaved {len(gaps_df)} reserve-pair gaps to {OUTPUT_PATH}")

    n_critical = gaps_df["critical"].sum()
    print(f"\n{n_critical} pairs flagged as critical corridors "
          f"(gap <= {CRITICAL_GAP_KM}km):")
    print(gaps_df[gaps_df["critical"]].to_string(index=False))

    print("\nAll gaps, narrowest first:")
    print(gaps_df.head(15).to_string(index=False))


if __name__ == "__main__":
    main()