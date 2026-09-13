import pytest
from pydantic import ValidationError
from services.data_loader import validate_semantics
import copy

BASE_DATA = {
  "nodes": [
    { "id": "n1", "name": "Hub", "lat": 40.71, "lon": -74.00, "type": "hospital", "population_weight": 500 },
    { "id": "n2", "name": "Dep", "lat": 40.72, "lon": -74.00, "type": "depot", "population_weight": 200 }
  ],
  "edges": [
    { "id": "e1", "from_node": "n1", "to_node": "n2", "weight": 2.0, "type": "road" }
  ]
}

def test_valid_network():
    assert validate_semantics(BASE_DATA) is not None

def test_duplicate_node_ids():
    data = copy.deepcopy(BASE_DATA)
    data["nodes"].append(data["nodes"][0])
    with pytest.raises(ValueError, match="Duplicate node ID"):
        validate_semantics(data)

def test_duplicate_edge_ids():
    data = copy.deepcopy(BASE_DATA)
    data["edges"].append(data["edges"][0])
    with pytest.raises(ValueError, match="Duplicate edge ID"):
        validate_semantics(data)

def test_invalid_edge_reference():
    data = copy.deepcopy(BASE_DATA)
    data["edges"][0]["to_node"] = "ghost_node"
    with pytest.raises(ValueError, match="references unknown to_node"):
        validate_semantics(data)

def test_self_loop():
    data = copy.deepcopy(BASE_DATA)
    data["edges"][0]["to_node"] = "n1"
    # Self loops log a warning but don't crash
    result = validate_semantics(data)
    assert result is not None

def test_negative_weight():
    data = copy.deepcopy(BASE_DATA)
    data["edges"][0]["weight"] = -1.0
    with pytest.raises(ValueError, match="Negative weight"):
        validate_semantics(data)

def test_invalid_node_type():
    data = copy.deepcopy(BASE_DATA)
    data["nodes"][0]["type"] = "alien_base"
    with pytest.raises(ValidationError): # Caught by pydantic
        validate_semantics(data)

def test_invalid_coordinates():
    data = copy.deepcopy(BASE_DATA)
    data["nodes"][0]["lat"] = 91.0
    with pytest.raises(ValueError, match="Invalid latitude"):
        validate_semantics(data)

def test_missing_hospital():
    data = copy.deepcopy(BASE_DATA)
    data["nodes"][0]["type"] = "junction"
    with pytest.raises(ValueError, match="at least one hospital"):
        validate_semantics(data)

def test_missing_depot():
    data = copy.deepcopy(BASE_DATA)
    data["nodes"][1]["type"] = "junction"
    with pytest.raises(ValueError, match="at least one depot"):
        validate_semantics(data)
