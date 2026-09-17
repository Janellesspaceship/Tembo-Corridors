"""
Clean and standardize the WDPA (World Database on Protected Areas) shapefiles
for Kenya, downloaded from protectedplanet.net.

Handles the standard WDPA export structure: separate "points" and "polygons"
shapefiles, which may be either a Kenya-only export OR the full global bulk
export (in which case we filter to Kenya here using the ISO3 country code).

Input:  data/raw/wdpa_kenya/*.shp   (both -points and -polygons shapefiles)
Output: data/processed/protected_areas_kenya.geojson

This is a cleaning/transform step only — no modeling, no ML.
"""

import glob
import os

import geopandas as gpd
import pandas as pd

RAW_DIR = "data/raw/wdpa_kenya"
OUTPUT_PATH = "data/processed/protected_areas_kenya.geojson"

# WDPA uses ISO3 country codes. Kenya = KEN.
COUNTRY_ISO3 = "KEN"

# Columns commonly present in WDPA shapefiles — actual column names can vary
# slightly by export, so the script checks what's really there before using it.
CANDIDATE_COLUMNS = {
    "name": ["NAME", "ORIG_NAME"],
    "designation": ["DESIG_ENG", "DESIG"],
    "iucn_category": ["IUCN_CAT"],
    "status": ["STATUS"],
    "status_year": ["STATUS_YR"],
    "reported_area_km2": ["REP_AREA"],
    "marine": ["MARINE"],
    "governance_type": ["GOV_TYPE"],
    "iso3": ["ISO3", "PARENT_ISO"],
}


def find_shapefiles(raw_dir: str) -> list[str]:
    matches = glob.glob(os.path.join(raw_dir, "*.shp"))
    if not matches:
        raise FileNotFoundError(
            f"No .shp files found in {raw_dir}. Did you extract the "
            f"downloaded zip(s) into this folder?"
        )
    print(f"Found {len(matches)} shapefile(s): {[os.path.basename(m) for m in matches]}")
    return matches


def resolve_columns(gdf: gpd.GeoDataFrame) -> dict:
    """Map our friendly column names to whatever's actually in this export."""
    resolved = {}
    for friendly_name, candidates in CANDIDATE_COLUMNS.items():
        for candidate in candidates:
            if candidate in gdf.columns:
                resolved[friendly_name] = candidate
                break
    return resolved


def load_and_filter(shp_path: str) -> gpd.GeoDataFrame:
    print(f"\nLoading {shp_path} ...")
    gdf = gpd.read_file(shp_path)
    print(f"  {len(gdf)} total records.")

    if gdf.crs is None:
        print("  Warning: no CRS found — assuming EPSG:4326.")
    elif gdf.crs.to_epsg() != 4326:
        print(f"  Reprojecting from {gdf.crs} to EPSG:4326 ...")
        gdf = gdf.to_crs(epsg=4326)

    col_map = resolve_columns(gdf)

    # Filter to Kenya if this looks like a global/multi-country export.
    if "iso3" in col_map:
        iso3_col = col_map["iso3"]
        before = len(gdf)
        gdf = gdf[gdf[iso3_col].astype(str).str.contains(COUNTRY_ISO3, na=False)]
        print(f"  Filtered by ISO3='{COUNTRY_ISO3}': {before} -> {len(gdf)} records.")
    else:
        print("  No ISO3/country column found — assuming this file is already "
              "Kenya-only. Double-check this assumption if the record count "
              "looks too large (thousands+ for Kenya alone would be unusual).")

    keep_cols = list(col_map.values()) + ["geometry"]
    gdf_clean = gdf[keep_cols].rename(columns={v: k for k, v in col_map.items()})
    return gdf_clean


def main() -> None:
    shp_paths = find_shapefiles(RAW_DIR)

    layers = []
    for shp_path in shp_paths:
        layer = load_and_filter(shp_path)
        geom_type = "points" if "points" in shp_path.lower() else (
            "polygons" if "polygons" in shp_path.lower() else "unknown")
        layer["geom_type"] = geom_type
        layers.append(layer)

    combined = gpd.GeoDataFrame(pd.concat(layers, ignore_index=True))

    # Exclude marine-only protected areas — not relevant to elephant range.
    if "marine" in combined.columns:
        before = len(combined)
        combined = combined[combined["marine"].astype(str) != "2"]  # 2 = marine-only in WDPA coding
        print(f"\nDropped {before - len(combined)} marine-only areas "
              f"({len(combined)} terrestrial/coastal remaining).")

    os.makedirs("data/processed", exist_ok=True)
    combined.to_file(OUTPUT_PATH, driver="GeoJSON")
    print(f"\nSaved {len(combined)} cleaned protected-area records to {OUTPUT_PATH}")

    print("\nBy geometry type (points vs polygons):")
    print(combined["geom_type"].value_counts())

    if "iucn_category" in combined.columns:
        print("\nBy IUCN category:")
        print(combined["iucn_category"].value_counts(dropna=False))


if __name__ == "__main__":
    main()