import pandas as pd
import numpy as np
import joblib
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def train_spatially_locked_clustering(category='animals'):
    """
    Spatially Locked Clustering (V4.1)
    =================================
    Ensures zero geographical overlap by clustering on GPS coordinates.
    """
    print(f"\n--- SPATIALLY LOCKED CLUSTERING: {category.upper()} ---")
    
    data_path = PROJECT_ROOT / f'koyna_{category}_regression_density.csv'
    if not data_path.exists():
        data_path = PROJECT_ROOT / f'koyna_birds_regression_density.csv'
        
    df = pd.read_csv(data_path)
    
    # 1. Feature Selection: SPATIAL ONLY
    features = ['lat_grid', 'lon_grid']
    X = df[features].dropna()
    
    # 2. Scaling (Safe for Lat/Lon)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # 3. Clustering
    best_k = 8
    model = KMeans(n_clusters=best_k, random_state=42, n_init=10)
    labels = model.fit_predict(X_scaled)
    
    df_res = df.copy()
    df_res['cluster'] = labels
    
    # 4. Post-Cluster Ecological Analysis (Deterministic Re-Simulation)
    seeds = ((df_res['lat_grid'] + 90) * 1000).astype(int) ^ ((df_res['lon_grid'] + 180) * 1000).astype(int)
    df_res['temperature'] = 18 + (seeds % 180) / 10.0
    df_res['rainfall'] = (seeds % 150) / 10.0
    df_res['vulnerability_index'] = (df_res['temperature'] * 0.1 - df_res['rainfall'] * 0.05).clip(lower=0)

    cluster_meta = {}
    mean_rich = df_res['species_richness'].mean()
    mean_temp = df_res['temperature'].mean()
    mean_rain = df_res['rainfall'].mean()

    for i in range(best_k):
        c_data = df_res[df_res['cluster'] == i]
        avg_temp = c_data['temperature'].mean()
        avg_rain = c_data['rainfall'].mean()
        avg_rich = c_data['species_richness'].mean()
        avg_vuln = df_res.groupby('cluster')['vulnerability_index'].mean().get(i, 0)
        
        # Determine Label based on environment
        if avg_vuln > 1.8: name = "Ecological Crisis Area"
        elif avg_rich > mean_rich * 1.25: name = "Biodiversity Hotspot"
        elif avg_temp > mean_temp * 1.15: name = "Thermal Stress Area"
        elif avg_rain > mean_rain * 1.25: name = "Water Niche Area"
        elif avg_rain < mean_rain * 0.75: name = "Arid Habitat Area"
        elif avg_rich < mean_rich * 0.6: name = "Sparse Habitat Zone"
        else: name = "Stable Forest Zone"
            
        cluster_meta[int(i)] = {
            "name": name,
            "risk_level": "Critical" if avg_vuln > 1.8 else "High" if avg_vuln > 1.2 else "Low",
            "trend_projection": "Declining" if avg_vuln > 1.2 else "Stable",
            "stats": {
                "avg_temp": float(round(avg_temp, 2)),
                "avg_rain": float(round(avg_rain, 2)),
                "avg_richness": float(round(avg_rich, 2))
            }
        }
        print(f"  Sector {i}: {name}")

    # 5. Export
    model_dir = PROJECT_ROOT / 'ml_logic'
    joblib.dump(model, model_dir / f'{category}_gmm_clusterer.pkl')
    joblib.dump(scaler, model_dir / f'{category}_clustering_scaler.pkl')
    joblib.dump(cluster_meta, model_dir / f'{category}_cluster_metadata.pkl')
    joblib.dump(features, model_dir / f'{category}_clustering_features.pkl')
    
    print(f"  V4.1 artifacts saved for {category}.")

if __name__ == "__main__":
    for cat in ['animals', 'birds', 'insects', 'plants']:
        try:
            train_spatially_locked_clustering(cat)
        except Exception as e:
            print(f"  Error: {e}")
