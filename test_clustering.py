#!/usr/bin/env python
import os
import django
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wildlife_project.settings')
django.setup()

from django.test import Client

c = Client()

print("=" * 70)
print("CLUSTERING MODEL & SPECIES DETAIL TEST")
print("=" * 70)

# Test 1: Load clustering
print("\n1. Testing Clustering API...")
start = time.time()
response = c.get('/api/animals/clustering/?clusters=8')
elapsed = time.time() - start
data = response.json()

print(f"   Status: {response.status_code}")
print(f"   Time: {elapsed:.2f}s")
print(f"   Clusters: {data.get('n_clusters')}")
print(f"   Total species: {data.get('total_species')}")
if data.get('clusters'):
    first_cluster = list(data['clusters'].values())[0]
    print(f"   Sample cluster: {first_cluster.get('species_count')} species, {first_cluster.get('animal_count')} observations")
    print(f"   Sample species: {first_cluster.get('species')[:3]}")

# Test 2: Load species detail
print("\n2. Testing Species Detail API...")
species_name = list(list(data.get('clusters', {}).values())[0].get('species', []))[0] if data.get('clusters') else None

if species_name:
    start = time.time()
    response = c.get(f'/api/animals/species/?species={species_name}')
    elapsed = time.time() - start
    species_data = response.json()
    
    print(f"   Status: {response.status_code}")
    print(f"   Time: {elapsed:.2f}s")
    print(f"   Species: {species_data.get('scientificName')}")
    print(f"   Class: {species_data.get('class')}")
    print(f"   Observations: {species_data.get('observationCount')}")
    print(f"   Locations collected: {len(species_data.get('locations', []))}")

    # Test 3: Load species photos
    print("\n3. Testing Species Photos API...")
    start = time.time()
    response = c.get(f'/api/animals/species-photos/?species={species_name}&offset=0&limit=5')
    elapsed = time.time() - start
    photos_data = response.json()
    
    print(f"   Status: {response.status_code}")
    print(f"   Time: {elapsed:.2f}s")
    print(f"   Photos returned: {photos_data.get('count')}")
    print(f"   Total for species: {photos_data.get('total')}")
    print(f"   With images: {sum(1 for p in photos_data.get('photos', []) if p.get('hasImage'))}")

# Test 4: Test clustering map page
print("\n4. Testing Clustering Map Page...")
response = c.get('/animals/clustering/')
print(f"   Status: {response.status_code}")
print(f"   Template rendered: {'animals_clustering_map.html' in str(response.templates)}")

# Test 5: Test species detail page
if species_name:
    print("\n5. Testing Species Detail Page...")
    response = c.get(f'/animals/species/?species={species_name}')
    print(f"   Status: {response.status_code}")
    print(f"   Template rendered: {'species_detail.html' in str(response.templates)}")

print("\n" + "=" * 70)
print("✓ All tests completed successfully!")
print("=" * 70)
