import json
import os
import logging
from schemas import NetworkResponse

logger = logging.getLogger(__name__)

def validate_semantics(data: dict) -> dict:
    # 1. Pydantic validation (Types, basic constraints)
    validated = NetworkResponse(**data)
    nodes = validated.nodes
    edges = validated.edges
    
    # 2. Unique node IDs and node validation
    node_ids = set()
    for n in nodes:
        if n.id in node_ids:
            raise ValueError(f"Duplicate node ID found: {n.id}")
        node_ids.add(n.id)
        
        # Coordinates
        if not (-90 <= n.lat <= 90):
            raise ValueError(f"Invalid latitude {n.lat} for node {n.id}")
        if not (-180 <= n.lon <= 180):
            raise ValueError(f"Invalid longitude {n.lon} for node {n.id}")
            
        # Population
        if n.population_weight < 0:
            raise ValueError(f"Negative population_weight for node {n.id}")
            
    # 3. Unique edge IDs and edge validation
    edge_ids = set()
    for e in edges:
        if e.id in edge_ids:
            raise ValueError(f"Duplicate edge ID found: {e.id}")
        edge_ids.add(e.id)
        
        if e.from_node not in node_ids:
            raise ValueError(f"Edge {e.id} references unknown from_node: {e.from_node}")
        if e.to_node not in node_ids:
            raise ValueError(f"Edge {e.id} references unknown to_node: {e.to_node}")
            
        if e.from_node == e.to_node:
            logger.warning(f"Validation Warning: Self-loop edge found: {e.id}. Ignoring mathematically, but flagged for data review.")
            
        if e.weight < 0:
            raise ValueError(f"Negative weight {e.weight} on edge {e.id}")
            
    # 4. Mandatory assets
    hospitals = sum(1 for n in nodes if n.type == "hospital")
    depots = sum(1 for n in nodes if n.type == "depot")
    
    if hospitals == 0:
        raise ValueError("Network must contain at least one hospital asset.")
    if depots == 0:
        raise ValueError("Network must contain at least one depot asset.")
        
    return validated.model_dump()

def load_network_data(filepath: str) -> dict:
    logger.info(f"Loading network data from {filepath}...")
    if not os.path.exists(filepath):
        logger.error(f"Network file not found: {filepath}")
        raise FileNotFoundError(f"Network file not found at {filepath}")
    
    with open(filepath, "r") as f:
        data = json.load(f)
        
    try:
        validated_data = validate_semantics(data)
        logger.info(f"Successfully loaded and validated {len(validated_data['nodes'])} nodes and {len(validated_data['edges'])} edges.")
        return validated_data
    except Exception as e:
        logger.error(f"Network validation failed: {str(e)}")
        raise e
