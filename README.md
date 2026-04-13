# Wildlife Population Density Predictor

## Quick Start Guide

### Step 1: Install Dependencies
Open PowerShell in the `Wildlife_Conserve` folder and run:
```bash
pip install -r requirements.txt
```

### Step 2: Train the Model
```bash
python train_model.py
```
This will:
- Load the dataset
- Train Random Forest and Gradient Boosting models
- Save the best model as `wildlife_model.pkl`
- Save the scaler as `scaler.pkl`

### Step 3: Start the Django Web Application
```bash
python manage.py runserver
```
The Django server will start at `http://localhost:8000`

### Step 4: Use the Frontend
1. Open your browser and go to `http://localhost:8000`
2. Enter values for each feature (pre-filled with average values)
3. Click "Predict Population Density"
4. View the prediction and statistics

## Files Description

- **train_model.py**: Trains the regression models and saves them
- **manage.py**: Django management script
- **wildlife_project/**: Django project configuration
  - **settings.py**: Django settings
  - **urls.py**: URL routing
  - **wsgi.py**: WSGI configuration
- **predictor/**: Django app for predictions
  - **views.py**: View functions for prediction logic
  - **apps.py**: App configuration
  - **templates/index.html**: Frontend interface with prediction form
- **requirements.txt**: Python dependencies

## Model Details

The system uses two regression models:
1. **Random Forest Regressor** - Ensemble of decision trees
2. **Gradient Boosting Regressor** - Sequential boosting approach

The best performing model is automatically selected and used for predictions.

## Features Used

The model uses environmental and species characteristics including:
- Geographic grid coordinates (lat_grid, lon_grid)
- Temporal features (month, year, day, decade, season)
- Species taxonomy encoding (phylum, class, order, family)
- Ecological indicators (species_richness)
- Metadata encoding (taxonRank, basisOfRecord)

## Expected Output

The prediction returns:
- **Population Density**: Number of sightings per unit area
- **Density Level**: Categorized as Low/Medium/High
- **Confidence Bounds**: Upper and lower estimates
