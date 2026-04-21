#!/usr/bin/env python
import os
import django
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wildlife_project.settings')
django.setup()

from django.test import Client

c = Client()

print("=" * 60)
print("Testing parallel thumbnail resolution performance")
print("=" * 60)

# Test animals gallery first batch
start = time.time()
response = c.get('/photos/animals/?offset=0&limit=24')
elapsed = time.time() - start
data = response.json()

print(f"\n✓ Animals Gallery (first 24):")
print(f"  Status: {response.status_code}")
print(f"  Time: {elapsed:.2f}s")
print(f"  Photos: {data.get('count')}/{data.get('total')}")
print(f"  With images: {sum(1 for p in data.get('photos', []) if p.get('hasImage'))}/24")

# Test birds gallery
start = time.time()
response = c.get('/photos/birds/?offset=0&limit=24')
elapsed = time.time() - start
data = response.json()

print(f"\n✓ Birds Gallery (first 24):")
print(f"  Status: {response.status_code}")
print(f"  Time: {elapsed:.2f}s")
print(f"  Photos: {data.get('count')}/{data.get('total')}")
print(f"  With images: {sum(1 for p in data.get('photos', []) if p.get('hasImage'))}/24")

# Test insects gallery  
start = time.time()
response = c.get('/photos/insects/?offset=0&limit=24')
elapsed = time.time() - start
data = response.json()

print(f"\n✓ Insects Gallery (first 24):")
print(f"  Status: {response.status_code}")
print(f"  Time: {elapsed:.2f}s")
print(f"  Photos: {data.get('count')}/{data.get('total')}")
print(f"  With images: {sum(1 for p in data.get('photos', []) if p.get('hasImage'))}/24")

print("\n" + "=" * 60)
print("Performance: Parallel resolution (6 workers) vs Sequential")
print("Expected: ~2-4s per 24 photos (vs 30-60s sequentially)")
print("=" * 60)
