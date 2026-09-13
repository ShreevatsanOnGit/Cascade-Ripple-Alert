import osmnx as ox
import networkx as nx
import json
import random
import os

print("Downloading road network for Manipal, Karnataka...")
# Get drivable road network for a 2km radius around Manipal
G = ox.graph_from_point((13.340881, 74.742142), dist=2000, network_type="drive", simplify=True)

# Convert to undirected to simplify our hackathon simulation routing later
G = G.to_undirected()

# Keep only the largest connected component to ensure everything is reachable
G = G.subgraph(max(nx.connected_components(G), key=len)).copy()

print(f"Network downloaded: {len(G.nodes)} nodes, {len(G.edges)} edges.")

nodes_data = []
edges_data = []

node_ids = list(G.nodes())

# 4. Pick 3-5 nodes as "hospital" and 2-3 as "depot"
hospitals = set(random.sample(node_ids, min(4, len(node_ids))))
remaining_nodes = [n for n in node_ids if n not in hospitals]
depots = set(random.sample(remaining_nodes, min(2, len(remaining_nodes))))

# Map OSMnx nodes to our contract
for node_id, data in G.nodes(data=True):
    node_type = "junction"
    if node_id in hospitals:
        node_type = "hospital"
    elif node_id in depots:
        node_type = "depot"
        
    nodes_data.append({
        "id": str(node_id),
        "name": f"Node {node_id}", # OSM nodes rarely have clean names without heavy parsing
        "lat": float(data['y']),
        "lon": float(data['x']),
        "type": node_type,
        "population_weight": random.randint(10, 500) # 6. Assigns population_weight
    })

# Map edges to our contract
edge_id_counter = 1
for u, v, data in G.edges(data=True):
    # 5. Marks edges crossing water/bridges as type "bridge"
    is_bridge = data.get('bridge') == 'yes'
    
    edges_data.append({
        "id": f"edge_{edge_id_counter}",
        "from_node": str(u),
        "to_node": str(v),
        "weight": float(data.get('length', 10.0)),
        "type": "bridge" if is_bridge else "road"
    })
    edge_id_counter += 1

network_json = {
    "nodes": nodes_data,
    "edges": edges_data
}

# 7. Saves to network.json
data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(data_dir, exist_ok=True)
with open(os.path.join(data_dir, "network.json"), "w") as f:
    json.dump(network_json, f, indent=2)

print(f"Saved processed network to data/network.json")
