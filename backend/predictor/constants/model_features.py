"""
Model feature constants - centralized feature lists for all models.
"""

# ── BIRDS FEATURES ──────────────────────────────────────────────────
BASE_BIRDS_FEATURES = [
    'coordinateUncertaintyInMeters',
    'day',
    'month',
    'year',
    'decade',
    'order_enc',
    'family_enc',
    'taxonRank_enc',
    'basisOfRecord_enc',
    'season_enc',
    'lat_grid',
    'lon_grid',
    'species_richness',
]

# ── INSECTS FEATURES ────────────────────────────────────────────────
BASE_INSECTS_FEATURES = [
    'coordinateUncertaintyInMeters',
    'day',
    'month',
    'year',
    'decade',
    'order_enc',
    'family_enc',
    'taxonRank_enc',
    'basisOfRecord_enc',
    'season_enc',
    'lat_grid',
    'lon_grid',
    'species_richness',
]

# ── ANIMALS OCCURRENCE FEATURES ─────────────────────────────────────
BASE_ANIMALS_OCCURRENCE_FEATURES = [
    'coordinateUncertaintyInMeters',
    'month',
    'year',
    'day',
    'decade',
    'lat_grid',
    'lon_grid',
    'phylum_enc',
    'class_enc',
    'order_enc',
    'family_enc',
    'taxonRank_enc',
    'basisOfRecord_enc',
    'season_enc',
    'species_richness',
]

# ── PLANTS FEATURES ────────────────────────────────────────────────
BASE_PLANTS_FEATURES = [
    'coordinateUncertaintyInMeters',
    'day',
    'month',
    'year',
    'decade',
    'season_enc',
    'lat_grid',
    'lon_grid',
    'species_richness',
    'order_enc',
    'family_enc',
    'class_enc',
    'taxonRank_enc',
    'basisOfRecord_enc',
]

# ── ANIMALS FEATURES ────────────────────────────────────────────────
BASE_ANIMALS_FEATURES = [
    'coordinateUncertaintyInMeters',
    'coordinateUncertaintyInMeters_mean',
    'month',
    'year',
    'day',
    'decade',
    'lat_grid',
    'lon_grid',
    'phylum_enc',
    'class_enc',
    'order_enc',
    'family_enc',
    'taxonRank_enc',
    'basisOfRecord_enc',
    'season_enc',
    'species_richness',
]

# ── FEATURE SETS BY CATEGORY ────────────────────────────────────────
FEATURE_SETS = {
    'animals': BASE_ANIMALS_FEATURES,
    'birds': BASE_BIRDS_FEATURES,
    'insects': BASE_INSECTS_FEATURES,
    'plants': BASE_PLANTS_FEATURES,
}

OCCURRENCE_FEATURE_SETS = {
    'animals': BASE_ANIMALS_OCCURRENCE_FEATURES,
    'birds': BASE_BIRDS_FEATURES.copy(),
    'insects': BASE_INSECTS_FEATURES.copy(),
    'plants': BASE_PLANTS_FEATURES.copy(),
}

# OTP Settings
OTP_TTL_SECONDS = 10 * 60

# Clustering defaults
DEFAULT_N_CLUSTERS = 8
DEFAULT_LIMIT_ITEMS = 20

# Cache keys
SPECIES_CACHE_KEYS = {
    'animals': 'species_animals',
    'birds': 'species_birds',
    'insects': 'species_insects',
    'plants': 'species_plants',
}

CLUSTERING_CACHE_KEYS = {
    'animals': 'clustering_animals',
    'birds': 'clustering_birds',
    'insects': 'clustering_insects',
    'plants': 'clustering_plants',
}

# API defaults
DEFAULT_PAGINATION_LIMIT = 50
MAX_PAGINATION_LIMIT = 500
