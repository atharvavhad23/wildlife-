import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from pathlib import Path

def analyze_data_sensitivity(category='animals'):
    csv_path = Path(f'koyna_{category}_regression_density.csv')
    if not csv_path.exists():
        # Try finding the base file
        csv_path = Path(f'Koyna_{category}_final.csv')
        if not csv_path.exists():
            print(f"File {csv_path} not found.")
            return

    df = pd.read_csv(csv_path)
    print(f"\n=== Analyzing {category.upper()} Data Sensitivity ===")
    print(f"Total Rows: {len(df)}")
    
    # Target column
    target = 'TARGET_sighting_density' if 'TARGET_sighting_density' in df.columns else None
    if not target:
        # Fallback to finding anything with 'density' in name
        density_cols = [c for c in df.columns if 'density' in c.lower()]
        if density_cols: target = density_cols[0]
    
    if not target:
        print("No target density column found.")
        return

    # Check variation in key features
    key_features = ['year', 'temperature', 'rainfall', 'humidity', 'species_richness']
    present_features = [f for f in key_features if f in df.columns]
    
    stats = df[present_features + [target]].describe().T
    print("\nFeature Statistics:")
    print(stats[['mean', 'std', 'min', 'max']])

    # Correlation Analysis
    correlations = df[present_features + [target]].corr()[target].sort_values(ascending=False)
    print("\nCorrelations with Target Density:")
    print(correlations)

    # Check if Year has any variation
    if 'year' in df.columns:
        year_counts = df['year'].value_counts().sort_index()
        print(f"\nYear Distribution (Unique years: {len(year_counts)}):")
        print(year_counts.head(10))

    # IDENTIFY THE PROBLEM: If Year and Target are NOT correlated, the model won't learn temporal trends.
    # If correlations are near zero, we MUST synthesize a more realistic dataset.

if __name__ == "__main__":
    for cat in ['animals', 'birds', 'insects', 'plants']:
        analyze_data_sensitivity(cat)
