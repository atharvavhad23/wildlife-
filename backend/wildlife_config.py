"""
Centralized configuration for all data, model, and resource paths.
This ensures all file references are in one place and easy to maintain.
"""

from pathlib import Path

# Base directories
BACKEND_DIR = Path(__file__).resolve().parent
DATA_DIR = BACKEND_DIR / "data"
MODELS_DIR = BACKEND_DIR / "models"
REPORTS_DIR = BACKEND_DIR / "reports"

# Data subdirectories
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
EXTERNAL_DATA_DIR = DATA_DIR / "external"

# Ensure all directories exist
for directory in [
    RAW_DATA_DIR,
    PROCESSED_DATA_DIR,
    EXTERNAL_DATA_DIR,
    MODELS_DIR / "animals",
    MODELS_DIR / "birds",
    MODELS_DIR / "insects",
    MODELS_DIR / "plants",
    REPORTS_DIR / "feature_importance",
]:
    directory.mkdir(parents=True, exist_ok=True)


# ──────────────────────────────────────────────────────────────────────────
# RAW DATA FILES (Original datasets)
# ──────────────────────────────────────────────────────────────────────────
RAW_ANIMALS_CSV = RAW_DATA_DIR / "Koyna_animals_final.csv"
RAW_BIRDS_CSV = RAW_DATA_DIR / "Koyna_birds_final.csv"
RAW_INSECTS_CSV = RAW_DATA_DIR / "Koyna_insects_final.csv"
RAW_PLANTS_CSV = RAW_DATA_DIR / "Koyna_plants_final.csv"
RAW_SPECIES_CSV = RAW_DATA_DIR / "Koynaspecies.csv"
RAW_SPECIES_CLEANED_CSV = RAW_DATA_DIR / "Koynaspecies_cleaned.csv"

# ──────────────────────────────────────────────────────────────────────────
# PROCESSED DATA FILES (Prepared for training)
# ──────────────────────────────────────────────────────────────────────────
PROCESSED_ANIMALS_REGRESSION_CSV = PROCESSED_DATA_DIR / "koyna_animals_regression_density.csv"
PROCESSED_BIRDS_REGRESSION_CSV = PROCESSED_DATA_DIR / "koyna_birds_regression_density.csv"
PROCESSED_INSECTS_REGRESSION_CSV = PROCESSED_DATA_DIR / "koyna_insects_regression_density.csv"
PROCESSED_PLANTS_REGRESSION_CSV = PROCESSED_DATA_DIR / "koyna_plants_regression_density.csv"

# Classification datasets
ANIMALS_CLASSIFICATION_CSV = PROCESSED_DATA_DIR / "koyna_animals_classification_class.csv"
ANIMALS_REGRESSION_COUNT_CSV = PROCESSED_DATA_DIR / "koyna_animals_regression_count.csv"

# ──────────────────────────────────────────────────────────────────────────
# EXTERNAL DATA FILES (Reference/auxiliary data)
# ──────────────────────────────────────────────────────────────────────────
IUCN_TREE_SPECIES_CSV = EXTERNAL_DATA_DIR / "Koyna_IUCN_Tree_Species.csv"
LOCALITY_DIVERSITY_CSV = EXTERNAL_DATA_DIR / "Koyna_Locality_Diversity.csv"

# ──────────────────────────────────────────────────────────────────────────
# ANIMALS MODEL FILES
# ──────────────────────────────────────────────────────────────────────────
ANIMALS_MODEL_PKL = MODELS_DIR / "animals" / "wildlife_model.pkl"
ANIMALS_SCALER_PKL = MODELS_DIR / "animals" / "scaler.pkl"
ANIMALS_FEATURE_NAMES_PKL = MODELS_DIR / "animals" / "feature_names.pkl"
ANIMALS_METADATA_PKL = MODELS_DIR / "animals" / "model_metadata.pkl"
ANIMALS_OCCURRENCE_CLASSIFIER_PKL = MODELS_DIR / "animals" / "animals_occurrence_classifier.pkl"
ANIMALS_OCCURRENCE_FEATURES_PKL = MODELS_DIR / "animals" / "animals_occurrence_features.pkl"
ANIMALS_OCCURRENCE_METADATA_PKL = MODELS_DIR / "animals" / "animals_occurrence_metadata.pkl"

