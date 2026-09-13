import json
import os

def simplify_graph(input_file="data/manipal_network.json", output_file="data/manipal_network.json"):
    print("Loading network data...")
    with open(input_file, 'r') as f:
        data = json.load(f)
        
    nodes = {n['id']: n for n in data['nodes']}
    edges = data['edges']
    
    # Keep track of adjacency
    # adj[node_id] = {neighbor_id: edge_object}
    # Since we can have multiple edges between the same nodes (multigraph), we must handle them, 
    # but in our simple street graph, it's mostly a simple graph. We'll use a dictionary of lists.
    adj = {nid: {} for nid in nodes.keys()}
    
    for e in edges:
        u = e['from_node']
        v = e['to_node']
        if u not in adj: adj[u] = {}
        if v not in adj: adj[v] = {}
        
        # If there's already an edge between u and v, we keep the shorter one (simplification)
        if v in adj[u]:
            if e['weight'] < adj[u][v]['weight']:
                adj[u][v] = e
                adj[v][u] = e
        else:
            adj[u][v] = e
            adj[v][u] = e

    # Find nodes to remove (degree == 2, type == 'junction')
    removed_count = 0
    
    # We loop until no more nodes can be simplified
    changed = True
    while changed:
        changed = False
        for nid, n in list(nodes.items()):
            if nid not in adj: continue
            
            neighbors = list(adj[nid].keys())
            
            # Condition for simplification: exactly 2 neighbors, and it is just a 'junction'
            if len(neighbors) == 2 and n['type'] == 'junction':
                u = neighbors[0]
                v = neighbors[1]
                
                # If u and v are already connected directly, simplifying this node would create parallel edges.
                # In that case, we can just skip or keep the shorter path.
                # For a clean visual, if they are already connected, we just remove the longer path.
                e1 = adj[u][nid]
                e2 = adj[nid][v]
                
                new_weight = e1['weight'] + e2['weight']
                new_type = e1['type'] if e1['type'] == e2['type'] else 'road'
                
                if v in adj[u]:
                    # They are already connected. We just remove the u-nid-v path entirely if we want to simplify,
                    # or keep it if it's shorter. Usually, parallel edges in OSM are dual carriageways.
                    # We'll just remove the u-nid-v path.
                    del adj[u][nid]
                    del adj[nid][u]
                    del adj[v][nid]
                    del adj[nid][v]
                    del nodes[nid]
                    del adj[nid]
                else:
                    # Create new edge
                    new_edge = {
                        "id": f"{e1['id']}_{e2['id']}_merged",
                        "from_node": u,
                        "to_node": v,
                        "weight": new_weight,
                        "type": new_type
                    }
                    
                    # Remove old edges
                    del adj[u][nid]
                    del adj[nid][u]
                    del adj[v][nid]
                    del adj[nid][v]
                    
                    # Add new edge
                    adj[u][v] = new_edge
                    adj[v][u] = new_edge
                    
                    # Delete the node
                    del nodes[nid]
                    del adj[nid]
                    
                removed_count += 1
                changed = True
                break # Restart loop because graph mutated

    # Reconstruct edges list
    new_edges_set = set()
    new_edges = []
    
    # To assign clean IDs again
    edge_counter = 1
    for u in adj:
        for v in adj[u]:
            e = adj[u][v]
            # Ensure we don't add the same undirected edge twice
            sorted_uv = tuple(sorted([u, v]))
            if sorted_uv not in new_edges_set:
                new_edges_set.add(sorted_uv)
                e['id'] = f"edge_{edge_counter}"
                e['from_node'] = u
                e['to_node'] = v
                new_edges.append(e)
                edge_counter += 1

    new_nodes = list(nodes.values())
    
    print(f"Removed {removed_count} intermediate nodes.")
    print(f"Final Nodes: {len(new_nodes)}, Final Edges: {len(new_edges)}")
    
    with open(output_file, 'w') as f:
        json.dump({"nodes": new_nodes, "edges": new_edges}, f, indent=2)

if __name__ == "__main__":
    simplify_graph()
