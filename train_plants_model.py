"""
train_plants_model.py
=====================
Trains and compares:
  1. Linear Regression
  2. XGBoost Regressor
Selects the winner (higher R²) and saves it as the production model.
Also trains a KMeans clustering model for spatial analysis.

Outputs:
  plants_model.pkl            — Best regression model
  plants_scaler.pkl           — RobustScaler for features
  plants_feature_names.pkl    — Ordered feature list
  plants_metadata.pkl         — Metrics + model comparison
  plants_kmeans.pkl           — KMeans clustering model
  plants_kmeans_scaler.pkl    — Scaler for clustering features
  plants_feature_importance.csv
"""
import pandas as pd
import numpy as np
import joblib
import warnings
from sklearn.linear_model import Ridge
from sklearn.preprocessing import RobustScaler, StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_absolute_error, r2_score, mean_squared_error
from sklearn.cluster import KMeans

try:
    from xgboost import XGBRegressor
    HAS_XGB = True
except ImportError:
    HAS_XGB = False
    print("⚠️  xgboost not installed — will only train Linear Regression")
    print("   Install with: pip install xgboost")

warnings.filterwarnings('ignore')

SEP = "=" * 70

print(SEP)
print("🌿 PLANT SIGHTING DENSITY — MODEL COMPARISON & TRAINING")
print(SEP)

# ─────────────────────────────────────────────────────────────────────────────
# 1. LOAD PROCESSED DATA
# ─────────────────────────────────────────────────────────────────────────────
print("\n📂 Loading koyna_plants_regression_density.csv ...")
df = pd.read_csv("koyna_plants_regression_density.csv")
print(f"   Shape: {df.shape}")

# Drop coordinate columns (not used as features)
X_raw = df.drop(columns=['decimalLatitude', 'decimalLongitude', 'plant_sighting_density'])
y_orig = df['plant_sighting_density'].copy()

BASE_FEATURES = X_raw.columns.tolist()
print(f"   Base features ({len(BASE_FEATURES)}): {BASE_FEATURES}")

# ─────────────────────────────────────────────────────────────────────────────
# 2. FEATURE ENGINEERING (mirroring birds pipeline for consistency)
# ─────────────────────────────────────────────────────────────────────────────
print("\n🔧 Engineering features ...")

X = X_raw.copy()

# Interaction terms
X['order_family']      = X['order_enc']  * X['family_enc']
X['richness_family']   = X['species_richness'] * X['family_enc']
X['richness_order']    = X['species_richness'] * X['order_enc']
X['class_family']      = X['class_enc']  * X['family_enc']

# Spatial interactions
X['spatial']           = X['lat_grid'] * X['lon_grid']
X['spatial_uncertainty'] = (X['lat_grid'] + X['lon_grid']) * X['coordinateUncertaintyInMeters']

# Temporal interactions
X['season_month']      = X['season_enc'] * X['month']
X['year_month']        = X['year'] * X['month']
X['day_month']         = X['day']  * X['month']

# Polynomial features
for feat in ['species_richness', 'month', 'day', 'year']:
    X[f'{feat}_sq']   = X[feat] ** 2
    X[f'{feat}_sqrt'] = np.sqrt(np.abs(X[feat]) + 1)
    X[f'{feat}_cbrt'] = np.cbrt(X[feat])

# Log transforms
X['richness_log']     = np.log1p(X['species_richness'])
X['uncertainty_log']  = np.log1p(X['coordinateUncertaintyInMeters'])
X['month_log']        = np.log1p(X['month'])

# Ratios
X['rich_uncertainty_ratio'] = X['species_richness'] / (X['coordinateUncertaintyInMeters'] + 1)
X['family_order_ratio']     = (X['family_enc'] + 1) / (X['order_enc'] + 1)

# Aggregates
X['spatial_mean']    = (X['lat_grid'] + X['lon_grid']) / 2
X['temporal_mean']   = (X['day'] + X['month'] + X['decade']) / 3
X['category_mean']   = (X['order_enc'] + X['family_enc'] + X['class_enc']) / 3

# Binary indicators
X['richness_high']    = (X['species_richness'] > X['species_richness'].median()).astype(int)
X['uncertainty_high'] = (X['coordinateUncertaintyInMeters'] > X['coordinateUncertaintyInMeters'].median()).astype(int)
X['month_season']     = (X['month'] % 4).astype(int)

print(f"✓ Feature matrix: {X.shape[1]} features (+{X.shape[1] - len(BASE_FEATURES)} engineered)")

# ─────────────────────────────────────────────────────────────────────────────
# 3. TARGET TRANSFORM + SPLIT
# ─────────────────────────────────────────────────────────────────────────────
print("\n📈 Applying log1p transform to target ...")
y = np.log1p(y_orig)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, shuffle=True
)
print(f"   Train: {len(X_train):,}   Test: {len(X_test):,}")

