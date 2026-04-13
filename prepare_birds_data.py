import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder
import warnings

warnings.filterwarnings('ignore')

print("🦅 Processing Birds Dataset...")

# Load the birds data
df_birds = pd.read_csv("Koyna_birds_final.csv")

print(f"Original dataset shape: {df_birds.shape}")
print(f"Columns: {df_birds.columns.tolist()}")

# Remove rows with missing target values
df_birds = df_birds[df_birds['individualCount'].notna()].copy()

# Handle missing values
df_birds = df_birds.fillna(df_birds.mean(numeric_only=True))

# Extract numeric features and encode categorical ones
features_to_use = [
    'coordinateUncertaintyInMeters', 'day', 'month', 'year',
    'order', 'family', 'genus', 'taxonRank', 'basisOfRecord'
]

# Create a copy with selected features
df_processed = pd.DataFrame()

# Numeric features
numeric_cols = ['coordinateUncertaintyInMeters', 'day', 'month', 'year']
for col in numeric_cols:
    if col in df_birds.columns:
        df_processed[col] = pd.to_numeric(df_birds[col], errors='coerce').fillna(df_birds[col].mean())

# Encode categorical features
categorical_cols = ['order', 'family', 'taxonRank', 'basisOfRecord']
le_dict = {}

for col in categorical_cols:
    if col in df_birds.columns:
        le = LabelEncoder()
        df_processed[f'{col}_enc'] = le.fit_transform(df_birds[col].astype(str).fillna('Unknown'))
        le_dict[col] = le

# Add target variable
df_processed['bird_sighting_density'] = df_birds['individualCount']

# Add geographic coordinates for reference (not as features)
df_processed['decimalLatitude'] = df_birds['decimalLatitude']
df_processed['decimalLongitude'] = df_birds['decimalLongitude']

# Create grid-based features
df_processed['lat_grid'] = np.round(df_birds['decimalLatitude'], 1)
df_processed['lon_grid'] = np.round(df_birds['decimalLongitude'], 1)

# Add temporal features
df_processed['decade'] = (df_birds['year'] // 10 * 10).astype(int)

# Season encoding (approximate based on month)
def get_season(month):
    if month in [12, 1, 2]:
        return 0  # Winter
    elif month in [3, 4, 5]:
        return 1  # Spring
    elif month in [6, 7, 8]:
        return 2  # Monsoon
    else:
        return 3  # Autumn

df_processed['season_enc'] = df_birds['month'].apply(get_season)

# Add species richness (count of unique species in each grid cell)
grid_species = df_birds.groupby([
    df_birds['decimalLatitude'].round(1),
    df_birds['decimalLongitude'].round(1)
]).apply(lambda x: len(x['species'].unique())).reset_index()
grid_species.columns = ['lat_rounded', 'lon_rounded', 'species_richness']

df_processed['lat_rounded'] = np.round(df_birds['decimalLatitude'], 1)
df_processed['lon_rounded'] = np.round(df_birds['decimalLongitude'], 1)

df_processed = df_processed.merge(
    grid_species,
    left_on=['lat_rounded', 'lon_rounded'],
    right_on=['lat_rounded', 'lon_rounded'],
    how='left'
)

# Clean up temporary columns
df_processed = df_processed.drop(columns=['lat_rounded', 'lon_rounded'])
df_processed['species_richness'] = df_processed['species_richness'].fillna(df_processed['species_richness'].mean())

# Remove rows with NaN values
df_processed = df_processed.dropna()

print(f"Processed dataset shape: {df_processed.shape}")
print(f"Target variable statistics:")
print(f"  Mean: {df_processed['bird_sighting_density'].mean():.2f}")
print(f"  Std: {df_processed['bird_sighting_density'].std():.2f}")
print(f"  Min: {df_processed['bird_sighting_density'].min():.2f}")
print(f"  Max: {df_processed['bird_sighting_density'].max():.2f}")

# Save processed dataset
df_processed.to_csv('koyna_birds_regression_density.csv', index=False)
print("\n✓ Processed birds dataset saved as: koyna_birds_regression_density.csv")
print(f"✓ Final features: {df_processed.shape[1] - 2} (excluding lat/lon)")
