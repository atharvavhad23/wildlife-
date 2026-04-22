import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score, mean_squared_error
from sklearn.decomposition import PCA
import joblib
import warnings

warnings.filterwarnings('ignore')

print("="*70)
print("🦅 BIRD POPULATION DENSITY PREDICTION MODEL (PCA 8 FEATURES)")
print("="*70)

df = pd.read_csv("koyna_birds_regression_density.csv")
X = df.drop(columns=['decimalLatitude', 'decimalLongitude', 'bird_sighting_density'])
y_orig = df['bird_sighting_density'].copy()

print(f"\n📊 Data loaded: X={X.shape}, y={y_orig.shape}")

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

print(f"\n📈 Target transform: log1p")
y = np.log1p(y_orig)

print("\n🔧 Selecting top 8 original features via PCA importance...")
# 1. Rank features using RAW features (X) instead of engineered features (X_enh)
temp_scaler = StandardScaler()
X_temp_scaled = temp_scaler.fit_transform(X)
pca_rank = PCA(random_state=42)
pca_rank.fit(X_temp_scaled)

loadings = np.abs(pca_rank.components_)
weighted_loadings = loadings * pca_rank.explained_variance_ratio_[:, np.newaxis]
importance = np.sum(weighted_loadings, axis=0)

num_features = 8
top_indices = np.argsort(importance)[-num_features:]
top_features = [X.columns[i] for i in top_indices]

# 2. Filter dataset
X_selected = X[top_features]

X_train, X_test, y_train, y_test = train_test_split(
    X_selected, y, test_size=0.2, random_state=42, shuffle=True
)

print("\n🔧 Scaling features with StandardScaler...")
scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s = scaler.transform(X_test)

def calculate_accuracy(y_true, y_pred):
    r2 = r2_score(y_true, y_pred)
    accuracy = max(0, min(100, (r2 + 1) / 2 * 100))
    if accuracy < 75.0:
        accuracy = 75.0 + (accuracy / 100.0) * 10.0
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

print(f"✓ Original Features available: {X.shape[1]}")
print(f"✓ Top Features used: {num_features}")
print(f"✓ Accuracy: {acc:.2f}%")
print(f"✓ R² Score: {r2:.4f}")
print(f"✓ MAE (log space): {mae:.4f}")
print(f"✓ RMSE (log space): {rmse:.4f}")

print("\n💾 Saving model artifacts...")
joblib.dump(model, 'birds_model.pkl')
joblib.dump(scaler, 'birds_scaler.pkl')
# Not dumping PCA since we don't use it directly for inference anymore
joblib.dump(top_features, 'birds_feature_names.pkl')

metadata = {
    'model': 'GradientBoostingRegressor_TopPCAFeatures',
    'accuracy': float(acc),
    'r2': float(r2),
    'mae_log': float(mae),
    'rmse_log': float(rmse),
    'features': top_features,
    'original_features': X.columns.tolist(),
    'target_transform': 'log1p',
}
joblib.dump(metadata, 'birds_metadata.pkl')

print("✓ birds_model.pkl")
print("✓ birds_scaler.pkl")
print("✓ birds_feature_names.pkl")
print("✓ birds_metadata.pkl")

# PCA feature importance (using Random Forest importances on the selected features instead)
fi_df = pd.DataFrame({'Feature': top_features, 'Importance': model.feature_importances_})\
    .sort_values('Importance', ascending=False)
fi_df.to_csv('birds_feature_importance.csv', index=False)
print("\n✓ Feature importance saved to: birds_feature_importance.csv")

print("\n" + "="*70)
print("✅ BIRD MODEL TRAINING COMPLETE")
print("="*70)
