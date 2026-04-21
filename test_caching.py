#!/usr/bin/env python
import os
import django
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wildlife_project.settings')
django.setup()

from django.test import Client

c = Client()

print("=" * 70)
print("PERFORMANCE TEST: First Load vs Cached Load")
print("=" * 70)

# First load - will resolve thumbnails and save cache
print("\n1️⃣  FIRST LOAD (parallel thumbnail resolution):")
start = time.time()
r1 = c.get('/photos/animals/?offset=0&limit=12')
t1 = time.time() - start
d1 = r1.json()
print(f"   Time: {t1:.2f}s | Photos: {d1.get('count')}/12 | With images: {sum(1 for p in d1.get('photos', []) if p.get('hasImage'))}/12")

# Second load - should use cache and be instant
print("\n2️⃣  SECOND LOAD (from cache):")
start = time.time()
r2 = c.get('/photos/animals/?offset=0&limit=12')
t2 = time.time() - start
d2 = r2.json()
print(f"   Time: {t2:.3f}s | Photos: {d2.get('count')}/12 | With images: {sum(1 for p in d2.get('photos', []) if p.get('hasImage'))}/12")

# Third load - next batch (should be fast if partially cached)
print("\n3️⃣  NEXT BATCH (offset=12, limit=12):")
start = time.time()
r3 = c.get('/photos/animals/?offset=12&limit=12')
t3 = time.time() - start
d3 = r3.json()
print(f"   Time: {t3:.2f}s | Photos: {d3.get('count')}/12 | With images: {sum(1 for p in d3.get('photos', []) if p.get('hasImage'))}/12")

# Summary
print("\n" + "=" * 70)
print("SUMMARY:")
print(f"  First load:    {t1:.2f}s (parallel resolution + disk save)")
print(f"  Cached load:   {t2:.3f}s (instant from cache)")
print(f"  Next batch:    {t3:.2f}s (mix of cached + new)")
print(f"\n  Speed improvement: {t1/max(t2, 0.001):.0f}x faster on cached loads")
print(f"  Cumulative time for 3 requests: {(t1+t2+t3):.2f}s")
print("=" * 70)

# Verify cache file exists
import pathlib
cache_file = pathlib.Path('thumbnail_cache.pkl')
if cache_file.exists():
    size_mb = cache_file.stat().st_size / (1024*1024)
    print(f"\n✓ Cache file created: {cache_file} ({size_mb:.1f} MB)")
else:
    print(f"\n✗ Cache file not found at {cache_file}")
