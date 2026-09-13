import requests
import json
import os
import math

# Bounding box for MIT Manipal (approx 1.2km)
# Center: 13.352, 74.792
# offset 0.01 deg is approx 1km
S, N = 13.346, 13.358
W, E = 74.781, 74.796

query = f"""
[out:json][timeout:25];
(
  way["highway"]({S},{W},{N},{E});
);
out body;
>;
out skel qt;
"""

print("Fetching OSM data...", flush=True)
url = "https://overpass-api.de/api/interpreter"
# Use French OSM mirror which is very reliable if DE is down, or just DE with a user agent
url = "https://overpass.openstreetmap.fr/api/interpreter"

response = requests.post(url, data={'data': query}, headers={'User-Agent': 'CascadeMap'})
if response.status_code != 200:
    print("Failed to fetch:", response.status_code, response.text)
    exit(1)

data = response.json()
print("Downloaded OSM data.", flush=True)

nodes = {}
ways = []

for elem in data['elements']:
    if elem['type'] == 'node':
        nodes[elem['id']] = {'lat': elem['lat'], 'lon': elem['lon']}
    elif elem['type'] == 'way':
        ways.append(elem)

# Build graph manually
nodes_data = []
edges_data = []
edge_id_counter = 1

included_nodes = set()

# First pass: find which nodes are actually part of roads
for way in ways:
    tags = way.get('tags', {})
    highway = tags.get('highway')
    if highway not in ['residential', 'unclassified', 'tertiary', 'secondary', 'primary', 'service']:
        continue # skip minor paths
        
    is_bridge = tags.get('bridge') == 'yes'
    
    nds = way.get('nodes', [])
    for i in range(len(nds)-1):
        u = nds[i]
        v = nds[i+1]
        
        if u not in nodes or v not in nodes: continue
        
        included_nodes.add(u)
        included_nodes.add(v)
        
        # Calculate euclidean distance for weight (very rough, approx meters)
        dy = (nodes[u]['lat'] - nodes[v]['lat']) * 111320
        dx = (nodes[u]['lon'] - nodes[v]['lon']) * 111320 * math.cos(math.radians(nodes[u]['lat']))
        dist = math.sqrt(dx*dx + dy*dy)
        
        edges_data.append({
            "id": f"edge_{edge_id_counter}",
            "from_node": str(u),
            "to_node": str(v),
            "weight": max(1.0, round(dist, 2)),
            "type": "bridge" if is_bridge else "road"
        })
        edge_id_counter += 1

# KMC roughly at 13.353, 74.785
# MIT roughly at 13.352, 74.792
kmc_dist = lambda n: (n['lat']-13.353)**2 + (n['lon']-74.785)**2
mit_dist = lambda n: (n['lat']-13.352)**2 + (n['lon']-74.792)**2

closest_to_kmc = None
min_kmc = float('inf')

closest_to_mit = None
min_mit = float('inf')

for nid in included_nodes:
    nd = nodes[nid]
    dk = kmc_dist(nd)
    if dk < min_kmc:
        min_kmc = dk
        closest_to_kmc = nid
        
    dm = mit_dist(nd)
    if dm < min_mit:
        min_mit = dm
        closest_to_mit = nid

for nid in included_nodes:
    nd = nodes[nid]
    node_type = "junction"
    name = f"Node_{nid}"
    pop = 10 + (nid % 40)
    
    if nid == closest_to_kmc:
        node_type = "hospital"
        name = "KMC Hospital"
        pop = 500
    elif nid == closest_to_mit:
        node_type = "depot"
        name = "MIT Depot (FC)"
        pop = 300
        
    nodes_data.append({
        "id": str(nid),
        "name": name,
        "lat": nd['lat'],
        "lon": nd['lon'],
        "type": node_type,
        "population_weight": pop
    })

network_json = {
    "nodes": nodes_data,
    "edges": edges_data
}

os.makedirs('data', exist_ok=True)
with open('data/manipal_network.json', 'w') as f:
    json.dump(network_json, f, indent=2)

print(f"Saved {len(nodes_data)} nodes and {len(edges_data)} edges.")
