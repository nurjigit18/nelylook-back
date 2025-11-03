# test_api.py
import requests

BASE_URL = "http://127.0.0.1:8000"

# Test 1: List all products
print("=" * 50)
print("TEST 1: List all products")
print("=" * 50)
response = requests.get(f"{BASE_URL}/catalog/products/")
print(f"Status: {response.status_code}")
print(f"Response keys: {response.json().keys()}")
print()

# Test 2: Get product by slug
print("=" * 50)
print("TEST 2: Get product by slug")
print("=" * 50)
slug = "plate-vyrez-dekolte"
response = requests.get(f"{BASE_URL}/catalog/products/?slug={slug}")
print(f"Status: {response.status_code}")
data = response.json()
print(f"Response keys: {data.keys()}")

if 'data' in data:
    print(f"Data type: {type(data['data'])}")
    if 'results' in data['data']:
        print(f"Results count: {len(data['data']['results'])}")
        if data['data']['results']:
            product = data['data']['results'][0]
            print(f"Product: {product.get('name', product.get('product_name'))}")
            print(f"Images count: {len(product.get('images', []))}")
            print(f"Colors count: {len(product.get('available_colors', []))}")
            print(f"Sizes count: {len(product.get('available_sizes', []))}")