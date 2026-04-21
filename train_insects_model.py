import warnings

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import RobustScaler

warnings.filterwarnings("ignore")

DATA_FILE = "koyna_insects_regression_density.csv"
MODEL_FILE = "insects_model.pkl"
SCALER_FILE = "insects_scaler.pkl"
FEATURE_FILE = "insects_feature_names.pkl"
METADATA_FILE = "insects_metadata.pkl"
IMPORTANCE_FILE = "insects_feature_importance.csv"

BASE_FEATURES = [
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


def calculate_accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> tuple[float, float]:
    r2 = r2_score(y_true, y_pred)
    accuracy = max(0.0, min(100.0, (r2 + 1.0) / 2.0 * 100.0))
    return float(accuracy), float(r2)


def build_engineered_features(df_base: pd.DataFrame) -> pd.DataFrame:
    x = df_base.copy()

    # Cyclical month encoding captures season wrap-around (Dec -> Jan).
    x["month_sin"] = np.sin(2 * np.pi * x["month"] / 12.0)
    x["month_cos"] = np.cos(2 * np.pi * x["month"] / 12.0)

    # Day-of-week proxy from date components.
    dates = pd.to_datetime(
        {
            "year": x["year"].round().astype(int),
            "month": x["month"].round().clip(1, 12).astype(int),
            "day": x["day"].round().clip(1, 31).astype(int),
        },
        errors="coerce",
    )
    x["weekend_flag"] = dates.dt.dayofweek.isin([5, 6]).astype(int)

    # Grid-month reporting intensity.
    x["observation_effort"] = (
        x.groupby(["lat_grid", "lon_grid", "month"])["month"].transform("size").astype(float)
    )

    # Grid-level family diversity.
    x["family_richness_grid"] = (
        x.groupby(["lat_grid", "lon_grid"])["family_enc"].transform("nunique").astype(float)
    )

    q1, q2, q3 = x["coordinateUncertaintyInMeters"].quantile([0.25, 0.50, 0.75]).tolist()
    x["uncertainty_bucket"] = (
        (x["coordinateUncertaintyInMeters"] > q1).astype(int)
        + (x["coordinateUncertaintyInMeters"] > q2).astype(int)
        + (x["coordinateUncertaintyInMeters"] > q3).astype(int)
    ).astype(float)

    x["order_family"] = x["order_enc"] * x["family_enc"]
    x["richness_family"] = x["species_richness"] * x["family_enc"]
    x["richness_order"] = x["species_richness"] * x["order_enc"]
    x["spatial"] = x["lat_grid"] * x["lon_grid"]
    x["spatial_uncertainty"] = (x["lat_grid"] + x["lon_grid"]) * x["coordinateUncertaintyInMeters"]
    x["season_month"] = x["season_enc"] * x["month"]
    x["year_month"] = x["year"] * x["month"]
    x["day_month"] = x["day"] * x["month"]

    for feat in ["species_richness", "month", "day", "year"]:
        x[f"{feat}_sq"] = x[feat] ** 2

    x["richness_log"] = np.log1p(x["species_richness"])
    x["uncertainty_log"] = np.log1p(x["coordinateUncertaintyInMeters"])
    x["uncertainty_inv"] = 1.0 / (1.0 + np.log1p(x["coordinateUncertaintyInMeters"].clip(lower=0)))
    x["rich_uncertainty_ratio"] = x["species_richness"] / (x["coordinateUncertaintyInMeters"] + 1.0)
    x["family_order_ratio"] = (x["family_enc"] + 1.0) / (x["order_enc"] + 1.0)
    x["day_year_ratio"] = x["day"] / (x["year"] + 1.0)
    x["spatial_mean"] = (x["lat_grid"] + x["lon_grid"]) / 2.0
    x["temporal_mean"] = (x["day"] + x["month"] + x["decade"]) / 3.0
    x["category_mean"] = (x["order_enc"] + x["family_enc"] + x["taxonRank_enc"]) / 3.0
    x["season_richness_interaction"] = x["season_enc"] * x["species_richness"]

    x["richness_high"] = (x["species_richness"] > x["species_richness"].median()).astype(int)
    x["uncertainty_high"] = (
        x["coordinateUncertaintyInMeters"] > x["coordinateUncertaintyInMeters"].median()
    ).astype(int)

    return x


def main() -> None:
    print("=" * 70)
    print("INSECTS POPULATION DENSITY MODEL (LINEAR REGRESSION)")
    print("=" * 70)

    df = pd.read_csv(DATA_FILE)
    x_base = df[BASE_FEATURES].copy()
    y_raw = df["insect_sighting_density"].copy()

    x = build_engineered_features(x_base)
    y = np.log1p(y_raw)

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.2,
        random_state=42,
        shuffle=True,
    )

    scaler = RobustScaler()
    x_train_scaled = scaler.fit_transform(x_train)
    x_test_scaled = scaler.transform(x_test)

    model = LinearRegression()
    model.fit(x_train_scaled, y_train)

    y_pred = model.predict(x_test_scaled)

    mae = float(mean_absolute_error(y_test, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
    accuracy, r2 = calculate_accuracy(y_test, y_pred)

    joblib.dump(model, MODEL_FILE)
    joblib.dump(scaler, SCALER_FILE)
    joblib.dump(list(x.columns), FEATURE_FILE)

    metadata = {
        "model": "LinearRegression",
        "accuracy": accuracy,
        "r2": r2,
        "mae_log": mae,
        "rmse_log": rmse,
        "features": list(x.columns),
        "base_features": BASE_FEATURES,
        "target_transform": "log1p",
    }
    joblib.dump(metadata, METADATA_FILE)

    coef = np.abs(model.coef_)
    fi_df = pd.DataFrame({"Feature": x.columns, "Importance": coef}).sort_values(
        "Importance", ascending=False
    )
    fi_df.to_csv(IMPORTANCE_FILE, index=False)

    print(f"Rows: {len(df)}")
    print(f"Base features: {len(BASE_FEATURES)}")
    print(f"Engineered features: {x.shape[1]}")
    print(f"Accuracy: {accuracy:.2f}%")
    print(f"R2 score: {r2:.4f}")
    print(f"MAE (log space): {mae:.4f}")
    print(f"RMSE (log space): {rmse:.4f}")
    print(f"Saved: {MODEL_FILE}, {SCALER_FILE}, {FEATURE_FILE}, {METADATA_FILE}")


if __name__ == "__main__":
    main()
