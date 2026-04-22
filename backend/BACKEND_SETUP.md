# Backend Setup & Run Guide

## Current Backend Structure (Optimized)

```
backend/
├── manage.py                    # Django management (run commands from here)
├── db.sqlite3                   # SQLite database
├── wildlife_config.py           # ✓ CENTRALIZED PATH CONFIG (main file to edit)
├── wildlife_project/            # Django project configuration
│   ├── __init__.py
│   ├── settings.py              # ✓ Updated with wildlife_config import
│   ├── urls.py                  # All API endpoints
│   ├── wsgi.py                  # Production WSGI entry
│
├── predictor/                   # Main Django app
│   ├── apps.py
│   ├── views.py                 # ✓ Updated with wildlife_config imports
│   ├── scratch_views.py
│   ├── __init__.py
│   ├── utils/                   # Business logic modules
│   │   ├── __init__.py
│   │   ├── decision_engine.py   # Conservation decision support
│   │   ├── environmental_data.py # Weather & ecological data
│   │   ├── trend_analysis.py    # Population trend analysis
│   └── templates/               # HTML templates (if used)
│
├── data/                        # ✓ ALL DATA FILES (organized)
│   ├── raw/                     # Original CSV files
│   │   ├── Koyna_animals_final.csv
│   │   ├── Koyna_birds_final.csv
│   │   ├── Koyna_insects_final.csv
│   │   ├── Koyna_plants_final.csv
│   │   ├── Koynaspecies.csv
│   │   ├── Koynaspecies_cleaned.csv
│   │
│   ├── processed/               # Prepared CSV files for training
│   │   ├── koyna_animals_regression_density.csv
│   │   ├── koyna_birds_regression_density.csv
│   │   ├── koyna_insects_regression_density.csv
│   │   ├── koyna_plants_regression_density.csv
│   │   ├── koyna_animals_classification_class.csv
│   │   ├── koyna_animals_regression_count.csv
│   │
│   └── external/                # Reference/auxiliary data
│       ├── Koyna_IUCN_Tree_Species.csv
│       ├── Koyna_Locality_Diversity.csv
│
├── models/                      # ✓ ALL MODEL FILES (organized by category)
│   ├── animals/
│   │   ├── wildlife_model.pkl           # Main regression model
│   │   ├── scaler.pkl                   # Feature scaler
│   │   ├── feature_names.pkl            # Feature list
│   │   ├── model_metadata.pkl           # Metrics
│   │   ├── animals_occurrence_classifier.pkl
│   │   ├── animals_occurrence_features.pkl
│   │   ├── animals_occurrence_metadata.pkl
│   │
│   ├── birds/
│   │   ├── birds_model.pkl
│   │   ├── birds_scaler.pkl
│   │   ├── birds_feature_names.pkl
│   │   ├── birds_metadata.pkl
│   │   ├── birds_occurrence_classifier.pkl
│   │   ├── birds_occurrence_features.pkl
│   │   ├── birds_occurrence_metadata.pkl
│   │
│   ├── insects/
│   │   ├── insects_model.pkl
│   │   ├── insects_scaler.pkl
│   │   ├── insects_feature_names.pkl
│   │   ├── insects_metadata.pkl
│   │   ├── insects_occurrence_classifier.pkl
│   │   ├── insects_occurrence_features.pkl
│   │   ├── insects_occurrence_metadata.pkl
│   │
│   └── plants/
│       ├── plants_model.pkl
│       ├── plants_scaler.pkl
│       ├── plants_feature_names.pkl
│       ├── plants_metadata.pkl
│       ├── plants_kmeans.pkl
│       ├── plants_kmeans_scaler.pkl
│       ├── plants_kmeans_meta.pkl
│       ├── plants_occurrence_classifier.pkl
│       ├── plants_occurrence_features.pkl
│       ├── plants_occurrence_metadata.pkl
│
└── reports/                     # ✓ FEATURE IMPORTANCE REPORTS
    └── feature_importance/
        ├── feature_importance.csv
        ├── birds_feature_importance.csv
        ├── insects_feature_importance.csv
        ├── plants_feature_importance.csv
```

