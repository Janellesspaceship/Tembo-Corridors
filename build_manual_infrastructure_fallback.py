"""
FALLBACK ONLY — use this if pull_osm_infrastructure.py's live Overpass
queries keep failing due to network connectivity issues.

Builds a settlements layer and a simplified roads layer from a manually
compiled list of the major towns and highways actually relevant to the
Amboseli-Tsavo-Laikipia-Samburu-Mara corridor landscape.

IMPORTANT — document this honestly in the README/article: these are
approximate reference coordinates for known towns and simplified
straight-line highway routes, not survey-grade OSM data. This is a
deliberate, stated scope trade-off made under a hard time constraint,
not a hidden shortcut. If time allows later, re-run the live OSM pull
to replace this with full-resolution data.

Outputs: data/processed/settlements_corridor.geojson
         data/processed/roads_corridor.geojson
"""

import os

import geopandas as gpd
from shapely.geometry import Point, LineString

os.makedirs("data/processed", exist_ok=True)

# --- Major towns near the corridor (approximate town-center coordinates) ---
SETTLEMENTS = [
    {"name": "Loitokitok", "lat": -2.9767, "lon": 37.5088},
    {"name": "Kimana", "lat": -2.8770, "lon": 37.5240},
    {"name": "Emali", "lat": -2.2333, "lon": 37.5000},
    {"name": "Mtito Andei", "lat": -2.6833, "lon": 38.1667},
    {"name": "Voi", "lat": -3.3961, "lon": 38.5561},
    {"name": "Taveta", "lat": -3.4000, "lon": 37.6833},
    {"name": "Isiolo", "lat": 0.3546, "lon": 37.5822},
    {"name": "Archer's Post", "lat": 0.6314, "lon": 37.6702},
    {"name": "Wamba", "lat": 0.9833, "lon": 37.3167},
    {"name": "Maralal", "lat": 1.0968, "lon": 36.6980},
    {"name": "Nanyuki", "lat": 0.0167, "lon": 37.0733},
    {"name": "Nyahururu", "lat": 0.0369, "lon": 36.3628},
    {"name": "Narok", "lat": -1.0833, "lon": 35.8667},
    {"name": "Kilgoris", "lat": -1.0167, "lon": 34.8667},
    {"name": "Meru", "lat": 0.0500, "lon": 37.6500},
]

# --- Major highways as simplified multi-point routes (not full geometry) ---
ROADS = {
    "A109 Nairobi-Mombasa Highway (via Tsavo)": [
        (37.5000, -2.2333),  # Emali
        (38.1667, -2.6833),  # Mtito Andei
        (38.5561, -3.3961),  # Voi
    ],
    "B3 Emali-Loitokitok Road (toward Amboseli)": [
        (37.5000, -2.2333),  # Emali
        (37.5240, -2.8770),  # Kimana
        (37.5088, -2.9767),  # Loitokitok
    ],
    "A2 Nairobi-Isiolo-Moyale Highway (Great North Road)": [
        (37.0733, 0.0167),   # Nanyuki
        (37.5822, 0.3546),   # Isiolo
        (37.6702, 0.6314),   # Archer's Post
    ],
    "Narok-Mara Road (B3/C12)": [
        (35.8667, -1.0833),  # Narok
        (34.8667, -1.0167),  # Kilgoris direction
    ],
}


def main() -> None:
    # Settlements
    settlements_gdf = gpd.GeoDataFrame(
        SETTLEMENTS,
        geometry=[Point(s["lon"], s["lat"]) for s in SETTLEMENTS],
        crs="EPSG:4326",
    )
    settlements_gdf.to_file(
        "data/processed/settlements_corridor.geojson", driver="GeoJSON"
    )
    print(f"Saved {len(settlements_gdf)} manually compiled settlements "
          f"to data/processed/settlements_corridor.geojson")

    # Roads
    road_records = [
        {"name": name, "geometry": LineString(coords)}
        for name, coords in ROADS.items()
    ]
    roads_gdf = gpd.GeoDataFrame(road_records, crs="EPSG:4326")
    roads_gdf.to_file(
        "data/processed/roads_corridor.geojson", driver="GeoJSON"
    )
    print(f"Saved {len(roads_gdf)} manually compiled road routes "
          f"to data/processed/roads_corridor.geojson")

    print("\nReminder: this is a stated fallback (manual, approximate "
          "coordinates), not live OSM data. Note this explicitly in the "
          "README's data sources / limitations section.")


if __name__ == "__main__":
    main()