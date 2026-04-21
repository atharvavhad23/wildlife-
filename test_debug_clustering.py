#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wildlife_project.settings')
django.setup()

from django.test import Client

c = Client()

print("Testing clustering map page...")
response = c.get('/animals/clustering/')
print(f"Status: {response.status_code}")
print(f"Content type: {response.get('Content-Type')}")
print(f"Content length: {len(response.content)}")

if response.status_code == 200:
    content = response.content.decode('utf-8')
    print(f"\nFirst 1000 chars:\n{content[:1000]}")
else:
    print(f"Error content:\n{response.content}")

print("\n" + "="*70)
print("Testing clustering API...")
response = c.get('/api/animals/clustering/?clusters=8')
print(f"Status: {response.status_code}")
data = response.json()
print(f"Has clusters: {'clusters' in data}")
print(f"Cluster count: {len(data.get('clusters', {}))}")
print(f"First cluster: {list(data.get('clusters', {}).keys())[:1]}")
