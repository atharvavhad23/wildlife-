import requests
import json
import time

url = "http://127.0.0.1:8000/predict/animals/"
payload = {
    "year": 2025,
    "temperature": 27.0,
    "rainfall": 8.0,
    "humidity": 70.0,
    "species_richness": 30.0,
    "month": 6,
    "lat_grid": 17.5,
    "lon_grid": 73.5,
    "order_enc": 2,
    "family_enc": 5
}

res1 = requests.post(url, json=payload)
print("2025 Output:")
print(json.dumps(res1.json(), indent=2))

payload["year"] = 2056
res2 = requests.post(url, json=payload)
print("\n2056 Output:")
print(json.dumps(res2.json(), indent=2))