# ──────────────────────────────────────────────────────────────────────────
# BIRDS MODEL FILES
# ──────────────────────────────────────────────────────────────────────────
BIRDS_MODEL_PKL = MODELS_DIR / "birds" / "birds_model.pkl"
BIRDS_SCALER_PKL = MODELS_DIR / "birds" / "birds_scaler.pkl"
BIRDS_FEATURE_NAMES_PKL = MODELS_DIR / "birds" / "birds_feature_names.pkl"
BIRDS_METADATA_PKL = MODELS_DIR / "birds" / "birds_metadata.pkl"
BIRDS_OCCURRENCE_CLASSIFIER_PKL = MODELS_DIR / "birds" / "birds_occurrence_classifier.pkl"
BIRDS_OCCURRENCE_FEATURES_PKL = MODELS_DIR / "birds" / "birds_occurrence_features.pkl"
BIRDS_OCCURRENCE_METADATA_PKL = MODELS_DIR / "birds" / "birds_occurrence_metadata.pkl"

# ──────────────────────────────────────────────────────────────────────────
# INSECTS MODEL FILES
# ──────────────────────────────────────────────────────────────────────────
INSECTS_MODEL_PKL = MODELS_DIR / "insects" / "insects_model.pkl"
INSECTS_SCALER_PKL = MODELS_DIR / "insects" / "insects_scaler.pkl"
INSECTS_FEATURE_NAMES_PKL = MODELS_DIR / "insects" / "insects_feature_names.pkl"
INSECTS_METADATA_PKL = MODELS_DIR / "insects" / "insects_metadata.pkl"
INSECTS_OCCURRENCE_CLASSIFIER_PKL = MODELS_DIR / "insects" / "insects_occurrence_classifier.pkl"
INSECTS_OCCURRENCE_FEATURES_PKL = MODELS_DIR / "insects" / "insects_occurrence_features.pkl"
INSECTS_OCCURRENCE_METADATA_PKL = MODELS_DIR / "insects" / "insects_occurrence_metadata.pkl"

# ──────────────────────────────────────────────────────────────────────────
# PLANTS MODEL FILES
# ──────────────────────────────────────────────────────────────────────────
PLANTS_MODEL_PKL = MODELS_DIR / "plants" / "plants_model.pkl"
PLANTS_SCALER_PKL = MODELS_DIR / "plants" / "plants_scaler.pkl"
PLANTS_FEATURE_NAMES_PKL = MODELS_DIR / "plants" / "plants_feature_names.pkl"
PLANTS_METADATA_PKL = MODELS_DIR / "plants" / "plants_metadata.pkl"
PLANTS_KMEANS_PKL = MODELS_DIR / "plants" / "plants_kmeans.pkl"
PLANTS_KMEANS_SCALER_PKL = MODELS_DIR / "plants" / "plants_kmeans_scaler.pkl"
PLANTS_KMEANS_META_PKL = MODELS_DIR / "plants" / "plants_kmeans_meta.pkl"
PLANTS_OCCURRENCE_CLASSIFIER_PKL = MODELS_DIR / "plants" / "plants_occurrence_classifier.pkl"
PLANTS_OCCURRENCE_FEATURES_PKL = MODELS_DIR / "plants" / "plants_occurrence_features.pkl"
PLANTS_OCCURRENCE_METADATA_PKL = MODELS_DIR / "plants" / "plants_occurrence_metadata.pkl"

# ──────────────────────────────────────────────────────────────────────────
# FEATURE IMPORTANCE FILES
# ──────────────────────────────────────────────────────────────────────────
FEATURE_IMPORTANCE_CSV = REPORTS_DIR / "feature_importance" / "feature_importance.csv"
BIRDS_FEATURE_IMPORTANCE_CSV = REPORTS_DIR / "feature_importance" / "birds_feature_importance.csv"
INSECTS_FEATURE_IMPORTANCE_CSV = REPORTS_DIR / "feature_importance" / "insects_feature_importance.csv"
PLANTS_FEATURE_IMPORTANCE_CSV = REPORTS_DIR / "feature_importance" / "plants_feature_importance.csv"