## Main Backend Files & Their Purpose

| File | Purpose | Status |
|------|---------|--------|
| **manage.py** | Django CLI entry point. Always run from `backend/` folder | ✓ Ready |
| **wildlife_config.py** | **CENTRALIZED PATH MANAGEMENT** - All data/model paths defined here | ✓ Created |
| **settings.py** | Django config (database, apps, email, paths) | ✓ Updated |
| **urls.py** | API route mapping (all endpoints) | ✓ Ready |
| **views.py** | All view functions (predictions, dashboards, clustering) | ✓ Updated to use wildlife_config |
| **apps.py** | Django app configuration | ✓ Ready |
| **decision_engine.py** | Conservation decision logic | ✓ Ready |
| **environmental_data.py** | Weather & ecology data | ✓ Ready |
| **trend_analysis.py** | Population trend analysis | ✓ Ready |

## How to Run Backend

### Step 1: Prepare Python Environment
```powershell
# Navigate to project root
Set-Location "e:/miniproject_wildlfie"

# Activate virtual environment
./.venv/Scripts/Activate.ps1

# Install dependencies (if not already installed)
pip install -r wildlife-/requirements.txt
```

### Step 2: Navigate to Backend
```powershell
cd wildlife-/backend
```

### Step 3: Start Django Development Server
```powershell
python manage.py runserver
```

**Output will show:**
```
Django version X.X.X, using settings 'wildlife_project.settings'
Starting development server at http://127.0.0.1:8000/
```

### Step 4: Access Backend
Open browser: **http://127.0.0.1:8000**

---

## API Endpoints (after backend starts)

### Prediction Endpoints
```
POST   /predict/animals/          - Predict animal density
GET    /predict/animals/result/   - Get prediction result
POST   /predict/birds/            - Predict bird density
GET    /predict/birds/result/     - Get prediction result
POST   /predict/insects/          - Predict insect density
GET    /predict/insects/result/   - Get prediction result
POST   /predict/plants/           - Predict plant density
```

### Feature & Dashboard Endpoints
```
GET    /features/animals/         - Get animal feature ranges
GET    /features/birds/           - Get bird feature ranges
GET    /features/insects/         - Get insect feature ranges
GET    /features/plants/          - Get plant feature ranges

GET    /dashboard/animals/        - Animal dashboard data
GET    /dashboard/birds/          - Bird dashboard data
GET    /dashboard/insects/        - Insect dashboard data
```

### Clustering & Analysis
```
GET    /api/animals/clustering/   - Animal spatial clustering
GET    /api/birds/clustering/     - Bird spatial clustering
GET    /api/insects/clustering/   - Insect spatial clustering
GET    /api/plants/clustering/    - Plant spatial clustering
```

### Authentication (OTP)
```
POST   /auth/send-otp/            - Send OTP to email
POST   /auth/verify-otp/          - Verify OTP code
```

---

## Important: File Setup (NEXT STEPS)

**Current Status:** Backend code is configured but data/model files are still in the root (`wildlife-/` folder).

**To fully activate the backend, you must move files:**

### Step A: Move Data Files to `backend/data/`

```powershell
# From wildlife-/ root, move raw data
Move-Item "Koyna_animals_final.csv" "backend/data/raw/"
Move-Item "Koyna_birds_final.csv" "backend/data/raw/"
Move-Item "Koyna_insects_final.csv" "backend/data/raw/"
Move-Item "Koyna_plants_final.csv" "backend/data/raw/"
Move-Item "Koynaspecies.csv" "backend/data/raw/"
Move-Item "Koynaspecies_cleaned.csv" "backend/data/raw/"

# Move processed CSVs
Move-Item "koyna_animals_regression_density.csv" "backend/data/processed/"
Move-Item "koyna_birds_regression_density.csv" "backend/data/processed/"
Move-Item "koyna_insects_regression_density.csv" "backend/data/processed/"
Move-Item "koyna_plants_regression_density.csv" "backend/data/processed/"
Move-Item "koyna_animals_classification_class.csv" "backend/data/processed/"
Move-Item "koyna_animals_regression_count.csv" "backend/data/processed/"

# Move external CSVs
Move-Item "Koyna_IUCN_Tree_Species.csv" "backend/data/external/"
Move-Item "Koyna_Locality_Diversity.csv" "backend/data/external/"
```

