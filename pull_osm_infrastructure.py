"""
Pull roads, settlements, and cropland from OpenStreetMap, scoped to the
elephant corridor study area — defined as the buffered envelope around
the 13 protected areas already pulled, not all of Kenya.

This is a deliberate scope decision: WorldPop raster processing was
dropped in favor of OSM settlement/cropland proximity as the human-
pressure proxy, given the project timeline. It also reuses a much
smaller query area than the earlier whole-country attempt that failed,
which should make this far more reliable.

Inputs:  data/processed/protected_areas_kenya.geojson
Outputs: data/processed/roads_corridor.geojson
         data/processed/settlements_corridor.geojson
         data/processed/cropland_corridor.geojson
"""

import os

import geopandas as gpd
import osmnx as ox

PROTECTED_AREAS_PATH = "data/processed/protected_areas_kenya.geojson"
BUFFER_DEGREES = 0.5  # ~55km at the equator — wide enough to catch corridors between reserves

ROADS_OUT = "data/processed/roads_corridor.geojson"
SETTLEMENTS_OUT = "data/processed/settlements_corridor.geojson"
CROPLAND_OUT = "data/processed/cropland_corridor.geojson"

SETTLEMENT_TAGS = {"place": ["city", "town", "village", "hamlet"]}
CROPLAND_TAGS = {"landuse": ["farmland", "orchard", "plantation"]}


def build_study_area() -> "gpd.GeoSeries":
    protected = gpd.read_file(PROTECTED_AREAS_PATH)
    print(f"Loaded {len(protected)} protected areas to build study area from.")

    # Union all reserve boundaries, then buffer outward to capture the
    # corridor space between them (not just the reserves themselves).
    unified = protected.geometry.union_all()
    study_area = unified.buffer(BUFFER_DEGREES)
    print(f"Study area bounds (west, south, east, north): {study_area.bounds}")
    return study_area


def pull_roads(study_area) -> None:
    print("\nPulling drivable road network within the study area "
          "(this may take a few minutes) ...")
    try:
        graph = ox.graph_from_polygon(study_area, network_type="drive")
        edges = ox.graph_to_gdfs(graph, nodes=False)
        edges.to_file(ROADS_OUT, driver="GeoJSON")
        print(f"  Saved {len(edges)} road segments to {ROADS_OUT}")
    except Exception as e:
        print(f"  FAILED to pull roads: {e}")
        print("  If this times out, try again in a few minutes, or reduce "
              "BUFFER_DEGREES to shrink the query area further.")


def pull_features(study_area, tags: dict, out_path: str, label: str) -> None:
    print(f"\nPulling {label} within the study area ...")
    try:
        gdf = ox.features_from_polygon(study_area, tags)
        gdf = gdf[gdf.geometry.geom_type.isin(
            ["Point", "Polygon", "MultiPolygon"])]
        keep_cols = [c for c in gdf.columns
                     if c in ["name", *tags.keys(), "geometry"]]
        gdf[keep_cols].to_file(out_path, driver="GeoJSON")
        print(f"  Saved {len(gdf)} {label} features to {out_path}")
    except Exception as e:
        print(f"  FAILED to pull {label}: {e}")


def main() -> None:
    os.makedirs("data/processed", exist_ok=True)
    study_area = build_study_area()

    pull_roads(study_area)
    pull_features(study_area, SETTLEMENT_TAGS, SETTLEMENTS_OUT, "settlements")
    pull_features(study_area, CROPLAND_TAGS, CROPLAND_OUT, "cropland")

    print("\nDone. Check which of the three outputs succeeded above — "
          "partial success is fine, we can proceed with whatever came "
          "through and retry the rest separately if needed.")


if __name__ == "__main__":
    main()