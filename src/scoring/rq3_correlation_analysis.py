"""
RQ3: Which spatial factors are most strongly associated with conflict
risk — proximity to protected-area edges, settlements, roads?

This is a descriptive-statistics answer (correlation + cross-tabulation),
not a prediction — consistent with the project's no-ML approach. It
reports actual numbers instead of just assuming the risk-score weights
were the right call.

Input:  data/processed/combined_priority_grid.csv
Output: printed to console (small enough not to need a separate file)
"""

import pandas as pd

DATA_PATH = "data/processed/combined_priority_grid.csv"


def main() -> None:
    df = pd.read_csv(DATA_PATH)
    print(f"Loaded {len(df)} scored cells.\n")

    # --- Correlation ---
    print("=== Correlation: elephant_count vs. distance factors ===")
    corr_settlement = df["elephant_count"].corr(df["dist_to_settlement_km"])
    corr_road = df["elephant_count"].corr(df["dist_to_road_km"])
    print(f"elephant_count vs dist_to_settlement_km: r = {corr_settlement:.3f}")
    print(f"elephant_count vs dist_to_road_km:        r = {corr_road:.3f}")
    print(
        "\n(Negative r means elephants tend to be found closer to "
        "settlements/roads than farther away — supporting the choice to "
        "weight those proximities in the risk score. A weak or positive "
        "r would have meant the opposite, and the weights should be "
        "revisited.)"
    )

    # --- Cross-tabulation ---
    print("\n=== Cross-tabulation: near vs far, average elephant count ===")
    near_settlement = df[df["dist_to_settlement_km"] <= df["dist_to_settlement_km"].median()]
    far_settlement = df[df["dist_to_settlement_km"] > df["dist_to_settlement_km"].median()]
    print(f"Cells NEAR a settlement (below median distance): "
          f"avg elephant_count = {near_settlement['elephant_count'].mean():.2f}")
    print(f"Cells FAR from a settlement (above median distance): "
          f"avg elephant_count = {far_settlement['elephant_count'].mean():.2f}")

    near_road = df[df["dist_to_road_km"] <= df["dist_to_road_km"].median()]
    far_road = df[df["dist_to_road_km"] > df["dist_to_road_km"].median()]
    print(f"\nCells NEAR a road (below median distance): "
          f"avg elephant_count = {near_road['elephant_count'].mean():.2f}")
    print(f"Cells FAR from a road (above median distance): "
          f"avg elephant_count = {far_road['elephant_count'].mean():.2f}")

    # --- Protected status cross-check ---
    print("\n=== Cross-tabulation: protected vs unprotected ===")
    grouped = df.groupby("inside_protected_area")["elephant_count"].agg(["mean", "count"])
    print(grouped)


if __name__ == "__main__":
    main()