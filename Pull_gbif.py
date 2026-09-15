"""
Pull African elephant (Loxodonta africana) occurrence records for Kenya
from the GBIF occurrence-search API.

No GBIF account needed for this volume of data — this uses the public
search endpoint, paginated, rather than requesting an async bulk download.

Output: data/raw/elephant_occurrences_kenya.csv
"""

import time
import requests
import pandas as pd

GBIF_MATCH_URL = "https://api.gbif.org/v1/species/match"
GBIF_SEARCH_URL = "https://api.gbif.org/v1/occurrence/search"

SPECIES_NAME = "Loxodonta africana"
COUNTRY_CODE = "KE"          # ISO 3166-1 alpha-2 for Kenya
PAGE_SIZE = 300               # GBIF's max per page
OUTPUT_PATH = "data/raw/elephant_occurrences_kenya.csv"

# Columns we actually want to keep for the pipeline.
# Not every column will be populated for every record — that's expected
# and worth noting honestly in the article (a real "data reality check").
KEEP_COLUMNS = [
    "gbifID", "scientificName", "species", "genus", "family",
    "decimalLatitude", "decimalLongitude", "coordinateUncertaintyInMeters",
    "stateProvince", "county", "locality",
    "eventDate", "year", "month", "day",
    "basisOfRecord", "institutionCode", "datasetName",
]


def resolve_taxon_key(species_name: str) -> int:
    """Look up the GBIF backbone taxonKey for a species name."""
    resp = requests.get(GBIF_MATCH_URL, params={"name": species_name}, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if "usageKey" not in data:
        raise ValueError(f"Could not resolve a taxonKey for '{species_name}': {data}")
    print(f"Resolved '{species_name}' -> taxonKey={data['usageKey']} "
          f"(matched name: {data.get('scientificName')}, "
          f"match type: {data.get('matchType')})")
    return data["usageKey"]


def pull_occurrences(taxon_key: int, country_code: str) -> list[dict]:
    """Page through GBIF occurrence/search and collect all matching records."""
    records: list[dict] = []
    offset = 0

    while True:
        params = {
            "taxonKey": taxon_key,
            "country": country_code,
            "hasCoordinate": "true",
            "hasGeospatialIssue": "false",
            "limit": PAGE_SIZE,
            "offset": offset,
        }
        resp = requests.get(GBIF_SEARCH_URL, params=params, timeout=30)
        resp.raise_for_status()
        payload = resp.json()

        batch = payload.get("results", [])
        records.extend(batch)
        print(f"  fetched {len(batch)} records (offset={offset}, "
              f"running total={len(records)})")

        if payload.get("endOfRecords") or not batch:
            break

        offset += PAGE_SIZE
        time.sleep(0.3)  # be polite to the public API

    return records


def main() -> None:
    taxon_key = resolve_taxon_key(SPECIES_NAME)

    print(f"\nPulling occurrences for taxonKey={taxon_key}, "
          f"country={COUNTRY_CODE} ...")
    records = pull_occurrences(taxon_key, COUNTRY_CODE)
    print(f"\nTotal records pulled: {len(records)}")

    if not records:
        print("No records found — check the filters or try without "
              "hasGeospatialIssue=false to see if that's excluding everything.")
        return

    df = pd.json_normalize(records)
    existing_cols = [c for c in KEEP_COLUMNS if c in df.columns]
    missing_cols = [c for c in KEEP_COLUMNS if c not in df.columns]
    if missing_cols:
        print(f"Note: these expected columns were not present in the "
              f"response and will be skipped: {missing_cols}")

    df_clean = df[existing_cols].dropna(
        subset=["decimalLatitude", "decimalLongitude"]
    )

    # Quick, honest coverage summary — this is your "data reality check"
    print("\n--- Coverage summary ---")
    print(f"Records with valid coordinates: {len(df_clean)}")
    if "stateProvince" in df_clean.columns:
        print("\nBy stateProvince:")
        print(df_clean["stateProvince"].value_counts(dropna=False))
    if "datasetName" in df_clean.columns:
        print("\nBy contributing dataset:")
        print(df_clean["datasetName"].value_counts(dropna=False))
    if "year" in df_clean.columns:
        print("\nBy year (most recent 10):")
        print(df_clean["year"].value_counts(dropna=False).sort_index().tail(10))

    import os
    os.makedirs("data/raw", exist_ok=True)
    df_clean.to_csv(OUTPUT_PATH, index=False)
    print(f"\nSaved {len(df_clean)} records to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()