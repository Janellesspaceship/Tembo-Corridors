"""
Restore protected-area attributes (designation type, IUCN category note,
approximate size) that were lost when the pipeline switched from WDPA
(which had these fields) to OSM/Nominatim geocoding (which only returns
a name and a boundary polygon).

Values below are manually compiled from public general knowledge and,
where checked, live web sources — NOT pulled fresh from WDPA. Sizes are
approximate and should be spot-checked against protectedplanet.net if
precision matters for your final submission. IUCN category is marked
"Not formally reported" for private conservancies and county-managed
reserves where a standard category is not consistently assigned in
official records — this mirrors the actual pattern seen in this
project's own WDPA points-layer pull (Kenya's 2 point records came back
as "Not Applicable" / "Not Reported").

Input/Output: data/processed/protected_areas_kenya.geojson (updated in place)
"""

import geopandas as gpd

PATH = "data/processed/protected_areas_kenya.geojson"

# name -> (designation_type, iucn_category_note, approx_size_km2)
ATTRIBUTES = {
    "Masai Mara National Reserve, Kenya": (
        "National Reserve (county-managed, Narok County)", "Not formally reported", 1510),
    "Amboseli National Park, Kenya": (
        "National Park (KWS-managed)", "Category II (typical for KWS parks)", 392),
    "Chyulu Hills National Park, Kenya": (
        "National Park (KWS-managed)", "Category II (typical for KWS parks)", 471),
    "Tsavo East National Park, Kenya": (
        "National Park (KWS-managed)", "Category II (typical for KWS parks)", 13747),
    "Tsavo West National Park, Kenya": (
        "National Park (KWS-managed)", "Category II (typical for KWS parks)", 9065),
    "Ol Pejeta Conservancy, Kenya": (
        "Private, not-for-profit conservancy", "Not formally reported (IUCN Green List, not I-VI category)", 360),
    "Lewa Wildlife Conservancy, Kenya": (
        "Private conservancy", "Not formally reported", 250),
    "Borana Conservancy, Kenya": (
        "Private conservancy", "Not formally reported", 130),
    "Solio Game Reserve, Kenya": (
        "Private game reserve", "Not formally reported", 70),
    "Samburu National Reserve, Kenya": (
        "National Reserve (county-managed, Samburu County)", "Not formally reported", 165),
    "Buffalo Springs National Reserve, Kenya": (
        "National Reserve (county-managed, Isiolo County)", "Not formally reported", 131),
    "Shaba National Reserve, Kenya": (
        "National Reserve (county-managed, Isiolo County)", "Not formally reported", 239),
    "Meru National Park, Kenya": (
        "National Park (KWS-managed)", "Category II (typical for KWS parks)", 870),
}


def main() -> None:
    gdf = gpd.read_file(PATH)
    name_col = "query_name" if "query_name" in gdf.columns else "name"
    print(f"Loaded {len(gdf)} protected areas, matching on column '{name_col}'.")

    gdf["designation_type"] = gdf[name_col].map(lambda n: ATTRIBUTES.get(n, (None,))[0])
    gdf["iucn_category_note"] = gdf[name_col].map(lambda n: ATTRIBUTES.get(n, (None, None))[1])
    gdf["approx_size_km2"] = gdf[name_col].map(lambda n: ATTRIBUTES.get(n, (None, None, None))[2])

    unmatched = gdf[gdf["designation_type"].isna()][name_col].tolist()
    if unmatched:
        print(f"\nWarning: {len(unmatched)} reserve(s) had no attribute match "
              f"(name mismatch?): {unmatched}")

    gdf.to_file(PATH, driver="GeoJSON")
    print(f"\nUpdated {PATH} with designation_type, iucn_category_note, "
          f"and approx_size_km2 columns.")

    print("\nSummary:")
    print(gdf[[name_col, "designation_type", "iucn_category_note", "approx_size_km2"]]
          .to_string(index=False))


if __name__ == "__main__":
    main()