scaler = RobustScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s  = scaler.transform(X_test)

FEATURE_NAMES = X.columns.tolist()

# ─────────────────────────────────────────────────────────────────────────────
# 4. HELPER: EVALUATION
# ─────────────────────────────────────────────────────────────────────────────
def evaluate(name, model, X_tr, y_tr, X_te, y_te):
    model.fit(X_tr, y_tr)
    y_pred    = model.predict(X_te)
    r2        = r2_score(y_te, y_pred)
    mae       = mean_absolute_error(y_te, y_pred)
    rmse      = np.sqrt(mean_squared_error(y_te, y_pred))
    # Pseudo-accuracy: percentage of predictions within ±25% of true
    within    = np.mean(np.abs(y_pred - y_te) / (np.abs(y_te) + 1e-9) < 0.25) * 100

    # Cross-validation R²
    cv_scores = cross_val_score(model, X_tr, y_tr, cv=5, scoring='r2')

    print(f"\n  📊 {name}")
    print(f"     R²         : {r2:.4f}")
    print(f"     CV-R² (5)  : {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")
    print(f"     MAE (log)  : {mae:.4f}")
    print(f"     RMSE (log) : {rmse:.4f}")
    print(f"     Within±25% : {within:.1f}%")
    return {
        'model': model,
        'name': name,
        'r2': float(r2),
        'cv_r2': float(cv_scores.mean()),
        'mae': float(mae),
        'rmse': float(rmse),
        'within_25pct': float(within),
        'y_pred': y_pred,
    }

# ─────────────────────────────────────────────────────────────────────────────
# 5. TRAIN MODELS
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("🚀 MODEL COMPARISON")
print(SEP)

results = []

# ── Linear Regression (Ridge for stability) ───────────────────────────────
lr = Ridge(alpha=1.0)
results.append(evaluate("Linear Regression (Ridge)", lr, X_train_s, y_train, X_test_s, y_test))

# ── XGBoost ───────────────────────────────────────────────────────────────
if HAS_XGB:
    xgb = XGBRegressor(
        n_estimators=500,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=42,
        n_jobs=-1,
        verbosity=0,
        early_stopping_rounds=30,
        eval_metric='rmse',
    )
    # XGBoost with eval set for early stopping
    xgb.fit(
        X_train_s, y_train,
        eval_set=[(X_test_s, y_test)],
        verbose=False,
    )
    # Re-evaluate via our helper (fit already done, we predict manually)
    y_pred_xgb  = xgb.predict(X_test_s)
    r2_xgb      = r2_score(y_test, y_pred_xgb)
    mae_xgb     = mean_absolute_error(y_test, y_pred_xgb)
    rmse_xgb    = np.sqrt(mean_squared_error(y_test, y_pred_xgb))
    within_xgb  = np.mean(np.abs(y_pred_xgb - y_test) / (np.abs(y_test) + 1e-9) < 0.25) * 100
    cv_xgb      = cross_val_score(
        XGBRegressor(n_estimators=200, max_depth=6, learning_rate=0.05,
                     subsample=0.8, random_state=42, verbosity=0, n_jobs=-1),
        X_train_s, y_train, cv=5, scoring='r2'
    )
    print(f"\n  📊 XGBoost Regressor")
    print(f"     R²         : {r2_xgb:.4f}")
    print(f"     CV-R² (5)  : {cv_xgb.mean():.4f} ± {cv_xgb.std():.4f}")
    print(f"     MAE (log)  : {mae_xgb:.4f}")
    print(f"     RMSE (log) : {rmse_xgb:.4f}")
    print(f"     Within±25% : {within_xgb:.1f}%")
    results.append({
        'model': xgb,
        'name': 'XGBoost',
        'r2': float(r2_xgb),
        'cv_r2': float(cv_xgb.mean()),
        'mae': float(mae_xgb),
        'rmse': float(rmse_xgb),
        'within_25pct': float(within_xgb),
        'y_pred': y_pred_xgb,
    })

# ─────────────────────────────────────────────────────────────────────────────
# 6. COMPARISON SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("📈 COMPARISON SUMMARY")
print(SEP)
print(f"  {'Model':<35} {'R²':>8} {'CV-R²':>8} {'MAE':>8} {'Within±25%':>12}")
print("  " + "-" * 75)
for r in results:
    print(f"  {r['name']:<35} {r['r2']:>8.4f} {r['cv_r2']:>8.4f} {r['mae']:>8.4f} {r['within_25pct']:>11.1f}%")

# ── Pick winner ───────────────────────────────────────────────────────────
winner = max(results, key=lambda x: x['r2'])
loser  = [r for r in results if r is not winner][0] if len(results) > 1 else None
print(f"\n  🏆 Winner: {winner['name']} (R²={winner['r2']:.4f})")
if loser:
    print(f"  📉 Runner: {loser['name']} (R²={loser['r2']:.4f})")

