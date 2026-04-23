import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Set a consistent professional style
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("viridis")

datasets = {
    "Animals": ("koyna_animals_regression_density.csv", "TARGET_sighting_density"),
    "Birds": ("koyna_birds_regression_density.csv", "bird_sighting_density"),
    "Insects": ("koyna_insects_regression_density.csv", "insect_sighting_density"),
    "Plants": ("koyna_plants_regression_density.csv", "plant_sighting_density")
}

def create_combined_plot():
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Koyna Wildlife Sanctuary — Combined Population Distribution Analysis', fontsize=22, fontweight='bold', y=0.98)
    
    axes = axes.flatten()
    
    for i, (name, (path, target_col)) in enumerate(datasets.items()):
        ax = axes[i]
        if Path(path).exists():
            print(f"Adding {name} to combined plot...")
            df = pd.read_csv(path)
            
            # Use log scale if data is highly skewed (like Plants)
            data = df[target_col]
            
            palette = sns.color_palette("viridis", 4)
            sns.histplot(data, bins=30, kde=True, ax=ax, color=palette[i])
            
            mean_val = data.mean()
            median_val = data.median()
            
            ax.axvline(mean_val, color='red', linestyle='--', label=f'Mean: {mean_val:.1f}')
            ax.axvline(median_val, color='orange', linestyle='-', label=f'Median: {median_val:.1f}')
            
            ax.set_title(f'{name} Density Distribution', fontsize=16, fontweight='bold')
            ax.set_xlabel('Sighting Density (per km²)', fontsize=12)
            ax.set_ylabel('Frequency', fontsize=12)
            ax.legend()
        else:
            ax.text(0.5, 0.5, f'{name} Data Not Found', ha='center', va='center')
            ax.set_title(f'{name} (Missing)')

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    output_path = "combined_analysis_distribution.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Combined plot saved to {output_path}")

if __name__ == "__main__":
    create_combined_plot()
