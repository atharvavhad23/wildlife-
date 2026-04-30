import pickle
import pandas as pd
from pathlib import Path

metadata_files = {
    "Density (Animals)": "animals_occurrence_metadata.pkl", # Need to check if this has density
    "Density (Birds)": "birds_metadata.pkl",
    "Density (Insects)": "insects_metadata.pkl",
    "Density (Plants)": "plants_metadata.pkl",
    "Occurrence (Animals)": "animals_occurrence_metadata.pkl",
    "Occurrence (Birds)": "birds_occurrence_metadata.pkl",
    "Occurrence (Insects)": "insects_occurrence_metadata.pkl",
    "Occurrence (Plants)": "plants_occurrence_metadata.pkl"
}

def extract_metadata():
    print("EXTRACTING ACTUAL MODEL METRICS...")
    print("-" * 50)
    
    all_results = []
    
    for label, filename in metadata_files.items():
        if Path(filename).exists():
            try:
                with open(filename, 'rb') as f:
                    meta = pickle.load(f)
                
                # Regressor metrics usually have 'r2'
                # Classifier metrics usually have 'accuracy' or 'f1'
                
                res = {"Model": label}
                
                if 'accuracy' in meta:
                    res["Accuracy"] = f"{meta['accuracy']*100:.2f}%" if isinstance(meta['accuracy'], float) else meta['accuracy']
                elif 'best_score' in meta: # Sometimes used for R2 in training scripts
                     res["Accuracy"] = f"{meta['best_score']*100:.2f}%"
                else:
                    res["Accuracy"] = "N/A"
                    
                if 'f1' in meta:
                    res["F1_Score"] = f"{meta['f1']:.4f}"
                elif 'weighted f1-score' in meta:
                    res["F1_Score"] = f"{meta['weighted f1-score']:.4f}"
                else:
                    res["F1_Score"] = "N/A"
                    
                if 'r2' in meta:
                    res["R2_Score"] = f"{meta['r2']:.4f}"
                else:
                    res["R2_Score"] = "N/A"
                    
                all_results.append(res)
                print(f"✅ Loaded {filename}: {res}")
                
            except Exception as e:
                print(f"❌ Error reading {filename}: {e}")
        else:
            print(f"⚠️ {filename} not found.")

    if all_results:
        df = pd.DataFrame(all_results)
        print("\nACTUAL METRICS TABLE:")
        print(df.to_string(index=False))
        df.to_csv("actual_model_metrics.csv", index=False)
    else:
        print("No metadata files could be read.")

if __name__ == "__main__":
    extract_metadata()
