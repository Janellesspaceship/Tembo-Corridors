"""
Load the finished pipeline outputs into BigQuery — the warehouse/serving
layer of the architecture, sitting between the local Python processing
and the dashboard/app.

Requires:
  1. A Google Cloud project (create one free at console.cloud.google.com
     if you don't have one for this project specifically).
  2. Authenticated locally via: gcloud auth application-default login
     (installs with Google Cloud SDK — see cloud.google.com/sdk/docs/install)
  3. pip install google-cloud-bigquery (already in requirements.txt)

Set PROJECT_ID and DATASET_ID below to your own values before running.
"""

import pandas as pd
from google.cloud import bigquery

PROJECT_ID = "africas-talking-bwai"     
DATASET_ID = "tembo_corridors"          # created automatically if it doesn't exist
LOCATION = "US"                          

TABLES_TO_LOAD = {
    "elephant_occurrences": "data/raw/elephant_occurrences_kenya.csv",
    "combined_priority_grid": "data/processed/combined_priority_grid.csv",
    "corridor_gaps": "data/processed/corridor_gaps.csv",
}


def ensure_dataset(client: bigquery.Client) -> None:
    dataset_ref = bigquery.DatasetReference(PROJECT_ID, DATASET_ID)
    try:
        client.get_dataset(dataset_ref)
        print(f"Dataset {DATASET_ID} already exists.")
    except Exception:
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = LOCATION
        client.create_dataset(dataset)
        print(f"Created dataset {DATASET_ID}.")


def load_table(client: bigquery.Client, table_name: str, csv_path: str) -> None:
    df = pd.read_csv(csv_path)
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{table_name}"

    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE",  # overwrite on rerun, safe for iteration
        autodetect=True,
    )
    job = client.load_table_from_dataframe(df, table_ref, job_config=job_config)
    job.result()  # wait for the load to finish

    table = client.get_table(table_ref)
    print(f"Loaded {table.num_rows} rows into {table_ref}")


def main() -> None:
    client = bigquery.Client(project=PROJECT_ID)
    ensure_dataset(client)

    for table_name, csv_path in TABLES_TO_LOAD.items():
        print(f"\nLoading {csv_path} -> {table_name} ...")
        load_table(client, table_name, csv_path)

    print("\nDone. Your BigQuery dataset now has:")
    for table_name in TABLES_TO_LOAD:
        print(f"  {PROJECT_ID}.{DATASET_ID}.{table_name}")
    print("\nYou can now connect Looker Studio (or any BI tool) directly "
          "to these tables, or query them with plain SQL in the BigQuery console.")


if __name__ == "__main__":
    main()