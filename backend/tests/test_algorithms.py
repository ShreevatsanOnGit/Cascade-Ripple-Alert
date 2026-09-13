from services.algorithms import CascadeSimulator
from dependencies import get_network_data

def test_graph_immutability():
    net_data = get_network_data()
    sim = CascadeSimulator(net_data)
    initial_node_count = sim.G.number_of_nodes()
    
    # Simulate a failure
    failed_id = net_data["nodes"][0]["id"]
    res = sim.simulate_failure([failed_id])
    
    # Check that canonical graph is unchanged
    assert sim.G.number_of_nodes() == initial_node_count
    assert sim.G.has_node(failed_id)

def test_different_failure_scenarios():
    net_data = get_network_data()
    sim = CascadeSimulator(net_data)
    
    res1 = sim.simulate_failure([net_data["nodes"][0]["id"]])
    res2 = sim.simulate_failure([net_data["nodes"][1]["id"]])
    res3 = sim.simulate_failure([net_data["nodes"][2]["id"]])
    
    # Just asserting they run and return expected shape without crashing
    for res in [res1, res2, res3]:
        assert "affected_routes" in res
        assert "stranded_nodes" in res
        assert "impact_score" in res
