from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    print("\n=== Testing /health ===")
    print(f"Status: {response.status_code}")
    print(response.json())

def test_dashboard():
    response = client.get("/dashboard/resumen")
    print("\n=== Testing /dashboard/resumen ===")
    print(f"Status: {response.status_code}")
    print(response.json())

if __name__ == "__main__":
    test_health()
    test_dashboard()