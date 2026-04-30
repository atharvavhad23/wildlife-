import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Use a clean style for academic presentation
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("viridis")

datasets = {
    "Animals": ("koyna_animals_regression_density.csv", "TARGET_sighting_density"),
    "Birds": ("koyna_birds_regression_density.csv", "bird_sighting_density"),
    "Insects": ("koyna_insects_regression_density.csv", "insect_sighting_density"),
    "Plants": ("koyna_plants_regression_density.csv", "plant_sighting_density")
}

def generate_slide_data(name, csv_path, target_col):
    df = pd.read_csv(csv_path)
    
    # Basic stats
    total_samples = len(df)
    mean_val = df[target_col].mean()
    median_val = df[target_col].median()
    
    # Coverage
    unique_grids = len(df.groupby(['lat_grid', 'lon_grid']))
    if 'species_richness' in df.columns:
        avg_richness = df['species_richness'].mean()
    else:
        avg_richness = "N/A"
        
    # Risk calculation (Execution Reality)
    # Following the friend's logic: High Density = High Alert/Risk
    high_thresh = df[target_col].quantile(0.75)
    low_thresh = df[target_col].quantile(0.25)
    
    high_risk = df[df[target_col] >= high_thresh]
    med_risk = df[(df[target_col] < high_thresh) & (df[target_col] >= low_thresh)]
    low_risk = df[df[target_col] < low_thresh]
    
    risk_stats = {
        'high': {'pct': len(high_risk)/total_samples*100, 'avg': high_risk[target_col].mean()},
        'med': {'pct': len(med_risk)/total_samples*100, 'avg': med_risk[target_col].mean()},
        'low': {'pct': len(low_risk)/total_samples*100, 'avg': low_risk[target_col].mean()}
    }
    
    # Generate Plot
    plt.figure(figsize=(8, 6))
    sns.histplot(df[target_col], bins=40, color='#27ae60', kde=True)
    plt.axvline(mean_val, color='red', linestyle='--', label=f'Mean: {mean_val:.2f}')
    plt.axvline(median_val, color='black', linestyle=':', label=f'Median: {median_val:.2f}')
    
    plt.title(f"Distribution of {name} Sighting Density (Target)", fontsize=14, pad=15)
    plt.xlabel(f"{name} per km²")
    plt.ylabel("Observation Count")
    plt.legend()
    
    plot_path = f"analysis_{name.lower()}.png"
    plt.savefig(plot_path, dpi=120, bbox_inches='tight')
    plt.close()
    
    return {
        'total': total_samples,
        'grids': unique_grids,
        'avg_richness': avg_richness,
        'mean': mean_val,
        'risk': risk_stats,
        'plot': plot_path
    }

print("Generating Data Analysis Reports...")
results = {}
for name, (path, target_col) in datasets.items():
    if Path(path).exists():
        print(f"Processing {name}...")
        results[name] = generate_slide_data(name, path, target_col)
    else:
        print(f"⚠️ {path} not found, skipping...")

# Create a Markdown Slide Report
with open("Analysis_Slide_Report.md", "w", encoding='utf-8') as f:
    f.write("# Koyna Wildlife Sanctuary — Data Analysis Slides\n\n")
    for name, data in results.items():
        f.write(f"## {name} Population Analysis\n")
        f.write("![Histogram Analysis](file:///d:/Wildlife_Conserve/" + data['plot'] + ")\n\n")
        f.write("### Scale & Coverage\n")
        f.write(f"- **{data['total']:,} total observations** analyzed across the sanctuary.\n")
        f.write(f"- Covers **{data['grids']} major spatial grids** (lat/lon clusters).\n")
        f.write(f"- Ecological Diversity: Avg. Species Richness of **{data['avg_richness']:.1f}** per grid.\n\n")
        f.write("### Execution Reality\n")
        f.write(f"**Average sighting density: {data['mean']:.2f} {name.lower()} per km²**\n\n")
        f.write(f"- 🔴 **High Alert Areas**: {data['risk']['high']['pct']:.1f}% → **{data['risk']['high']['avg']:.2f}** avg. density\n")
        f.write(f"- 🟡 **Medium Activity**: {data['risk']['med']['pct']:.1f}% → **{data['risk']['med']['avg']:.2f}** avg. density\n")
        f.write(f"- 🟢 **Stable/Low Density**: {data['risk']['low']['pct']:.1f}% → **{data['risk']['low']['avg']:.2f}** avg. density\n\n")
        f.write("---\n\n")

print("Analysis slides generated successfully.")
