# Backend Quick Start (3 Steps to Run)

## Current Status
✅ Backend folder organized  
✅ Centralized path config created  
✅ All code updated  
✅ Django validated  

⏳ **NEXT:** Move data/models, then run

---

## STEP 1: Activate Python Environment

```powershell
Set-Location "e:/miniproject_wildlfie"
./.venv/Scripts/Activate.ps1
cd wildlife-/backend
```

---

## STEP 2: Move Data & Model Files (One-time setup)

### Move Data Files
```powershell
# From wildlife-/ root, move to backend/data/
# (Run these from the wildlife-/ folder, NOT backend/)

cd ..  # Go to wildlife-/

# Raw data → backend/data/raw/
Move-Item "Koyna_animals_final.csv" "backend/data/raw/"
Move-Item "Koyna_birds_final.csv" "backend/data/raw/"
Move-Item "Koyna_insects_final.csv" "backend/data/raw/"
Move-Item "Koyna_plants_final.csv" "backend/data/raw/"
Move-Item "Koynaspecies.csv" "backend/data/raw/"
Move-Item "Koynaspecies_cleaned.csv" "backend/data/raw/"

# Processed data → backend/data/processed/
Move-Item "koyna_animals_regression_density.csv" "backend/data/processed/"
Move-Item "koyna_birds_regression_density.csv" "backend/data/processed/"
Move-Item "koyna_insects_regression_density.csv" "backend/data/processed/"
Move-Item "koyna_plants_regression_density.csv" "backend/data/processed/"
Move-Item "koyna_animals_classification_class.csv" "backend/data/processed/"
Move-Item "koyna_animals_regression_count.csv" "backend/data/processed/"

# External data → backend/data/external/
Move-Item "Koyna_IUCN_Tree_Species.csv" "backend/data/external/"
Move-Item "Koyna_Locality_Diversity.csv" "backend/data/external/"
```

### Move Model Files
```powershell
# Animal models → backend/models/animals/
Move-Item "wildlife_model.pkl" "backend/models/animals/"
Move-Item "scaler.pkl" "backend/models/animals/"
Move-Item "feature_names.pkl" "backend/models/animals/"
Move-Item "model_metadata.pkl" "backend/models/animals/"

# All occurrence models (from pkl files/ folder)
# Move animals occurrence files
Move-Item "pkl files/animals_occurrence_classifier.pkl" "backend/models/animals/"
Move-Item "pkl files/animals_occurrence_features.pkl" "backend/models/animals/"
Move-Item "pkl files/animals_occurrence_metadata.pkl" "backend/models/animals/"

# Move birds models
Move-Item "pkl files/birds_model.pkl" "backend/models/birds/"
Move-Item "pkl files/birds_scaler.pkl" "backend/models/birds/"
Move-Item "pkl files/birds_feature_names.pkl" "backend/models/birds/"
Move-Item "pkl files/birds_metadata.pkl" "backend/models/birds/"
Move-Item "pkl files/birds_occurrence_classifier.pkl" "backend/models/birds/"
Move-Item "pkl files/birds_occurrence_features.pkl" "backend/models/birds/"
Move-Item "pkl files/birds_occurrence_metadata.pkl" "backend/models/birds/"

# Move insects models
Move-Item "pkl files/insects_model.pkl" "backend/models/insects/"
Move-Item "pkl files/insects_scaler.pkl" "backend/models/insects/"
Move-Item "pkl files/insects_feature_names.pkl" "backend/models/insects/"
Move-Item "pkl files/insects_metadata.pkl" "backend/models/insects/"
Move-Item "pkl files/insects_occurrence_classifier.pkl" "backend/models/insects/"
Move-Item "pkl files/insects_occurrence_features.pkl" "backend/models/insects/"
Move-Item "pkl files/insects_occurrence_metadata.pkl" "backend/models/insects/"

# Move plants models
Move-Item "plants_model.pkl" "backend/models/plants/"
Move-Item "plants_scaler.pkl" "backend/models/plants/"
Move-Item "plants_feature_names.pkl" "backend/models/plants/"
Move-Item "plants_metadata.pkl" "backend/models/plants/"
Move-Item "plants_kmeans.pkl" "backend/models/plants/"
Move-Item "plants_kmeans_scaler.pkl" "backend/models/plants/"
Move-Item "plants_kmeans_meta.pkl" "backend/models/plants/"
Move-Item "pkl files/plants_occurrence_classifier.pkl" "backend/models/plants/"
Move-Item "pkl files/plants_occurrence_features.pkl" "backend/models/plants/"
Move-Item "pkl files/plants_occurrence_metadata.pkl" "backend/models/plants/"
```

### Move Reports
```powershell
Move-Item "feature_importance.csv" "backend/reports/feature_importance/"
Move-Item "birds_feature_importance.csv" "backend/reports/feature_importance/"
Move-Item "insects_feature_importance.csv" "backend/reports/feature_importance/"
Move-Item "plants_feature_importance.csv" "backend/reports/feature_importance/"
```

