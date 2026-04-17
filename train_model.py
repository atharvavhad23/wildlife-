import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

DATA_FILE = Path("koyna_animals_regression_density.csv")
MODEL_FILE = Path("wildlife_model.pkl")
SCALER_FILE = Path("scaler.pkl")
FEATURE_FILE = Path("feature_names.pkl")
METADATA_FILE = Path("model_metadata.pkl")

TARGET_COLUMN = "TARGET_sighting_density"
DROP_COLUMNS = ["decimalLatitude", "decimalLongitude", TARGET_COLUMN]

ENV_FEATURES = [
    "temperature",
    "rainfall",
    "humidity",
    "vegetation_index",
    "water_availability",
    "human_disturbance",
]


def load_dataset(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        raise FileNotFoundError(f"Dataset not found: {csv_path}")
    df = pd.read_csv(csv_path)
    if TARGET_COLUMN not in df.columns:
        raise ValueError(f"Missing target column '{TARGET_COLUMN}' in dataset")
    return df


def ensure_environmental_features(df: pd.DataFrame) -> pd.DataFrame:
    """Populate missing environmental columns with realistic synthetic values."""
    rng = np.random.default_rng(seed=42)
    n = len(df)

    if "temperature" not in df.columns:
        df["temperature"] = rng.normal(loc=26.5, scale=4.2, size=n).clip(10, 42)

    if "humidity" not in df.columns:
        df["humidity"] = rng.normal(loc=62.0, scale=14.0, size=n).clip(20, 98)

    if "rainfall" not in df.columns:
        df["rainfall"] = rng.gamma(shape=1.7, scale=3.0, size=n).clip(0, 150)

    if "vegetation_index" not in df.columns:
        veg = 0.35 + (df["rainfall"] / (df["rainfall"].max() + 1e-6)) * 0.45 + rng.normal(0, 0.08, size=n)
        df["vegetation_index"] = veg.clip(0.05, 0.98)

    if "water_availability" not in df.columns:
        water = 0.2 + (df["rainfall"] / (df["rainfall"].max() + 1e-6)) * 0.75 + rng.normal(0, 0.05, size=n)
        df["water_availability"] = water.clip(0.0, 1.0)

    if "human_disturbance" not in df.columns:
        disturbance = 1.0 - df["vegetation_index"] + rng.normal(0, 0.08, size=n)
        df["human_disturbance"] = disturbance.clip(0.0, 1.0)

    return df


def build_feature_matrix(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, list[str]]:
    base_features = [col for col in df.columns if col not in DROP_COLUMNS]

    # Keep existing feature order and append required environmental features if absent.
    ordered_features = [col for col in base_features if col not in ENV_FEATURES] + ENV_FEATURES
    ordered_features = list(dict.fromkeys(ordered_features))

    missing_after_generation = [col for col in ENV_FEATURES if col not in df.columns]
    if missing_after_generation:
        raise ValueError(f"Failed to prepare environmental features: {missing_after_generation}")

    X = df[ordered_features].copy()
    y = df[TARGET_COLUMN].copy()
    return X, y, ordered_features


def train_and_evaluate(X: pd.DataFrame, y: pd.Series) -> dict:
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    model = RandomForestRegressor(
        n_estimators=300,
        max_depth=18,
        min_samples_split=4,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train_scaled, y_train)

    predictions = model.predict(X_test_scaled)
    r2 = r2_score(y_test, predictions)
    rmse = float(np.sqrt(mean_squared_error(y_test, predictions)))

    return {
        "model": model,
        "scaler": scaler,
        "r2": float(r2),
        "rmse": rmse,
    }


def save_artifacts(model, scaler, feature_names: list[str], metrics: dict) -> None:
    joblib.dump(model, MODEL_FILE)
    joblib.dump(scaler, SCALER_FILE)
    joblib.dump(feature_names, FEATURE_FILE)
    joblib.dump(metrics, METADATA_FILE)


def main() -> None:
    print("=" * 60)
    print("WILDLIFE POPULATION DENSITY MODEL TRAINING")
    print("=" * 60)

    df = load_dataset(DATA_FILE)
    df = ensure_environmental_features(df)

    X, y, feature_names = build_feature_matrix(df)
    result = train_and_evaluate(X, y)

    metrics = {
        "model_name": "RandomForestRegressor",
        "r2_score": result["r2"],
        "rmse": result["rmse"],
        "feature_count": len(feature_names),
        "feature_names": feature_names,
    }

    save_artifacts(result["model"], result["scaler"], feature_names, metrics)

    print(f"Features used ({len(feature_names)}): {feature_names}")
    print(f"R2 Score: {result['r2']:.4f}")
    print(f"RMSE: {result['rmse']:.4f}")
    print(f"Saved model to: {MODEL_FILE}")
    print(f"Saved scaler to: {SCALER_FILE}")
    print(f"Saved features to: {FEATURE_FILE}")
    print("Training complete.")


if __name__ == "__main__":
    main()
