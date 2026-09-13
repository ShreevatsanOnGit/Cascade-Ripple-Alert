import os
import json
import networkx as nx
import osmnx as ox
import random

# Use MIT Manipal location
center_point = (13.352, 74.792)
dist = 1200 # 1.2km radius covers MIT, Kamath Circle, KMC Hospital
ox.settings.timeout = 60 # 60 second timeout
ox.settings.overpass_endpoint = "https://overpass.kumi.systems/api/interpreter"

print(f"Downloading network around {center_point} with radius {dist}m...", flush=True)
G = ox.graph_from_point(center_point, dist=dist, network_type='drive')
G = ox.utils_graph.get_undirected(G)

nodes_data = []
edges_data = []

# Convert nodes
hospitals_found = 0
depots_found = 0

for node_id, data in G.nodes(data=True):
    lat = data.get('y')
    lon = data.get('x')
    
    # Heuristic for types and weights
    # In a real OSM query we might fetch POIs. For now, let's use rough coordinates.
    # KMC Hospital is roughly 13.353, 74.785. Let's find the nearest node to that.
    node_type = "junction"
    pop_weight = 10
    
    nodes_data.append({
        "id": str(node_id),
        "name": f"Node {node_id}",
        "lat": lat,
        "lon": lon,
        "type": node_type,
        "population_weight": pop_weight
    })

# Fetch POIs to enrich nodes
print("Fetching hospitals...", flush=True)
tags_hospital = {'amenity': 'hospital'}
try:
    pois_hospital = ox.features_from_point(center_point, tags=tags_hospital, dist=dist)
except Exception as e:
    pois_hospital = None
    
print("Fetching depots...", flush=True)
tags_depot = {'amenity': ['bus_station', 'fuel'], 'building': ['warehouse', 'industrial']}
try:
    pois_depot = ox.features_from_point(center_point, tags=tags_depot, dist=dist)
except Exception as e:
    pois_depot = None

def get_nearest_node(lat, lon):
    return str(ox.distance.nearest_nodes(G, lon, lat))

if pois_hospital is not None and not pois_hospital.empty:
    for idx, row in pois_hospital.iterrows():
        if hasattr(row.geometry, 'centroid'):
            lat, lon = row.geometry.centroid.y, row.geometry.centroid.x
        else:
            lat, lon = row.geometry.y, row.geometry.x
        nid = get_nearest_node(lat, lon)
        name = row.get('name', 'Hospital')
        # Update node
        for n in nodes_data:
            if n['id'] == nid:
                n['type'] = 'hospital'
                n['name'] = str(name) if name else 'Hospital'
                n['population_weight'] = 500
                hospitals_found += 1
                
if pois_depot is not None and not pois_depot.empty:
    for idx, row in pois_depot.iterrows():
        if hasattr(row.geometry, 'centroid'):
            lat, lon = row.geometry.centroid.y, row.geometry.centroid.x
        else:
            lat, lon = row.geometry.y, row.geometry.x
        nid = get_nearest_node(lat, lon)
        name = row.get('name', 'Depot/Facility')
        for n in nodes_data:
            if n['id'] == nid and n['type'] != 'hospital':
                n['type'] = 'depot'
                n['name'] = str(name) if name else 'Facility'
                n['population_weight'] = 200
                depots_found += 1

# Fallback if no hospital or depot found
if hospitals_found == 0:
    nodes_data[0]['type'] = 'hospital'
    nodes_data[0]['name'] = 'KMC Hospital (Fallback)'
    nodes_data[0]['population_weight'] = 500

if depots_found == 0:
    nodes_data[1]['type'] = 'depot'
    nodes_data[1]['name'] = 'MIT Depot (Fallback)'
    nodes_data[1]['population_weight'] = 200

# Increase weight of some central nodes to represent hostels/academic blocks
for n in nodes_data:
    if n['type'] == 'junction':
        # Arbitrary variation for simulation realism based on ID to be deterministic
        n['population_weight'] = 10 + (int(n['id']) % 40)

# Convert edges
edge_id_counter = 1
for u, v, data in G.edges(data=True):
    is_bridge = data.get('bridge') == 'yes'
    weight = data.get('length', 10.0)
    
    edges_data.append({
        "id": f"edge_{edge_id_counter}",
        "from_node": str(u),
        "to_node": str(v),
        "weight": weight,
        "type": "bridge" if is_bridge else "road"
    })
    edge_id_counter += 1

network_json = {
    "nodes": nodes_data,
    "edges": edges_data
}

os.makedirs('data', exist_ok=True)
with open('data/manipal_network.json', 'w') as f:
    json.dump(network_json, f, indent=2)

print(f"Saved {len(nodes_data)} nodes and {len(edges_data)} edges to data/manipal_network.json")
