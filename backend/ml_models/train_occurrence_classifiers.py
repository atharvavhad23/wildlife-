import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split

warnings.filterwarnings('ignore')

DATASETS = {
    'animals': {
        'csv': 'koyna_animals_regression_density.csv',
        'target': 'TARGET_sighting_density',
        'features': [
            'coordinateUncertaintyInMeters', 'month', 'year', 'day', 'decade',
            'lat_grid', 'lon_grid', 'phylum_enc', 'class_enc', 'order_enc',
            'family_enc', 'taxonRank_enc', 'basisOfRecord_enc', 'season_enc',
            'species_richness',
        ],
    },
    'birds': {
        'csv': 'koyna_birds_regression_density.csv',
        'target': 'bird_sighting_density',
        'features': [
            'coordinateUncertaintyInMeters', 'day', 'month', 'year', 'decade',
            'order_enc', 'family_enc', 'taxonRank_enc', 'basisOfRecord_enc',
            'season_enc', 'lat_grid', 'lon_grid', 'species_richness',
        ],
    },
    'insects': {
        'csv': 'koyna_insects_regression_density.csv',
        'target': 'insect_sighting_density',
        'features': [
            'coordinateUncertaintyInMeters', 'day', 'month', 'year', 'decade',
            'order_enc', 'family_enc', 'taxonRank_enc', 'basisOfRecord_enc',
            'season_enc', 'lat_grid', 'lon_grid', 'species_richness',
        ],
    },
    'plants': {
        'csv': 'koyna_plants_regression_density.csv',
        'target': 'plant_sighting_density',
        'features': [
            'coordinateUncertaintyInMeters', 'day', 'month', 'year', 'decade',
            'season_enc', 'lat_grid', 'lon_grid', 'species_richness',
            'order_enc', 'family_enc', 'class_enc', 'taxonRank_enc', 'basisOfRecord_enc',
        ],
    },
}


def _trend_labels(df: pd.DataFrame, target_col: str) -> pd.Series:
    sort_cols = [c for c in ['lat_grid', 'lon_grid', 'year', 'month', 'day'] if c in df.columns]
    grouped = df.sort_values(sort_cols).groupby(['lat_grid', 'lon_grid'], dropna=False)[target_col]
    pct = grouped.pct_change().replace([np.inf, -np.inf], np.nan).fillna(0.0)

    labels = np.where(pct > 0.05, 'rising', np.where(pct < -0.05, 'declining', 'stable'))
    return pd.Series(labels, index=df.index)


def _safe_numeric(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in cols:
        if col not in out.columns:
            out[col] = 0
        out[col] = pd.to_numeric(out[col], errors='coerce')
        median = out[col].median()
        out[col] = out[col].fillna(float(median) if np.isfinite(median) else 0.0)
    return out


def train_one(category: str, cfg: dict) -> dict:
    csv_path = Path(cfg['csv'])
    if not csv_path.exists():
        raise FileNotFoundError(f'Missing dataset: {csv_path}')

    df = pd.read_csv(csv_path)
    features = cfg['features']
    target = cfg['target']

    df = _safe_numeric(df, features + [target])
    y = _trend_labels(df, target)
    x = df[features]

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    model = RandomForestClassifier(
        n_estimators=400,
        max_depth=14,
        min_samples_split=4,
        min_samples_leaf=2,
        class_weight='balanced_subsample',
        random_state=42,
        n_jobs=-1,
    )
    model.fit(x_train, y_train)

    pred = model.predict(x_test)
    acc = float(accuracy_score(y_test, pred))

    report = classification_report(y_test, pred, output_dict=True, zero_division=0)
    per_class = {
        label: {
            'precision': float(metrics.get('precision', 0.0)),
            'recall': float(metrics.get('recall', 0.0)),
            'f1': float(metrics.get('f1-score', 0.0)),
        }
        for label, metrics in report.items()
        if label in {'rising', 'stable', 'declining'}
    }

    joblib.dump(model, f'{category}_occurrence_classifier.pkl')
    joblib.dump(features, f'{category}_occurrence_features.pkl')
    joblib.dump(
        {
            'model': 'RandomForestClassifier',
            'accuracy': acc,
            'features': features,
            'labels': ['declining', 'stable', 'rising'],
            'per_class': per_class,
        },
        f'{category}_occurrence_metadata.pkl',
    )

    return {
        'category': category,
        'accuracy': acc,
        'support': int(len(x)),
        'distribution': y.value_counts().to_dict(),
    }


def main() -> None:
    print('=' * 72)
    print('RANDOM FOREST OCCURRENCE TREND CLASSIFIERS')
    print('=' * 72)

    results = []
    for category, cfg in DATASETS.items():
        print(f'\nTraining {category} occurrence classifier...')
        result = train_one(category, cfg)
        results.append(result)
        print(f"  accuracy: {result['accuracy']:.4f}  samples: {result['support']}")
        print(f"  distribution: {result['distribution']}")

    print('\n' + '=' * 72)
    print('Saved artifacts per category:')
    print('  <category>_occurrence_classifier.pkl')
    print('  <category>_occurrence_features.pkl')
    print('  <category>_occurrence_metadata.pkl')
    print('=' * 72)


if __name__ == '__main__':
    main()
