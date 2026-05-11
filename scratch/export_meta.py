import joblib
import json

def convert(o):
    if isinstance(o, (float, int, str, bool, list, dict)) or o is None:
        return o
    return str(o)

try:
    meta_reg = joblib.load('d:/Wildlife_Conserve/ml_logic/birds_metadata.pkl')
    with open('d:/Wildlife_Conserve/scratch/birds_reg_meta.json', 'w') as f:
        json.dump(meta_reg, f, default=convert, indent=2)
except: pass

try:
    meta_class = joblib.load('d:/Wildlife_Conserve/ml_logic/birds_occurrence_metadata.pkl')
    with open('d:/Wildlife_Conserve/scratch/birds_class_meta.json', 'w') as f:
        json.dump(meta_class, f, default=convert, indent=2)
except: pass
