# ML Validation Summary

Generated from:
- `validation_report.json`
- `validation_report.csv`
- `compatibility_report.json`
- `compatibility_report.csv`
- `validate_models_full.py`
- `validate_dir.py`

## Working Production Models
- `animals_occurrence_classifier.pkl`
- `birds_model.pkl`
- `birds_occurrence_classifier.pkl`
- `insects_model.pkl`
- `insects_occurrence_classifier.pkl`
- `plants_model.pkl`
- `plants_occurrence_classifier.pkl`
- `plants_kmeans.pkl`
- `wildlife_model.pkl`

## Broken Artifacts
- None in the final validation runs.

## Missing Files From Legacy Expectations
- `animals_model.pkl`
- `animals_count_model.pkl`
- `animals_feature_names.pkl`
- `animals_metadata.pkl`
- `birds_feature_names.pkl`

## Feature Mismatches Fixed
- `validate_models_full.py` now builds sample inputs from real feature metadata or `n_features_in_`.
- Shape mismatch failures were eliminated for:
  - `birds_model.pkl`
  - `insects_model.pkl`
  - `plants_model.pkl`
  - `plants_kmeans.pkl`

## Helper / Cache Artifacts
- `thumbnail_cache.pkl` is treated as a helper/cache artifact and skipped from predictive validation.

## Metadata Cleanup
Normalized metadata payloads now include:
- `model_name`
- `target`
- `feature_count`

Updated files include:
- `animals_occurrence_metadata.pkl`
- `birds_metadata.pkl`
- `birds_occurrence_metadata.pkl`
- `insects_metadata.pkl`
- `insects_occurrence_metadata.pkl`
- `model_metadata.pkl`
- `plants_kmeans_meta.pkl`
- `plants_metadata.pkl`
- `plants_occurrence_metadata.pkl`

## Compatibility Status
- `sklearn`: safe
- `xgboost`: safe

## Final Recommendations
- Keep the validated prediction models only.
- Treat the missing legacy `animals_*` files as stale expectations unless they are required by a downstream route.
- Review legacy metadata/helper artifacts before deleting anything.
- Prefer `backend/ml_models/` as the single source of truth for runtime model loading.
