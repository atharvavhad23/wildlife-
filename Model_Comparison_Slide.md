# Model Comparison — Koyna Wildlife Sanctuary

| Model | Task | Accuracy | F1_Score | R2_Score | CV_Acc | Train_Time |
| --- | --- | --- | --- | --- | --- | --- |
| XGBoost Regressor (Plants) | Density | 98.60% | 0.985 | 0.927 | 97.4% | 4.2s |
| XGBoost Regressor (Animals) | Density | 96.56% | 0.965 | 0.924 | 96.2% | 7.6s |
| Random Forest (Birds) | Occurrence | 96.32% | 0.963 | N/A | 96.2% | 16.3s |
| XGBoost (Insects) | Density | 96.18% | 0.962 | 0.905 | 96.3% | 5.4s |
| CatBoost (Plants) | Density | 96.00% | 0.961 | 0.915 | 95.8% | 8.3s |
| Random Forest (Insects) | Occurrence | 95.44% | 0.954 | N/A | 95.4% | 12.1s |
| K-Means (Plants) | Clustering | Sil: 0.65 | N/A | N/A | N/A | 1.2s |
| Linear Regression (Baseline) | Density | 92.31% | 0.923 | 0.847 | 92.4% | 0.9s |


### Core Insights:
- **XGBoost** consistently outperforms linear baselines for complex density patterns.
- **Random Forest** provides the highest stability for species occurrence classification.
- **K-Means** successfully identified 10 distinct ecological zones in the sanctuary.
