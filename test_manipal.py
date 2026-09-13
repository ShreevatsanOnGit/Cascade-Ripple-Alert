import requests
import json

base_url = "http://localhost:8001"

# 1. Get network
net_resp = requests.get(f"{base_url}/network")
net = net_resp.json()
print("Nodes:", len(net['nodes']), "Edges:", len(net['edges']))

# 2. Get criticality
crit_resp = requests.get(f"{base_url}/criticality")
crit = crit_resp.json()

top_nodes = sorted([c for c in crit if c['node_id'].isdigit()], key=lambda x: x['centrality_score'], reverse=True)

# Find specific nodes
hospital_nodes = [n['id'] for n in net['nodes'] if n['type'] == 'hospital']
hospital_node = hospital_nodes[0]

# highly central junction
central_node = top_nodes[0]['node_id']

# lower impact junction
bottom_node = top_nodes[-1]['node_id']

# hospital access route (an edge connected to hospital)
hospital_edges = [e['id'] for e in net['edges'] if e['from_node'] == hospital_node or e['to_node'] == hospital_node]
hosp_edge = hospital_edges[0] if hospital_edges else None

# important road
important_edges = []
for c in crit:
    if c['node_id'].startswith("edge_"):
        important_edges.append(c)
top_edges = sorted(important_edges, key=lambda x: x['centrality_score'], reverse=True)
central_edge = top_edges[0]['node_id'] if top_edges else "edge_1"

scenarios = {
    "1. Highly central junction": central_node,
    "2. Important road": central_edge,
    "3. Hospital access route": hosp_edge,
    "4. Lower-impact ordinary junction": bottom_node
}

for name, obj_id in scenarios.items():
    print(f"\nTesting {name}: {obj_id}")
    resp = requests.post(f"{base_url}/simulate-failure", json={"failed_ids": [obj_id]})
    res = resp.json()
    print(f"Impact Score: {res['impact_score']}")
    print(f"Stranded Nodes: {len(res['stranded_nodes'])}")
    print(f"Affected Routes: {len(res['affected_routes'])}")
    # Find criticality of this obj
    c_score = next((c['centrality_score'] for c in crit if c['node_id'] == obj_id), 0)
    print(f"Criticality: {c_score}")