---

## STEP 3: Run Backend Server

```powershell
# Make sure you're in backend folder
cd wildlife-/backend

# Start Django server
python manage.py runserver
```

**Expected Output:**
```
Error loading animals model: No such file or directory...  ← Expected if models not moved yet
...
System check identified no issues (0 silenced).
Starting development server at http://127.0.0.1:8000/
```

Open browser: **http://127.0.0.1:8000**

---

## Test Backend is Working

```powershell
# In PowerShell, test API endpoints:
Invoke-RestMethod -Uri "http://127.0.0.1:8000/features/animals/" -Method GET
```

---

## File Structure After Setup

```
wildlife-/backend/
├── manage.py
├── db.sqlite3
├── wildlife_config.py           ✓ All paths
│
├── data/                        ✓ All CSVs organized
│   ├── raw/          (16 files)
│   ├── processed/     (6 files)
│   └── external/      (2 files)
│
├── models/                      ✓ All PKL models organized
│   ├── animals/      (7 files)
│   ├── birds/        (7 files)
│   ├── insects/      (7 files)
│   └── plants/      (10 files)
│
├── reports/
│   └── feature_importance/  (4 files)
│
├── predictor/
│   ├── views.py              ✓ Updated with wildlife_config
│   ├── utils/
│   │   ├── decision_engine.py
│   │   ├── environmental_data.py
│   │   └── trend_analysis.py
│   └── templates/
│
└── wildlife_project/
    ├── settings.py           ✓ Updated with wildlife_config import
    ├── urls.py
    └── wsgi.py
```

---

## Troubleshooting

### **Problem:** Django says "file not found"
```
Error: No such file or directory: 'backend/models/animals/wildlife_model.pkl'
```
**Solution:** Run Step 2 (move files) first before running server.

### **Problem:** "ModuleNotFoundError: wildlife_config"
```
ModuleNotFoundError: No module named 'wildlife_config'
```
**Solution:** Make sure you're in the `backend/` folder when running:
```powershell
cd wildlife-/backend
python manage.py runserver
```

### **Problem:** Permission error moving files
```
Move-Item : Access to the path ... is denied
```
**Solution:** Close any open files/editors, then try again.

### **Problem:** Port 8000 already in use
```
Error: That port is already in use.
```
**Solution:** Use different port:
```powershell
python manage.py runserver 8001
```

---

## What's Been Done

✅ **Organized Backend Structure**
- Backend folder created with clear separation of concerns
- Data files organized by raw/processed/external
- Models organized by category (animals/birds/insects/plants)
- Reports centralized

✅ **Centralized Configuration**
- Created `wildlife_config.py` with ALL file paths
- One source of truth for all data/model locations
- Easy to maintain and modify

✅ **Updated All Code**
- `settings.py` imports `wildlife_config`
- `views.py` uses `wildlife_config` instead of hardcoded paths
- Occurrence classifiers use centralized paths
- CSV loading uses centralized paths

✅ **Created Documentation**
- `BACKEND_SETUP.md` - Complete setup guide
- `ARCHITECTURE.md` - Visual architecture & data flow
- `QUICKSTART.md` - This file (3-step guide)

---

## Next Steps

1. **Move files** using Step 2 above
2. **Run backend** using Step 3 above
3. **Test APIs** to confirm everything works
4. **Connect frontend** to backend (separate process)

---

## Key Concepts

### Why centralized config?
- ✅ Change any path in ONE place (wildlife_config.py)
- ✅ No scattered hardcoded paths
- ✅ Easy to see all locations at a glance
- ✅ Helps with deployment (dev vs production)

### Why organized folders?
- ✅ Clear separation of concerns
- ✅ Easy backup/sync
- ✅ Professional project structure
- ✅ Scales better as project grows

### Path Resolution
```
views.py imports wildlife_config
  ↓
wildlife_config.py calculates paths from file location
  ↓
Path = backend/wildlife_config.py directory + subfolder
  ↓
Example: backend/models/animals/wildlife_model.pkl
```

---

## Files Modified

| File | Changes |
|------|---------|
| `backend/wildlife_config.py` | ✓ CREATED - centralized paths |
| `backend/wildlife_project/settings.py` | ✓ Updated to import wildlife_config |
| `backend/predictor/views.py` | ✓ Updated all paths to use wildlife_config |
| `backend/BACKEND_SETUP.md` | ✓ CREATED - detailed setup guide |
| `backend/ARCHITECTURE.md` | ✓ CREATED - architecture diagrams |

---

## Support

For detailed information, see:
- 📖 **BACKEND_SETUP.md** - Comprehensive guide
- 📊 **ARCHITECTURE.md** - Visual diagrams & data flow
- 🚀 **QUICKSTART.md** - This file

