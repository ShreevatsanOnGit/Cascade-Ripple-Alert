import networkx as nx
import copy

class CascadeSimulator:
    def __init__(self, network_data):
        self.G = nx.Graph()
        self.hospitals = []
        self.depots = []
        self.population_by_node = {}
        
        # Load nodes
        for n in network_data["nodes"]:
            self.G.add_node(n["id"], **n)
            self.population_by_node[n["id"]] = n.get("population_weight", 0)
            if n["type"] == "hospital":
                self.hospitals.append(n["id"])
            elif n["type"] == "depot":
                self.depots.append(n["id"])
                
        # Load edges
        for e in network_data["edges"]:
            self.G.add_edge(e["from_node"], e["to_node"], weight=e["weight"], id=e["id"])
            
        print("Graph built. Precomputing baseline routes and centrality...")
        
        # Precompute Betweenness Centrality
        self.centrality = nx.betweenness_centrality(self.G, weight="weight")
        self.criticality_ranking = [{"node_id": k, "centrality_score": v} for k, v in sorted(self.centrality.items(), key=lambda item: item[1], reverse=True)]
        
        # Precompute baseline paths to nearest hospital/depot
        self.targets = set(self.hospitals + self.depots)
        self.baseline_routes, self.baseline_stranded = self._compute_routes(self.G)
        print("Precomputation complete.")

    def _compute_routes(self, graph):
        # We need shortest paths from every node to the *nearest* critical facility.
        routes = {}
        stranded = []
        
        valid_targets = {t for t in self.targets if t in graph}
        if not valid_targets:
            return {}, list(graph.nodes())

        lengths, paths = nx.multi_source_dijkstra(graph, valid_targets, weight="weight")
        
        for node in graph.nodes():
            if node in paths and node not in valid_targets:
                actual_path = paths[node][::-1]
                routes[node] = {"length": lengths[node], "path": actual_path}
            elif node not in valid_targets:
                stranded.append(node)
                
        return routes, stranded

    def simulate_failure(self, failed_ids):
        G_copy = self.G.copy()
        
        # Remove nodes
        G_copy.remove_nodes_from([n for n in failed_ids if n in G_copy])
        
        # Remove edges if provided
        edges_to_remove = [(u, v) for u, v, d in G_copy.edges(data=True) if d.get("id") in failed_ids]
        G_copy.remove_edges_from(edges_to_remove)
        
        # Recompute
        new_routes, new_stranded = self._compute_routes(G_copy)
        
        affected_routes = []
        length_increase_penalty = 0
        total_pop = sum(self.population_by_node.values())
        
        for node in new_routes:
            if node in self.baseline_routes:
                old_len = self.baseline_routes[node]["length"]
                new_len = new_routes[node]["length"]
                if new_len > old_len * 1.1: # Threshold: 10% worse route
                    affected_routes.append(node)
                    length_increase_penalty += (new_len - old_len) * self.population_by_node.get(node, 0)
        
        # Identify newly stranded nodes
        newly_stranded = list(set(new_stranded) - set(self.baseline_stranded))
        stranded_pop = sum(self.population_by_node.get(n, 0) for n in newly_stranded)
        
        # Impact Score Formula:
        # Weighted combination of population stranded and aggregate delay penalty
        stranded_score = (stranded_pop / max(1, total_pop)) * 100
        delay_score = min(50, length_increase_penalty / max(1, total_pop)) 
        impact_score = stranded_score * 0.7 + delay_score * 0.3
        
        return {
            "affected_routes": affected_routes,
            "stranded_nodes": newly_stranded,
            "impact_score": round(impact_score, 2)
        }
