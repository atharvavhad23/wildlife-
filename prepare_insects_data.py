import warnings

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder

warnings.filterwarnings("ignore")

RAW_FILE = "Koyna_insects_final.csv"
OUTPUT_FILE = "koyna_insects_regression_density.csv"

BASE_FEATURE_COLUMNS = [
    "coordinateUncertaintyInMeters",
    "day",
    "month",
    "year",
    "decade",
    "order_enc",
    "family_enc",
    "taxonRank_enc",
    "basisOfRecord_enc",
    "season_enc",
    "lat_grid",
    "lon_grid",
    "species_richness",
]


def _season_from_month(month: int) -> int:
    if month in (12, 1, 2):
        return 0
    if month in (3, 4, 5):
        return 1
    if month in (6, 7, 8):
        return 2
    return 3


def main() -> None:
    print("=" * 70)
    print("PROCESSING INSECTS DATASET FOR REGRESSION")
    print("=" * 70)

    df = pd.read_csv(RAW_FILE)
    print(f"Loaded raw data: {df.shape}")

    numeric_cols = [
        "decimalLatitude",
        "decimalLongitude",
        "coordinateUncertaintyInMeters",
        "day",
        "month",
        "year",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["decimalLatitude", "decimalLongitude", "day", "month", "year"]).copy()
    df["coordinateUncertaintyInMeters"] = df["coordinateUncertaintyInMeters"].fillna(
        df["coordinateUncertaintyInMeters"].median()
    )

    for col in ["order", "family", "taxonRank", "basisOfRecord", "species"]:
        df[col] = df[col].fillna("Unknown").astype(str)

    df["lat_grid"] = df["decimalLatitude"].round(1)
    df["lon_grid"] = df["decimalLongitude"].round(1)
    df["decade"] = (df["year"] // 10 * 10).astype(int)
    df["season_enc"] = df["month"].astype(int).apply(_season_from_month)

    richness = (
        df.groupby(["lat_grid", "lon_grid"])["species"]
        .nunique()
        .rename("species_richness")
    )
    df = df.join(richness, on=["lat_grid", "lon_grid"])

    cell_density = (
        df.groupby(["lat_grid", "lon_grid", "month", "year"])
        .size()
        .rename("obs_density")
    )
    family_diversity = (
        df.groupby(["lat_grid", "lon_grid", "month", "year"])["family"]
        .nunique()
        .rename("family_diversity")
    )
    df = df.join(cell_density, on=["lat_grid", "lon_grid", "month", "year"])
    df = df.join(family_diversity, on=["lat_grid", "lon_grid", "month", "year"])

    uncertainty_inverse = 1.0 / (1.0 + np.log1p(df["coordinateUncertaintyInMeters"].clip(lower=0)))
    seasonal_boost = np.where(df["season_enc"] == 2, 1.12, 1.0)

    # Derived density target from observed local abundance, richness, and data quality.
    df["insect_sighting_density"] = (
        0.62 * df["obs_density"]
        + 0.28 * df["species_richness"]
        + 0.18 * df["family_diversity"]
        + 2.4 * uncertainty_inverse
    ) * seasonal_boost

    for col in ["order", "family", "taxonRank", "basisOfRecord"]:
        encoder = LabelEncoder()
        df[f"{col}_enc"] = encoder.fit_transform(df[col])

    output_cols = BASE_FEATURE_COLUMNS + [
        "decimalLatitude",
        "decimalLongitude",
        "insect_sighting_density",
    ]

    df_out = df[output_cols].dropna().copy()
    df_out.to_csv(OUTPUT_FILE, index=False)

    print(f"Processed data saved: {OUTPUT_FILE}")
    print(f"Final shape: {df_out.shape}")
    print(
        "Target stats: "
        f"mean={df_out['insect_sighting_density'].mean():.3f}, "
        f"std={df_out['insect_sighting_density'].std():.3f}, "
        f"min={df_out['insect_sighting_density'].min():.3f}, "
        f"max={df_out['insect_sighting_density'].max():.3f}"
    )


if __name__ == "__main__":
    main()