### Step B: Move Model Files to `backend/models/`

```powershell
# Move animal models
Move-Item "wildlife_model.pkl" "backend/models/animals/"
Move-Item "scaler.pkl" "backend/models/animals/"
Move-Item "feature_names.pkl" "backend/models/animals/"
Move-Item "model_metadata.pkl" "backend/models/animals/"
Move-Item "animals_occurrence_classifier.pkl" "backend/models/animals/"
Move-Item "animals_occurrence_features.pkl" "backend/models/animals/"
Move-Item "animals_occurrence_metadata.pkl" "backend/models/animals/"

# Move bird models
Move-Item "pkl files/birds_*.pkl" "backend/models/birds/"

# Move insect models
Move-Item "pkl files/insects_*.pkl" "backend/models/insects/"

# Move plant models
Move-Item "plants_*.pkl" "backend/models/plants/"

# Move occurrence models for all categories
Move-Item "pkl files/*_occurrence_*.pkl" "backend/models/animals/" # animals
Move-Item "pkl files/*_occurrence_*.pkl" "backend/models/birds/" # birds
# ... etc
```

### Step C: Move Feature Importance Reports
```powershell
Move-Item "feature_importance.csv" "backend/reports/feature_importance/"
Move-Item "birds_feature_importance.csv" "backend/reports/feature_importance/"
Move-Item "insects_feature_importance.csv" "backend/reports/feature_importance/"
Move-Item "plants_feature_importance.csv" "backend/reports/feature_importance/"
```

---

## How Path Management Works

All file paths are **centralized** in `backend/wildlife_config.py`:

```python
# Example from wildlife_config.py
ANIMALS_MODEL_PKL = MODELS_DIR / "animals" / "wildlife_model.pkl"
BIRDS_MODEL_PKL = MODELS_DIR / "birds" / "birds_model.pkl"
PROCESSED_ANIMALS_REGRESSION_CSV = PROCESSED_DATA_DIR / "koyna_animals_regression_density.csv"
```

When you load a model in `views.py`, use:
```python
import wildlife_config
model = joblib.load(str(wildlife_config.ANIMALS_MODEL_PKL))
```

**Benefits:**
- ✓ All paths in ONE file (easy to maintain)
- ✓ No hardcoded paths scattered throughout code
- ✓ Easy to change folders without touching views.py
- ✓ Clear organization by category & file type

---

## Configuration Files to Update (Optional)

### Update .env for Email (Optional)
Create `backend/.env`:
```
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=your-email@gmail.com
```

### Update Database (if needed)
```powershell
cd backend
python manage.py migrate
```

---

## Troubleshooting

### Models Not Loading
```
Error: No such file or directory: 'backend/models/animals/wildlife_model.pkl'
```
**Solution:** Run Step A & B above to move files to correct folders.

### Import Error: wildlife_config
```
ModuleNotFoundError: No module named 'wildlife_config'
```
**Solution:** Ensure you're running commands from `backend/` folder:
```powershell
cd backend
python manage.py runserver
```

### CSV File Not Found
```
Error loading animals data: FileNotFoundError
```
**Solution:** Move data files using Step A above.

---

## Summary

✅ **Backend folder structure is optimized**  
✅ **All paths centralized in wildlife_config.py**  
✅ **All code updated to use new paths**  
✅ **Django configuration validated**  

**⚠️ NEXT:** Move data/model files from `wildlife-/` to `backend/data/` and `backend/models/` as shown in "File Setup" section.

**THEN:** Run `python manage.py runserver` from `backend/` folder.

