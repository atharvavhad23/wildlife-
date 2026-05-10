import os
import sys
from datetime import datetime
from pathlib import Path

import django
import pandas as pd
from mongoengine.connection import get_connection
from pymongo.errors import ServerSelectionTimeoutError

BACKEND_DIR = Path(__file__).resolve().parents[1]
CSV_DIR = BACKEND_DIR.parent
ENV_FILE = BACKEND_DIR / 'core' / 'config' / '.env'

# ✅ FIXED
BATCH_SIZE = 1000
PROGRESS_INTERVAL = 2000


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        os.environ[key.strip()] = value.strip().strip('"').strip("'")


def setup_django() -> None:
    sys.path.insert(0, str(BACKEND_DIR / 'apps'))
    sys.path.insert(0, str(BACKEND_DIR))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wildlife_project.settings')
    django.setup()


def normalize_text(value):
    if value is None:
        return ''
    if isinstance(value, float) and pd.isna(value):
        return ''
    text = str(value).strip()
    return '' if text.lower() in {'', 'nan', 'none', 'null'} else text


def parse_float(value):
    try:
        return float(value)
    except:
        return None


def parse_datetime(value):
    try:
        return pd.to_datetime(value).to_pydatetime()
    except:
        return datetime.utcnow()


def read_csv_records(csv_path: Path):
    df = pd.read_csv(csv_path)
    df = df.fillna('')
    return df.to_dict(orient='records')


def ping_mongo():
    conn = get_connection()
    conn.admin.command('ping')
    print('MongoDB ping: OK')


# ---------------- SPECIES ---------------- #
def insert_species():
    from apps.species.models import Species

    files = [
        CSV_DIR / 'Koynaspecies_cleaned.csv',
        CSV_DIR / 'Koyna_IUCN_Tree_Species.csv'
    ]

    batch = []
    inserted = 0
    skipped = 0

    for file in files:
        if not file.exists():
            continue

        for record in read_csv_records(file):
            try:
                name = normalize_text(
                    record.get('Species_Name') or
                    record.get('name') or
                    record.get('species')
                )

                if not name:
                    skipped += 1
                    continue

                doc = {
                    'name': name,
                    'scientific_name': name,
                    'category': 'animals',
                    'iucn_status': 'DD',
                    'created_at': datetime.utcnow(),
                }

                batch.append(doc)

                if len(batch) >= BATCH_SIZE:
                    Species._get_collection().insert_many(batch)
                    inserted += len(batch)
                    batch = []
                    print(f'Inserted {inserted} species...')

            except:
                skipped += 1

    if batch:
        Species._get_collection().insert_many(batch)
        inserted += len(batch)

    print(f'Species inserted: {inserted}')
    print(f'Species skipped: {skipped}')


# ---------------- OBSERVATIONS ---------------- #
def insert_observations():
    from apps.observations.models import Observation

    files = [
        CSV_DIR / 'Koyna_animals_final.csv',
        CSV_DIR / 'Koyna_birds_final.csv',
        CSV_DIR / 'Koyna_insects_final.csv',
        CSV_DIR / 'Koyna_plants_final.csv',
    ]

    batch = []
    inserted = 0
    skipped = 0

    for file in files:
        if not file.exists():
            continue

        for record in read_csv_records(file):
            try:
                lat = parse_float(record.get('decimalLatitude'))
                lon = parse_float(record.get('decimalLongitude'))

                if lat is None or lon is None:
                    skipped += 1
                    continue

                doc = {
                    'species_name': normalize_text(
                        record.get('scientificName') or
                        record.get('species') or ''
                    ),
                    'location': {'lat': lat, 'lon': lon},
                    'geo_location': [lon, lat],
                    'observed_at': parse_datetime(record.get('eventDate')),
                    'source': 'csv',
                    'created_at': datetime.utcnow(),
                }

                # ✅ FIX: Always insert (no skipping)
                batch.append(doc)

                if len(batch) >= BATCH_SIZE:
                    Observation._get_collection().insert_many(batch)
                    inserted += len(batch)
                    batch = []
                    print(f'Inserted {inserted} observations...')

            except:
                skipped += 1

    if batch:
        Observation._get_collection().insert_many(batch)
        inserted += len(batch)

    print(f'Observations inserted: {inserted}')
    print(f'Observations skipped: {skipped}')


# ---------------- MAIN ---------------- #
def main():
    load_env_file(ENV_FILE)
    setup_django()
    ping_mongo()

    print('Starting species import...')
    insert_species()

    print('Starting observations import...')
    insert_observations()

    print('Seed complete.')


if __name__ == '__main__':
    main()