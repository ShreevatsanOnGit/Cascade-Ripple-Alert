import json
import hashlib
from fastapi.testclient import TestClient
import sys
sys.path.append('.')
from main import app

def hash_dict(d):
    return hashlib.md5(json.dumps(d, sort_keys=True).encode()).hexdigest()

client = TestClient(app)

def check_determinism(endpoint, method="GET", payload=None, iters=10):
    hashes = set()
    for _ in range(iters):
        if method == "GET":
            res = client.get(endpoint)
        else:
            res = client.post(endpoint, json=payload)
        h = hash_dict(res.json())
        hashes.add(h)
    return len(hashes) == 1

print("Determinism /network:", check_determinism("/network"))
print("Determinism /criticality:", check_determinism("/criticality"))
payload = {"failed_ids": ["1466675408"]} # We don't have real network loaded by default, we have dummy
payload = {"failed_ids": ["n4"]} # Use dummy valid node
print("Determinism /simulate-failure:", check_determinism("/simulate-failure", method="POST", payload=payload))
