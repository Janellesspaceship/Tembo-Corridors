"""
Pull protected-area boundaries for the specific reserves/conservancies
relevant to Kenya's Amboseli-Tsavo-Laikipia-Samburu elephant corridor
landscape — by name, via Nominatim geocoding (ox.geocode_to_gdf), rather
than a whole-country Overpass tag search.

Why this approach: a whole-country query for all of Kenya's protected
areas (a) is ~300x the recommended single-query area, so it gets split
into hundreds of sub-queries, and (b) failed outright here due to a
network-level timeout to overpass-api.de. Querying named places one at
a time is smaller, faster, hits Nominatim instead, and degrades
gracefully — if one name fails, the rest still succeed.

The reserve list below is scoped to match where the GBIF elephant
occurrence data was actually concentrated (Narok, Kajiado, Taita Taveta,
Laikipia, Isiolo, Samburu) — this is intentional, not a shortcut: your
project is about this specific corridor landscape, not all of Kenya.

Output: data/processed/protected_areas_kenya.geojson
"""

import os

import geopandas as gpd
import osmnx as ox
import pandas as pd

OUTPUT_PATH = "data/processed/protected_areas_kenya.geojson"

# Named reserves/conservancies covering the elephant corridor landscape.
# Add or remove names as needed — each is queried independently.
PLACE_NAMES = [
    "Masai Mara National Reserve, Kenya",
    "Amboseli National Park, Kenya",
    "Chyulu Hills National Park, Kenya",
    "Tsavo East National Park, Kenya",
    "Tsavo West National Park, Kenya",
    "Ol Pejeta Conservancy, Kenya",
    "Lewa Wildlife Conservancy, Kenya",
    "Borana Conservancy, Kenya",
    "Solio Game Reserve, Kenya",
    "Samburu National Reserve, Kenya",
    "Buffalo Springs National Reserve, Kenya",
    "Shaba National Reserve, Kenya",
    "Meru National Park, Kenya",
]


def main() -> None:
    results = []
    failed = []

    for name in PLACE_NAMES:
        try:
            print(f"Geocoding: {name} ...")
            gdf = ox.geocode_to_gdf(name)
            gdf["query_name"] = name
            results.append(gdf)
            print(f"  OK — got geometry type: {gdf.geometry.iloc[0].geom_type}")
        except Exception as e:
            print(f"  FAILED: {e}")
            failed.append(name)

    if not results:
        print("\nNo reserves could be geocoded at all — this points to a "
              "broader network issue (check your internet connection, VPN, "
              "or firewall settings) rather than a problem with specific "
              "place names.")
        return

    combined = gpd.GeoDataFrame(pd.concat(results, ignore_index=True))

    keep_cols = [c for c in
                 ["query_name", "display_name", "geometry"]
                 if c in combined.columns]
    combined_clean = combined[keep_cols]

    os.makedirs("data/processed", exist_ok=True)
    combined_clean.to_file(OUTPUT_PATH, driver="GeoJSON")

    print(f"\nSaved {len(combined_clean)} protected areas to {OUTPUT_PATH}")
    if failed:
        print(f"\nCould not geocode {len(failed)} name(s): {failed}")
        print("You can retry just these, adjust the spelling, or accept "
              "the partial result — the rest of the pipeline can proceed "
              "with what succeeded.")


if __name__ == "__main__":
    main()