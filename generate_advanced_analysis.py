import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Set academic style
plt.style.use('seaborn-v0_8-whitegrid')

datasets = {
    "Animals": ("koyna_animals_regression_density.csv", "TARGET_sighting_density"),
    "Birds": ("koyna_birds_regression_density.csv", "bird_sighting_density"),
    "Insects": ("koyna_insects_regression_density.csv", "insect_sighting_density"),
    "Plants": ("koyna_plants_regression_density.csv", "plant_sighting_density")
}

season_map = {0: 'Winter', 1: 'Summer', 2: 'Monsoon', 3: 'Post-Monsoon'}

def generate_advanced_plots():
    all_data = []
    
    for name, (path, target_col) in datasets.items():
        if Path(path).exists():
            df = pd.read_csv(path)
            temp_df = df[['season_enc', target_col]].copy()
            temp_df.columns = ['Season', 'Density']
            temp_df['Category'] = name
            all_data.append(temp_df)
    
    if not all_data:
        print("No data found.")
        return

    full_df = pd.concat(all_data)
    full_df['Season Name'] = full_df['Season'].map(season_map)
    
    # --- 1. Heatmap: Mean Density by Category and Season ---
    pivot_df = full_df.pivot_table(index='Category', columns='Season Name', values='Density', aggfunc='mean')
    
    plt.figure(figsize=(10, 6))
    sns.heatmap(pivot_df, annot=True, fmt=".1f", cmap="YlOrRd", linewidths=.5)
    plt.title('Mean Sighting Density: Category × Season (Heatmap)', fontsize=16, fontweight='bold')
    plt.savefig('advanced_analysis_heatmap.png', dpi=300, bbox_inches='tight')
    print("Heatmap saved to advanced_analysis_heatmap.png")
    
    # --- 2. Box Plot: Density distribution by Category ---
    plt.figure(figsize=(10, 6))
    # Using log scale for the boxplot because Plant density is much higher than others
    sns.boxplot(x='Category', y='Density', data=full_df, palette='viridis')
    plt.yscale('log')
    plt.title('Density Distribution by Category (Log Scale)', fontsize=16, fontweight='bold')
    plt.ylabel('Density (Log Scale)', fontsize=12)
    plt.savefig('advanced_analysis_boxplot.png', dpi=300, bbox_inches='tight')
    print("Boxplot saved to advanced_analysis_boxplot.png")

if __name__ == "__main__":
    generate_advanced_plots()
