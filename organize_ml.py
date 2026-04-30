import os
import shutil
from pathlib import Path

ml_logic_dir = Path("ml_logic")
ml_logic_dir.mkdir(exist_ok=True)

# Additional related files to move
extra_files = [
    "prepare_birds_data.py",
    "prepare_insects_data.py",
    "prepare_plants_data.py",
    "extract_actual_metrics.py",
    "actual_model_metrics.csv",
    "generate_pca_accuracy_table.py",
    "generate_comparison_table.py",
    "generate_f1_report.py",
    "Model_Comparison_Table.csv"
]

for item in extra_files:
    item_path = Path(item)
    if item_path.exists():
        print(f"Moving {item} to ml_logic/")
        shutil.move(str(item_path), str(ml_logic_dir / item_path.name))

print("\n✅ Final organization complete.")
