import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import RobustScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score, mean_squared_error
import joblib
import warnings

warnings.filterwarnings('ignore')

print("="*70)
print("🦅 BIRD POPULATION DENSITY PREDICTION MODEL (CLEAN + CURRENT)")
print("="*70)

df = pd.read_csv("koyna_birds_regression_density.csv")
X = df.drop(columns=['decimalLatitude', 'decimalLongitude', 'bird_sighting_density'])
y_orig = df['bird_sighting_density'].copy()

print(f"\n📊 Data loaded: X={X.shape}, y={y_orig.shape}")
print(f"   Target: mean={y_orig.mean():.2f}, std={y_orig.std():.2f}, min={y_orig.min():.2f}, max={y_orig.max():.2f}")

print(f"\n🔧 Feature engineering (base={X.shape[1]})...")
X_enh = X.copy()

# Interaction Terms
X_enh['order_family'] = X['order_enc'] * X['family_enc']
X_enh['richness_family'] = X['species_richness'] * X['family_enc']
X_enh['richness_order'] = X['species_richness'] * X['order_enc']
X_enh['order_family_rich'] = X['order_enc'] * X['family_enc'] * X['species_richness']

# Spatial Interactions
X_enh['spatial'] = X['lat_grid'] * X['lon_grid']
X_enh['spatial_uncertainty'] = (X['lat_grid'] + X['lon_grid']) * X['coordinateUncertaintyInMeters']

# Temporal Interactions
X_enh['season_month'] = X['season_enc'] * X['month']
X_enh['year_month'] = X['year'] * X['month']
X_enh['day_month'] = X['day'] * X['month']

# Polynomial Features
for feat in ['species_richness', 'month', 'day', 'year']:
    X_enh[f'{feat}_sq'] = X[feat] ** 2
    X_enh[f'{feat}_sqrt'] = np.sqrt(np.abs(X[feat]) + 1)
    X_enh[f'{feat}_cbrt'] = np.cbrt(X[feat])

# Log transforms
X_enh['richness_log'] = np.log1p(X['species_richness'])
X_enh['richness_log2'] = np.log1p(X['species_richness']) ** 2
X_enh['uncertainty_log'] = np.log1p(X['coordinateUncertaintyInMeters'])
X_enh['month_log'] = np.log1p(X['month'])

# Ratios
X_enh['rich_uncertainty_ratio'] = X['species_richness'] / (X['coordinateUncertaintyInMeters'] + 1)
X_enh['family_order_ratio'] = (X['family_enc'] + 1) / (X['order_enc'] + 1)
X_enh['day_year_ratio'] = X['day'] / (X['year'] + 1)

# Aggregates
X_enh['spatial_mean'] = (X['lat_grid'] + X['lon_grid']) / 2
X_enh['spatial_sum'] = X['lat_grid'] + X['lon_grid']
X_enh['temporal_mean'] = (X['day'] + X['month'] + X['decade']) / 3
X_enh['category_mean'] = (X['order_enc'] + X['family_enc'] + X['taxonRank_enc']) / 3

# Binary features (use dataset medians)
X_enh['richness_high'] = (X['species_richness'] > X['species_richness'].median()).astype(int)
X_enh['uncertainty_high'] = (
    X['coordinateUncertaintyInMeters'] > X['coordinateUncertaintyInMeters'].median()
).astype(int)
X_enh['month_season'] = (X['month'] % 4).astype(int)

print(f"✓ Enhanced features: {X_enh.shape[1]} (+{X_enh.shape[1] - X.shape[1]})")

print(f"\n📈 Target transform: log1p")
y = np.log1p(y_orig)

X_train, X_test, y_train, y_test = train_test_split(
    X_enh, y, test_size=0.2, random_state=42, shuffle=True
)

print("\n🔧 Scaling features with RobustScaler...")
scaler = RobustScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s = scaler.transform(X_test)

def calculate_accuracy(y_true, y_pred):
    r2 = r2_score(y_true, y_pred)
    accuracy = max(0, min(100, (r2 + 1) / 2 * 100))
    return accuracy, r2

print("\n" + "="*70)
print("🚀 TRAINING MODEL")
print("="*70)

model = GradientBoostingRegressor(
    n_estimators=500,
    max_depth=7,
    learning_rate=0.05,
    min_samples_split=3,
    min_samples_leaf=2,
    subsample=0.8,
    max_features='sqrt',
    validation_fraction=0.1,
    n_iter_no_change=30,
    random_state=42,
    loss='huber',
    alpha=0.9,
)

model.fit(X_train_s, y_train)
y_pred = model.predict(X_test_s)

mae = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
acc, r2 = calculate_accuracy(y_test, y_pred)

print(f"✓ Accuracy: {acc:.2f}%")
print(f"✓ R² Score: {r2:.4f}")
print(f"✓ MAE (log space): {mae:.4f}")
print(f"✓ RMSE (log space): {rmse:.4f}")

print("\n💾 Saving model artifacts...")
joblib.dump(model, 'birds_model.pkl')
joblib.dump(scaler, 'birds_scaler.pkl')
joblib.dump(X_enh.columns.tolist(), 'birds_feature_names.pkl')

metadata = {
    'model': 'GradientBoostingRegressor',
    'accuracy': float(acc),
    'r2': float(r2),
    'mae_log': float(mae),
    'rmse_log': float(rmse),
    'features': X_enh.columns.tolist(),
    'target_transform': 'log1p',
}
joblib.dump(metadata, 'birds_metadata.pkl')

print("✓ birds_model.pkl")
print("✓ birds_scaler.pkl")
print("✓ birds_feature_names.pkl")
print("✓ birds_metadata.pkl")

if hasattr(model, 'feature_importances_'):
    fi_df = pd.DataFrame({'Feature': X_enh.columns, 'Importance': model.feature_importances_})\
        .sort_values('Importance', ascending=False)
    fi_df.to_csv('birds_feature_importance.csv', index=False)
    print("\n✓ Feature importance saved to: birds_feature_importance.csv")

print("\n" + "="*70)
print("✅ BIRD MODEL TRAINING COMPLETE")
print("="*70)
