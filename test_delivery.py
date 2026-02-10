import urllib.request
import json
from datetime import datetime

BASE_URL = "http://localhost:8000/api"

def make_request(url, method="GET", data=None):
    req = urllib.request.Request(url, method=method)
    req.add_header('Content-Type', 'application/json')
    
    if data:
        body = json.dumps(data).encode('utf-8')
        req.data = body

    try:
        with urllib.request.urlopen(req) as response:
            print(f"Status: {response.status}")
            print(f"Body: {response.read().decode('utf-8')}")
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code}")
        print(f"Error Body: {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"Error: {e}")

def test_delivery():
    # 1. Create user
    print("Creating user...")
    make_request(f"{BASE_URL}/users", "POST", {
        "name": "Test",
        "surname": "User",
        "dni": "99999999",
        "contract_type": "Regular Otro sindicato"
    })

    # 2. Create delivery
    print("\nCreating delivery...")
    payload = {
        "dni": "99999999",
        "items": [{"name": "Test Item", "qty": 1}],
        "date": datetime.now().isoformat()
    }
    
    make_request(f"{BASE_URL}/deliveries", "POST", payload)

if __name__ == "__main__":
    test_delivery()
