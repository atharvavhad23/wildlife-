"""
prepare_plants_data.py
======================
Feature engineering pipeline for Koyna Plants dataset.
Creates koyna_plants_regression_density.csv used by the ML training script.

Target: plant_sighting_density — observations per 0.1-degree grid cell
"""
import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder
import warnings

warnings.filterwarnings('ignore')

print("=" * 70)
print("🌿 PREPARING KOYNA PLANTS DATASET FOR REGRESSION")
print("=" * 70)

# ── Load raw data ──────────────────────────────────────────────────────────
df = pd.read_csv("Koyna_plants_final.csv")
print(f"\n📋 Raw dataset: {df.shape[0]:,} rows × {df.shape[1]} cols")

# ── Basic cleaning ─────────────────────────────────────────────────────────
# Keep rows that have valid coordinates
df = df.dropna(subset=['decimalLatitude', 'decimalLongitude'])
df['decimalLatitude'] = pd.to_numeric(df['decimalLatitude'], errors='coerce')
df['decimalLongitude'] = pd.to_numeric(df['decimalLongitude'], errors='coerce')
df = df.dropna(subset=['decimalLatitude', 'decimalLongitude'])

# Parse temporal columns
df['day']   = pd.to_numeric(df['day'],   errors='coerce').fillna(15).clip(1, 31).astype(int)
df['month'] = pd.to_numeric(df['month'], errors='coerce').fillna(6).clip(1, 12).astype(int)
df['year']  = pd.to_numeric(df['year'],  errors='coerce')
df = df[df['year'].between(1800, 2030)]   # sanity filter
df['year']  = df['year'].astype(int)

print(f"✓ After coordinate + date cleaning: {df.shape[0]:,} rows")

# ── Grid-based density target ──────────────────────────────────────────────
# 0.1° grid (≈11 km per cell)
df['lat_grid'] = np.round(df['decimalLatitude'],  1)
df['lon_grid'] = np.round(df['decimalLongitude'], 1)

grid_counts = (
    df.groupby(['lat_grid', 'lon_grid'])
    .size()
    .reset_index(name='plant_sighting_density')
)
df = df.merge(grid_counts, on=['lat_grid', 'lon_grid'], how='left')
print(f"✓ Target 'plant_sighting_density': mean={df['plant_sighting_density'].mean():.1f}, "
      f"max={df['plant_sighting_density'].max()}")

# ── Species richness per grid cell ─────────────────────────────────────────
sp_col = 'scientificName' if 'scientificName' in df.columns else 'species'
grid_rich = (
    df.groupby(['lat_grid', 'lon_grid'])[sp_col]
    .nunique()
    .reset_index(name='species_richness')
)
df = df.merge(grid_rich, on=['lat_grid', 'lon_grid'], how='left')
df['species_richness'] = df['species_richness'].fillna(1)
print(f"✓ Species richness computed, max={df['species_richness'].max()}")

# ── Temporal features ──────────────────────────────────────────────────────
df['decade'] = (df['year'] // 10 * 10)

def month_to_season(m):
    if m in [12, 1, 2]: return 0   # winter
    if m in [3, 4, 5]:  return 1   # spring
    if m in [6, 7, 8]:  return 2   # monsoon
    return 3                         # autumn

df['season_enc'] = df['month'].map(month_to_season)

# ── Categorical encoding ───────────────────────────────────────────────────
cat_cols = ['order', 'family', 'class', 'taxonRank', 'basisOfRecord']
le_dict  = {}

for col in cat_cols:
    target_col = f'{col}_enc'
    if col in df.columns:
        le = LabelEncoder()
        df[target_col] = le.fit_transform(df[col].astype(str).fillna('Unknown'))
        le_dict[col] = le
    else:
        df[target_col] = 0

print(f"✓ Categorical columns encoded: {cat_cols}")

# ── Coordinate uncertainty ─────────────────────────────────────────────────
df['coordinateUncertaintyInMeters'] = pd.to_numeric(
    df.get('coordinateUncertaintyInMeters', 0), errors='coerce'
).fillna(df.get('coordinateUncertaintyInMeters', pd.Series([1000])).median())

# ── Assemble processed dataframe ───────────────────────────────────────────
FEATURES = [
    'lat_grid', 'lon_grid',
    'day', 'month', 'year', 'decade', 'season_enc',
    'coordinateUncertaintyInMeters',
    'species_richness',
    'order_enc', 'family_enc', 'class_enc', 'taxonRank_enc', 'basisOfRecord_enc',
]

df_out = df[FEATURES + ['decimalLatitude', 'decimalLongitude', 'plant_sighting_density']].copy()
df_out = df_out.dropna()

print(f"\n✓ Final processed dataset: {df_out.shape[0]:,} rows × {df_out.shape[1]} cols")
print(f"   Target stats — mean: {df_out['plant_sighting_density'].mean():.2f}, "
      f"std: {df_out['plant_sighting_density'].std():.2f}, "
      f"max: {df_out['plant_sighting_density'].max()}")

df_out.to_csv('koyna_plants_regression_density.csv', index=False)
print("\n✅ Saved: koyna_plants_regression_density.csv")
print("=" * 70)
