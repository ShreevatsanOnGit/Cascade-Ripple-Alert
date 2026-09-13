from fastapi.testclient import TestClient
from main import app
import json

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "nodes" in data
    assert "edges" in data

def test_get_network():
    response = client.get("/network")
    assert response.status_code == 200

def test_criticality():
    response = client.get("/criticality")
    assert response.status_code == 200

def test_simulate_failure_success():
    response = client.post("/simulate-failure", json={"failed_ids": ["n4"]})
    assert response.status_code == 200

def test_simulate_failure_multiple():
    response = client.post("/simulate-failure", json={"failed_ids": ["n4", "n5"]})
    assert response.status_code == 200
    data = response.json()
    assert "impact_score" in data

def test_simulate_failure_unknown_node():
    response = client.post("/simulate-failure", json={"failed_ids": ["UNKNOWN_NODE"]})
    assert response.status_code == 400

def test_simulate_failure_unknown_edge():
    response = client.post("/simulate-failure", json={"failed_ids": ["UNKNOWN_EDGE"]})
    assert response.status_code == 400

def test_simulate_failure_malformed():
    response = client.post("/simulate-failure", json={"failed_ids": "not_a_list"})
    assert response.status_code == 422

def test_explain_endpoint():
    req = {"affected_routes": ["n1"], "stranded_nodes": ["n2"], "impact_score": 10.5}
    response = client.post("/explain", json=req)
    assert response.status_code == 200
