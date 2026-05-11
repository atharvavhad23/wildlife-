import joblib
import os

path = 'd:/Wildlife_Conserve/ml_logic/birds_metadata.pkl'
if os.path.exists(path):
    meta = joblib.load(path)
    print("Birds Metadata:", meta)
else:
    print("File not found")
