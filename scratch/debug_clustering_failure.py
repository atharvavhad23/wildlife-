import os
import django
import pandas as pd
import numpy as np

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wildlife_project.settings')
django.setup()

from predictor.views import _get_labeled_df

def debug_clustering(category='birds', n=8):
    print(f"--- Debugging {category} (n={n}) ---")
    df = _get_labeled_df(n, category)
    if df is None:
        print("Error: DataFrame is None")
        return
        
    print(f"Total Rows: {len(df)}")
    print("Cluster Distribution:")
    print(df['cluster'].value_counts())
    
    unique_clusters = df['cluster'].unique()
    print(f"Unique Cluster IDs: {unique_clusters}")
    
    if len(unique_clusters) <= 1:
        print("FAILURE: Only one cluster detected!")
        # Inspect features
        feats = ['lat_grid', 'lon_grid', 'temperature', 'rainfall', 'humidity', 'vulnerability_index']
        print("\nFeature Sample (First 5 rows):")
        print(df[feats].head())
        print("\nFeature Variance:")
        print(df[feats].var())
    else:
        print(f"SUCCESS: {len(unique_clusters)} clusters generated.")

if __name__ == "__main__":
    debug_clustering('birds', 13) # Match user screenshot
    debug_clustering('animals', 8)
