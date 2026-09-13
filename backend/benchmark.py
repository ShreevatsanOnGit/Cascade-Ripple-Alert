import time
import json
import statistics
import networkx as nx
import sys
sys.path.append('.')
from services.data_loader import validate_semantics
from services.algorithms import CascadeSimulator

def measure(fn, *args, iters=5):
    times = []
    for _ in range(iters):
        start = time.perf_counter()
        res = fn(*args)
        times.append(time.perf_counter() - start)
    return min(times), statistics.mean(times), max(times), res

with open('../data/network.json') as f:
    raw_data = json.load(f)

# 1. Loading time
t_min, t_mean, t_max, net_data = measure(validate_semantics, raw_data, iters=10)
print(f'Network Loading: min={t_min*1000:.2f}ms, avg={t_mean*1000:.2f}ms, max={t_max*1000:.2f}ms')

# 2. Simulator Init Time
t_min, t_mean, t_max, sim = measure(CascadeSimulator, net_data, iters=3)
print(f'CascadeSimulator Init: min={t_min*1000:.2f}ms, avg={t_mean*1000:.2f}ms, max={t_max*1000:.2f}ms')

# Find target nodes
junction_id = [n['id'] for n in net_data['nodes'] if n['type'] == 'junction'][0]
bridge_edge = [e for e in net_data['edges'] if e['type'] == 'bridge'][0]
central_node = sim.criticality_ranking[0]['node_id']

# 3. Simulate Failure
t_min, t_mean, t_max, _ = measure(sim.simulate_failure, [junction_id], iters=10)
print(f'Simulate Failure (Junction {junction_id}): min={t_min*1000:.2f}ms, avg={t_mean*1000:.2f}ms, max={t_max*1000:.2f}ms')

b_id = bridge_edge['id']
t_min, t_mean, t_max, _ = measure(sim.simulate_failure, [b_id], iters=10)
print(f'Simulate Failure (Bridge Edge {b_id}): min={t_min*1000:.2f}ms, avg={t_mean*1000:.2f}ms, max={t_max*1000:.2f}ms')

t_min, t_mean, t_max, _ = measure(sim.simulate_failure, [central_node], iters=10)
print(f'Simulate Failure (Central Node {central_node}): min={t_min*1000:.2f}ms, avg={t_mean*1000:.2f}ms, max={t_max*1000:.2f}ms')

# 4. Criticality complete computation
def compute_centrality(G):
    return nx.betweenness_centrality(G, weight='weight')
t_min, t_mean, t_max, _ = measure(compute_centrality, sim.G, iters=3)
print(f'Criticality (Betweenness): min={t_min*1000:.2f}ms, avg={t_mean*1000:.2f}ms, max={t_max*1000:.2f}ms')