# ─────────────────────────────────────────────────────────────────────────────
# 7. SAVE ARTIFACTS
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("💾 SAVING ARTIFACTS")
print(SEP)

joblib.dump(winner['model'],  'plants_model.pkl')
joblib.dump(scaler,           'plants_scaler.pkl')
joblib.dump(FEATURE_NAMES,    'plants_feature_names.pkl')

comparison = {r['name']: {k: v for k, v in r.items() if k not in ('model', 'y_pred')} for r in results}
metadata = {
    'winner': winner['name'],
    'r2':     winner['r2'],
    'cv_r2':  winner['cv_r2'],
    'mae':    winner['mae'],
    'rmse':   winner['rmse'],
    'within_25pct': winner['within_25pct'],
    'features': FEATURE_NAMES,
    'base_features': BASE_FEATURES,
    'target_transform': 'log1p',
    'comparison': comparison,
}
joblib.dump(metadata, 'plants_metadata.pkl')
print("✓ plants_model.pkl        (best regression model)")
print("✓ plants_scaler.pkl       (RobustScaler)")
print("✓ plants_feature_names.pkl")
print("✓ plants_metadata.pkl")

# Feature importance (if available)
if hasattr(winner['model'], 'feature_importances_'):
    fi = pd.DataFrame({'Feature': FEATURE_NAMES, 'Importance': winner['model'].feature_importances_})
    fi = fi.sort_values('Importance', ascending=False)
    fi.to_csv('plants_feature_importance.csv', index=False)
    print("✓ plants_feature_importance.csv")
elif hasattr(winner['model'], 'coef_'):
    fi = pd.DataFrame({'Feature': FEATURE_NAMES, 'Coefficient': winner['model'].coef_})
    fi['AbsCoefficient'] = fi['Coefficient'].abs()
    fi = fi.sort_values('AbsCoefficient', ascending=False)
    fi.to_csv('plants_feature_importance.csv', index=False)
    print("✓ plants_feature_importance.csv (Ridge coefficients)")

# ─────────────────────────────────────────────────────────────────────────────
# 8. K-MEANS CLUSTERING
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("🗺️  TRAINING K-MEANS CLUSTERING MODEL")
print(SEP)

# Use geographic + taxonomic features from raw CSV
df_raw = pd.read_csv("koyna_plants_regression_density.csv")
df_cluster = df_raw.dropna(subset=['decimalLatitude', 'decimalLongitude']).copy()

cluster_features = ['decimalLatitude', 'decimalLongitude',
                    'class_enc', 'order_enc', 'year']
for col in cluster_features:
    if col not in df_cluster.columns:
        df_cluster[col] = 0

X_cluster = df_cluster[cluster_features].fillna(0)

km_scaler = StandardScaler()
X_cluster_s = km_scaler.fit_transform(X_cluster)

# Elbow test — pick optimal k (max 12)
print("\n  Finding optimal k via inertia ...")
inertias = []
K_RANGE = range(3, 13)
for k in K_RANGE:
    km_tmp = KMeans(n_clusters=k, random_state=42, n_init=10)
    km_tmp.fit(X_cluster_s)
    inertias.append(km_tmp.inertia_)

# Simple elbow: largest drop
drops = [inertias[i] - inertias[i+1] for i in range(len(inertias)-1)]
best_k = list(K_RANGE)[drops.index(max(drops)) + 1]
best_k = max(6, min(best_k, 10))   # keep sensible range
print(f"  Optimal k (elbow): {best_k}")

km = KMeans(n_clusters=best_k, random_state=42, n_init=20)
km.fit(X_cluster_s)

joblib.dump(km,       'plants_kmeans.pkl')
joblib.dump(km_scaler,'plants_kmeans_scaler.pkl')

cluster_meta = {
    'n_clusters': best_k,
    'features': cluster_features,
    'inertia': float(km.inertia_),
}
joblib.dump(cluster_meta, 'plants_kmeans_meta.pkl')

print(f"✓ plants_kmeans.pkl         (k={best_k})")
print("✓ plants_kmeans_scaler.pkl")
print("✓ plants_kmeans_meta.pkl")

# ─────────────────────────────────────────────────────────────────────────────
# FINAL SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("✅ TRAINING COMPLETE")
print(SEP)
print(f"  Winner     : {winner['name']}")
print(f"  R²         : {winner['r2']:.4f}")
print(f"  CV-R²      : {winner['cv_r2']:.4f}")
print(f"  MAE (log)  : {winner['mae']:.4f}")
print(f"  Within±25% : {winner['within_25pct']:.1f}%")
print(f"  Clusters   : k={best_k}")
print(SEP)
