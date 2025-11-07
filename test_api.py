import requests
import json
from datetime import date, timedelta

BASE_URL = "http://localhost:8000"

def test_endpoints():
    # Test health
    print("\n=== Testing /health ===")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))

    # Test dashboard/resumen
    print("\n=== Testing /dashboard/resumen ===")
    response = requests.get(f"{BASE_URL}/dashboard/resumen")
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))

    # Test margen-bruto with date filters
    print("\n=== Testing /kpi/margen-bruto with dates ===")
    today = date.today()
    start_date = today - timedelta(days=30)
    params = {
        'fecha_inicio': start_date.isoformat(),
        'fecha_fin': today.isoformat()
    }
    response = requests.get(f"{BASE_URL}/kpi/margen-bruto", params=params)
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))

    # Test top-destinos
    print("\n=== Testing /analytics/top-destinos ===")
    response = requests.get(f"{BASE_URL}/analytics/top-destinos", params={'limit': 3})
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))

if __name__ == "__main__":
    test_endpoints()