def get_model_files(category: str) -> dict:
    """Return all model-related file paths for a given category."""
    category = category.lower()
    if category == "animals":
        return {
            "model": ANIMALS_MODEL_PKL,
            "scaler": ANIMALS_SCALER_PKL,
            "feature_names": ANIMALS_FEATURE_NAMES_PKL,
            "metadata": ANIMALS_METADATA_PKL,
            "occurrence_classifier": ANIMALS_OCCURRENCE_CLASSIFIER_PKL,
            "occurrence_features": ANIMALS_OCCURRENCE_FEATURES_PKL,
            "occurrence_metadata": ANIMALS_OCCURRENCE_METADATA_PKL,
        }
    elif category == "birds":
        return {
            "model": BIRDS_MODEL_PKL,
            "scaler": BIRDS_SCALER_PKL,
            "feature_names": BIRDS_FEATURE_NAMES_PKL,
            "metadata": BIRDS_METADATA_PKL,
            "occurrence_classifier": BIRDS_OCCURRENCE_CLASSIFIER_PKL,
            "occurrence_features": BIRDS_OCCURRENCE_FEATURES_PKL,
            "occurrence_metadata": BIRDS_OCCURRENCE_METADATA_PKL,
        }
    elif category == "insects":
        return {
            "model": INSECTS_MODEL_PKL,
            "scaler": INSECTS_SCALER_PKL,
            "feature_names": INSECTS_FEATURE_NAMES_PKL,
            "metadata": INSECTS_METADATA_PKL,
            "occurrence_classifier": INSECTS_OCCURRENCE_CLASSIFIER_PKL,
            "occurrence_features": INSECTS_OCCURRENCE_FEATURES_PKL,
            "occurrence_metadata": INSECTS_OCCURRENCE_METADATA_PKL,
        }
    elif category == "plants":
        return {
            "model": PLANTS_MODEL_PKL,
            "scaler": PLANTS_SCALER_PKL,
            "feature_names": PLANTS_FEATURE_NAMES_PKL,
            "metadata": PLANTS_METADATA_PKL,
            "kmeans": PLANTS_KMEANS_PKL,
            "kmeans_scaler": PLANTS_KMEANS_SCALER_PKL,
            "kmeans_meta": PLANTS_KMEANS_META_PKL,
            "occurrence_classifier": PLANTS_OCCURRENCE_CLASSIFIER_PKL,
            "occurrence_features": PLANTS_OCCURRENCE_FEATURES_PKL,
            "occurrence_metadata": PLANTS_OCCURRENCE_METADATA_PKL,
        }
    else:
        raise ValueError(f"Unknown category: {category}")


def get_csv_files(category: str) -> dict:
    """Return all CSV file paths for a given category."""
    category = category.lower()
    if category == "animals":
        return {
            "raw": RAW_ANIMALS_CSV,
            "processed_regression": PROCESSED_ANIMALS_REGRESSION_CSV,
            "classification": ANIMALS_CLASSIFICATION_CSV,
            "regression_count": ANIMALS_REGRESSION_COUNT_CSV,
        }
    elif category == "birds":
        return {
            "raw": RAW_BIRDS_CSV,
            "processed_regression": PROCESSED_BIRDS_REGRESSION_CSV,
        }
    elif category == "insects":
        return {
            "raw": RAW_INSECTS_CSV,
            "processed_regression": PROCESSED_INSECTS_REGRESSION_CSV,
        }
    elif category == "plants":
        return {
            "raw": RAW_PLANTS_CSV,
            "processed_regression": PROCESSED_PLANTS_REGRESSION_CSV,
        }
    else:
        raise ValueError(f"Unknown category: {category}")


# Summary mapping for debugging/documentation
ALL_CATEGORIES = ["animals", "birds", "insects", "plants"]
