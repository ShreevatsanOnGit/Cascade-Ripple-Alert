import json
import os

from services.algorithms import CascadeSimulator
from services.cascade import CascadeEngine, MAX_CASCADE_STEPS


# Tiny legal network: hospital + depot required by Phase-1 construction.
FIXTURE = {
    "nodes": [
        {"id": "n1", "name": "Hospital", "lat": 40.71, "lon": -74.00, "type": "hospital", "population_weight": 100},
        {"id": "n2", "name": "Depot", "lat": 40.72, "lon": -74.00, "type": "depot", "population_weight": 50},
        {"id": "n3", "name": "Junction", "lat": 40.73, "lon": -74.01, "type": "junction", "population_weight": 20},
        {"id": "n4", "name": "Far", "lat": 40.74, "lon": -74.02, "type": "junction", "population_weight": 10},
    ],
    "edges": [
        {"id": "e1", "from_node": "n1", "to_node": "n2", "weight": 1.0, "type": "road"},
        {"id": "e2", "from_node": "n2", "to_node": "n3", "weight": 1.0, "type": "road"},
        {"id": "e3", "from_node": "n3", "to_node": "n4", "weight": 1.0, "type": "road"},
    ],
}


def _simulator():
    return CascadeSimulator(FIXTURE)


def _engine(max_steps=MAX_CASCADE_STEPS):
    return CascadeEngine(_simulator(), max_steps=max_steps)


class ScriptedCandidates(CascadeEngine):
    """Test hook: return a fixed sequence of candidate batches, then none."""

    def __init__(self, simulator, batches, max_steps=MAX_CASCADE_STEPS):
        super().__init__(simulator, max_steps=max_steps)
        self._batches = [list(batch) for batch in batches]
        self._index = 0

    def _find_candidate_failures(self, G_work, failed_set, previous_corridors=None):
        if self._index >= len(self._batches):
            return []
        batch = self._batches[self._index]
        self._index += 1
        return batch


class AlwaysOneRemainingNode(CascadeEngine):
    """Keeps proposing one unfailed node so the depth cap can fire."""

    def _find_candidate_failures(self, G_work, failed_set, previous_corridors=None):
        for node_id in sorted(G_work.nodes(), key=str):
            if node_id not in failed_set:
                return [node_id]
        return []


def test_initial_failure_is_recorded():
    result = _engine().simulate_cascade(["n4"])
    assert result["steps"][0]["step"] == 1
    assert result["steps"][0]["newly_failed"] == ["n4"]
    assert result["events"][0]["asset_id"] == "n4"
    assert result["events"][0]["asset_type"] == "node"


def test_initial_event_reason_and_trigger():
    result = _engine().simulate_cascade(["n4"])
    event = result["events"][0]
    assert event["reason"] == "initial_failure"
    assert event["triggered_by"] == []
    assert event["step"] == 1


def test_initial_failure_not_duplicated():
    result = _engine().simulate_cascade(["n4", "n4"])
    failed_ids = [e["asset_id"] for e in result["events"]]
    assert failed_ids.count("n4") == 1
    assert result["steps"][0]["newly_failed"] == ["n4"]


def test_no_candidates_stops_stabilized():
    result = _engine().simulate_cascade(["n4"])
    assert result["stopped_reason"] == "stabilized"
    assert len(result["steps"]) == 1
    assert all(e["reason"] == "initial_failure" for e in result["events"])


def test_cascade_depth_is_correct():
    empty = _engine().simulate_cascade(["n3"])
    assert empty["cascade_depth"] == 1

    sim = _simulator()
    # e2 still exists after n4 is removed; e3 would be deleted with n4.
    scripted = ScriptedCandidates(sim, batches=[["e2"]])
    result = scripted.simulate_cascade(["n4"])
    assert result["cascade_depth"] == 2
    assert result["steps"][1]["newly_failed"] == ["e2"]
    assert result["events"][1]["reason"] == "last_remaining_corridor"
    assert result["events"][1]["triggered_by"] == ["n4"]


def test_maximum_depth_terminates_safely():
    sim = _simulator()
    engine = AlwaysOneRemainingNode(sim, max_steps=2)
    result = engine.simulate_cascade(["n4"])
    assert result["cascade_depth"] == 2
    assert result["stopped_reason"] == "max_depth"
    assert sim.G.number_of_nodes() == 4


def test_event_ordering_is_deterministic():
    result = _engine().simulate_cascade(["n4", "e2"])
    events = result["events"]
    assert [e["asset_id"] for e in events] == ["e2", "n4"]
    assert events[0]["asset_type"] == "edge"
    assert events[1]["asset_type"] == "node"


def test_repeated_simulations_are_identical():
    engine = _engine()
    first = engine.simulate_cascade(["e2", "n4"])
    second = engine.simulate_cascade(["e2", "n4"])
    assert first == second


def test_original_graph_unchanged():
    sim = _simulator()
    nodes_before = sim.G.number_of_nodes()
    edges_before = sim.G.number_of_edges()
    node_ids = set(sim.G.nodes())
    CascadeEngine(sim).simulate_cascade(["n4", "e2"])
    assert sim.G.number_of_nodes() == nodes_before
    assert sim.G.number_of_edges() == edges_before
    assert set(sim.G.nodes()) == node_ids
    assert sim.G.has_node("n4")


def test_independent_simulations_do_not_affect_each_other():
    sim = _simulator()
    engine = CascadeEngine(sim)
    a = engine.simulate_cascade(["n4"])
    b = engine.simulate_cascade(["e1"])
    a_again = engine.simulate_cascade(["n4"])
    assert a == a_again
    assert a != b
    assert sim.G.has_node("n4")
    assert any(d.get("id") == "e1" for _, _, d in sim.G.edges(data=True))


def test_invalid_ids_are_rejected():
    engine = _engine()
    try:
        engine.simulate_cascade(["UNKNOWN_NODE"])
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "Unknown ID: UNKNOWN_NODE" in str(exc)

    try:
        engine.simulate_cascade("n4")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "list" in str(exc).lower()


def test_node_failure_works():
    result = _engine().simulate_cascade(["n4"])
    phase1 = _simulator().simulate_failure(["n4"])
    assert result["affected_routes"] == sorted(phase1["affected_routes"], key=str)
    assert result["stranded_nodes"] == sorted(phase1["stranded_nodes"], key=str)
    assert result["impact_score"] == phase1["impact_score"]
    assert result["events"][0]["asset_type"] == "node"


def test_edge_failure_works():
    result = _engine().simulate_cascade(["e3"])
    phase1 = _simulator().simulate_failure(["e3"])
    assert result["affected_routes"] == sorted(phase1["affected_routes"], key=str)
    assert result["stranded_nodes"] == sorted(phase1["stranded_nodes"], key=str)
    assert result["impact_score"] == phase1["impact_score"]
    assert result["events"][0]["asset_type"] == "edge"
    assert result["events"][0]["asset_id"] == "e3"


def test_scripted_candidates_applied_together_and_deduped():
    sim = _simulator()
    engine = ScriptedCandidates(sim, batches=[["e3", "e3"]])
    result = engine.simulate_cascade(["e2"])
    assert result["cascade_depth"] == 2
    assert result["steps"][1]["newly_failed"] == ["e3"]
    assert [e["asset_id"] for e in result["events"] if e["step"] == 2] == ["e3"]
    assert result["stopped_reason"] == "stabilized"


def _engine_from(network):
    return CascadeEngine(CascadeSimulator(network))


# K4 around the hospital: removing one spoke leaves two other paths.
K4 = {
    "nodes": [
        {"id": "h", "name": "Hospital", "lat": 40.71, "lon": -74.00, "type": "hospital", "population_weight": 100},
        {"id": "d", "name": "Depot", "lat": 40.70, "lon": -74.00, "type": "depot", "population_weight": 40},
        {"id": "a", "name": "A", "lat": 40.72, "lon": -74.01, "type": "junction", "population_weight": 10},
        {"id": "b", "name": "B", "lat": 40.72, "lon": -74.02, "type": "junction", "population_weight": 10},
        {"id": "c", "name": "C", "lat": 40.73, "lon": -74.01, "type": "junction", "population_weight": 10},
    ],
    "edges": [
        {"id": "ha", "from_node": "h", "to_node": "a", "weight": 1.0, "type": "road"},
        {"id": "hb", "from_node": "h", "to_node": "b", "weight": 1.0, "type": "road"},
        {"id": "hc", "from_node": "h", "to_node": "c", "weight": 1.0, "type": "road"},
        {"id": "ab", "from_node": "a", "to_node": "b", "weight": 1.0, "type": "road"},
        {"id": "ac", "from_node": "a", "to_node": "c", "weight": 1.0, "type": "road"},
        {"id": "bc", "from_node": "b", "to_node": "c", "weight": 1.0, "type": "road"},
        {"id": "hd", "from_node": "h", "to_node": "d", "weight": 1.0, "type": "road"},
    ],
}

# X has two ways to H (via P and via Q). Cutting H-P makes P-X the new last corridor.
TWO_PATH = {
    "nodes": [
        {"id": "h", "name": "Hospital", "lat": 40.71, "lon": -74.00, "type": "hospital", "population_weight": 100},
        {"id": "d", "name": "Depot", "lat": 40.70, "lon": -74.00, "type": "depot", "population_weight": 40},
        {"id": "p", "name": "P", "lat": 40.72, "lon": -74.00, "type": "junction", "population_weight": 10},
        {"id": "q", "name": "Q", "lat": 40.71, "lon": -74.02, "type": "junction", "population_weight": 10},
        {"id": "x", "name": "X", "lat": 40.72, "lon": -74.02, "type": "junction", "population_weight": 10},
    ],
    "edges": [
        {"id": "hd", "from_node": "h", "to_node": "d", "weight": 1.0, "type": "road"},
        {"id": "hp", "from_node": "h", "to_node": "p", "weight": 1.0, "type": "road"},
        {"id": "px", "from_node": "p", "to_node": "x", "weight": 1.0, "type": "road"},
        {"id": "xh", "from_node": "x", "to_node": "h", "weight": 1.0, "type": "road"},
        {"id": "xq", "from_node": "x", "to_node": "q", "weight": 1.0, "type": "road"},
        {"id": "qh", "from_node": "q", "to_node": "h", "weight": 1.0, "type": "road"},
    ],
}

# Square H-A-B-C. Failing H-A creates three new facility corridors at once.
SQUARE = {
    "nodes": [
        {"id": "h", "name": "Hospital", "lat": 40.71, "lon": -74.00, "type": "hospital", "population_weight": 100},
        {"id": "d", "name": "Depot", "lat": 40.70, "lon": -74.00, "type": "depot", "population_weight": 40},
        {"id": "a", "name": "A", "lat": 40.72, "lon": -74.00, "type": "junction", "population_weight": 10},
        {"id": "b", "name": "B", "lat": 40.72, "lon": -74.01, "type": "junction", "population_weight": 10},
        {"id": "c", "name": "C", "lat": 40.71, "lon": -74.01, "type": "junction", "population_weight": 10},
    ],
    "edges": [
        {"id": "e1", "from_node": "h", "to_node": "a", "weight": 1.0, "type": "road"},
        {"id": "e2", "from_node": "a", "to_node": "b", "weight": 1.0, "type": "road"},
        {"id": "e3", "from_node": "b", "to_node": "c", "weight": 1.0, "type": "road"},
        {"id": "e4", "from_node": "c", "to_node": "h", "weight": 1.0, "type": "road"},
        {"id": "ed", "from_node": "d", "to_node": "h", "weight": 1.0, "type": "road"},
    ],
}

# A reaches H directly and via B. Failing node B makes HA the new last corridor.
VIA_NODE = {
    "nodes": [
        {"id": "h", "name": "Hospital", "lat": 40.71, "lon": -74.00, "type": "hospital", "population_weight": 100},
        {"id": "d", "name": "Depot", "lat": 40.70, "lon": -74.00, "type": "depot", "population_weight": 40},
        {"id": "a", "name": "A", "lat": 40.72, "lon": -74.00, "type": "junction", "population_weight": 10},
        {"id": "b", "name": "B", "lat": 40.72, "lon": -74.01, "type": "junction", "population_weight": 10},
    ],
    "edges": [
        {"id": "hd", "from_node": "h", "to_node": "d", "weight": 1.0, "type": "road"},
        {"id": "ha", "from_node": "h", "to_node": "a", "weight": 1.0, "type": "road"},
        {"id": "ab", "from_node": "a", "to_node": "b", "weight": 1.0, "type": "road"},
        {"id": "bh", "from_node": "b", "to_node": "h", "weight": 1.0, "type": "road"},
    ],
}


def test_no_secondary_when_alternate_paths_remain():
    result = _engine_from(K4).simulate_cascade(["ha"])
    assert result["cascade_depth"] == 1
    assert result["stopped_reason"] == "stabilized"
    assert all(e["reason"] == "initial_failure" for e in result["events"])


def test_one_new_last_remaining_corridor():
    result = _engine_from(TWO_PATH).simulate_cascade(["hp"])
    assert result["cascade_depth"] == 2
    assert result["steps"][1]["newly_failed"] == ["px"]
    corridor = [e for e in result["events"] if e["step"] == 2]
    assert len(corridor) == 1
    assert corridor[0]["asset_id"] == "px"
    assert corridor[0]["asset_type"] == "edge"
    assert corridor[0]["reason"] == "last_remaining_corridor"
    assert corridor[0]["triggered_by"] == ["hp"]
    assert result["stopped_reason"] == "stabilized"


def test_new_corridors_in_one_round_are_applied_together():
    result = _engine_from(SQUARE).simulate_cascade(["e1"])
    assert result["steps"][1]["newly_failed"] == ["e2", "e3", "e4"]
    assert result["cascade_depth"] == 2
    assert all(e["triggered_by"] == ["e1"] for e in result["events"] if e["step"] == 2)


def test_preexisting_corridor_is_not_forced():
    result = _engine().simulate_cascade(["e3"])
    assert result["cascade_depth"] == 1
    assert result["stopped_reason"] == "stabilized"


def test_does_not_fail_stranded_nodes():
    result = _engine_from(TWO_PATH).simulate_cascade(["hp"])
    failed_nodes = [e["asset_id"] for e in result["events"] if e["asset_type"] == "node"]
    assert failed_nodes == []
    assert "p" not in result["steps"][1]["newly_failed"]
    assert "x" not in result["steps"][1]["newly_failed"]


def test_node_failure_can_create_a_corridor():
    result = _engine_from(VIA_NODE).simulate_cascade(["b"])
    assert result["steps"][0]["newly_failed"] == ["b"]
    assert result["steps"][1]["newly_failed"] == ["ha"]
    assert result["events"][1]["reason"] == "last_remaining_corridor"
    assert result["events"][1]["triggered_by"] == ["b"]


def test_real_rule_is_deterministic_and_immutable():
    sim = CascadeSimulator(TWO_PATH)
    engine = CascadeEngine(sim)
    first = engine.simulate_cascade(["hp"])
    second = engine.simulate_cascade(["hp"])
    assert first == second
    assert sim.G.has_node("p")
    assert any(d.get("id") == "hp" for _, _, d in sim.G.edges(data=True))


def test_unknown_edge_id_is_rejected():
    try:
        _engine().simulate_cascade(["UNKNOWN_EDGE"])
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "Unknown ID: UNKNOWN_EDGE" in str(exc)


def test_empty_failed_ids_stabilizes_without_events():
    result = _engine_from(K4).simulate_cascade([])
    assert result["cascade_depth"] == 1
    assert result["stopped_reason"] == "stabilized"
    assert result["events"] == []
    assert result["steps"][0]["newly_failed"] == []
    assert result["impact_score"] == 0


def test_step1_matches_phase1_before_secondary():
    sim = CascadeSimulator(TWO_PATH)
    phase1 = sim.simulate_failure(["hp"])
    result = CascadeEngine(sim).simulate_cascade(["hp"])
    assert result["steps"][0]["affected_routes"] == sorted(phase1["affected_routes"], key=str)
    assert result["steps"][0]["newly_stranded"] == sorted(phase1["stranded_nodes"], key=str)
    assert result["steps"][0]["impact_score"] == phase1["impact_score"]
    assert result["cascade_depth"] == 2


def test_final_metrics_match_last_step_and_full_failed_set():
    result = _engine_from(TWO_PATH).simulate_cascade(["hp"])
    last = result["steps"][-1]
    assert result["affected_routes"] == last["affected_routes"]
    assert result["impact_score"] == last["impact_score"]
    phase1_final = CascadeSimulator(TWO_PATH).simulate_failure(["hp", "px"])
    assert result["stranded_nodes"] == sorted(phase1_final["stranded_nodes"], key=str)
    assert result["impact_score"] == phase1_final["impact_score"]


def test_no_duplicate_failures_across_real_cascade():
    result = _engine_from(SQUARE).simulate_cascade(["e1"])
    asset_ids = [e["asset_id"] for e in result["events"]]
    assert asset_ids == ["e1", "e2", "e3", "e4"]
    assert len(asset_ids) == len(set(asset_ids))


def test_event_ordering_within_a_round():
    result = _engine_from(SQUARE).simulate_cascade(["e1"])
    step2 = [e["asset_id"] for e in result["events"] if e["step"] == 2]
    assert step2 == ["e2", "e3", "e4"]
    assert all(e["asset_type"] == "edge" for e in result["events"])


def test_triggered_by_follows_previous_round():
    result = _engine_from(SQUARE).simulate_cascade(["e1"])
    assert result["events"][0]["triggered_by"] == []
    for event in result["events"]:
        if event["step"] == 2:
            assert event["triggered_by"] == ["e1"]
            assert event["reason"] == "last_remaining_corridor"


def test_multi_step_cascade_triggered_by_chain():
    sim = CascadeSimulator(K4)
    engine = ScriptedCandidates(sim, batches=[["hb"], ["hc"]])
    result = engine.simulate_cascade(["ha"])
    assert result["cascade_depth"] == 3
    assert [step["newly_failed"] for step in result["steps"]] == [["ha"], ["hb"], ["hc"]]
    by_step = {e["step"]: e for e in result["events"]}
    assert by_step[1]["triggered_by"] == []
    assert by_step[2]["triggered_by"] == ["ha"]
    assert by_step[3]["triggered_by"] == ["hb"]
    assert result["stopped_reason"] == "stabilized"


def test_max_depth_stops_before_applying_known_corridor():
    result = CascadeEngine(CascadeSimulator(TWO_PATH), max_steps=1).simulate_cascade(["hp"])
    assert result["cascade_depth"] == 1
    assert result["stopped_reason"] == "max_depth"
    assert result["steps"][0]["newly_failed"] == ["hp"]
    assert all(e["reason"] == "initial_failure" for e in result["events"])


def test_stranded_delta_is_per_step():
    result = _engine_from(TWO_PATH).simulate_cascade(["hp"])
    assert "p" not in result["steps"][0]["newly_stranded"]
    assert "p" in result["steps"][1]["newly_stranded"]
    assert "p" in result["stranded_nodes"]


def test_independent_cascades_on_different_graphs():
    shared_unused = CascadeSimulator(K4)
    a = CascadeEngine(CascadeSimulator(TWO_PATH)).simulate_cascade(["hp"])
    b = CascadeEngine(CascadeSimulator(K4)).simulate_cascade(["ha"])
    assert a["cascade_depth"] == 2
    assert b["cascade_depth"] == 1
    assert shared_unused.G.number_of_edges() == 7


def test_result_has_required_keys():
    result = _engine_from(TWO_PATH).simulate_cascade(["hp"])
    for key in (
        "affected_routes",
        "stranded_nodes",
        "impact_score",
        "events",
        "steps",
        "cascade_depth",
        "stopped_reason",
    ):
        assert key in result
    event = result["events"][0]
    for key in ("asset_id", "asset_type", "step", "reason", "triggered_by"):
        assert key in event
    step = result["steps"][0]
    for key in ("step", "newly_failed", "newly_stranded", "affected_routes", "impact_score"):
        assert key in step


# --- Phase 6: Manipal integration (read-only; does not edit data files) ---

MANIPAL_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "manipal_network.json")
)

# Chosen from the actual JSON: 1 hospital, 1 depot, degree-1 leaf, degree-4 hub.
MANIPAL_HOSPITAL = "10156270806"  # KMC Hospital
MANIPAL_DEPOT = "1828354385"  # MIT Depot (FC)
MANIPAL_LOW_IMPACT = "10129706135"  # degree 1 junction
MANIPAL_HIGH_DEGREE = "9933536956"  # degree 4 junction (criticality proxy)
MANIPAL_LEAF_EDGE = "edge_276"  # 10129706135 -- 10129706138
MANIPAL_HUB_EDGE = "edge_4"  # 6641211400 -- 9933536956

_manipal_sim = None


def _manipal_simulator():
    global _manipal_sim
    if _manipal_sim is None:
        with open(MANIPAL_PATH, encoding="utf-8") as handle:
            _manipal_sim = CascadeSimulator(json.load(handle))
    return _manipal_sim


def _manipal_engine():
    return CascadeEngine(_manipal_simulator())


def _summarize(label, failed_ids, result):
    return {
        "label": label,
        "failed_ids": list(failed_ids),
        "impact_score": result["impact_score"],
        "stranded_count": len(result["stranded_nodes"]),
        "affected_count": len(result["affected_routes"]),
        "cascade_depth": result["cascade_depth"],
        "stopped_reason": result["stopped_reason"],
        "event_count": len(result["events"]),
        "secondary_events": [
            e for e in result["events"] if e["reason"] != "initial_failure"
        ],
    }


def test_manipal_file_is_readable_and_has_facilities():
    sim = _manipal_simulator()
    assert MANIPAL_HOSPITAL in sim.targets
    assert MANIPAL_DEPOT in sim.targets
    assert sim.G.number_of_nodes() == 302
    assert sim.G.number_of_edges() == 335


def test_manipal_low_impact_junction():
    sim = _manipal_simulator()
    result = CascadeEngine(sim).simulate_cascade([MANIPAL_LOW_IMPACT])
    phase1 = sim.simulate_failure([MANIPAL_LOW_IMPACT])
    assert result["steps"][0]["impact_score"] == phase1["impact_score"]
    assert result["stopped_reason"] in ("stabilized", "max_depth")
    assert sim.G.has_node(MANIPAL_LOW_IMPACT)
    summary = _summarize("low_impact_junction", [MANIPAL_LOW_IMPACT], result)
    assert summary["cascade_depth"] >= 1


def test_manipal_high_degree_junction():
    sim = _manipal_simulator()
    result = CascadeEngine(sim).simulate_cascade([MANIPAL_HIGH_DEGREE])
    phase1 = sim.simulate_failure([MANIPAL_HIGH_DEGREE])
    assert result["steps"][0]["impact_score"] == phase1["impact_score"]
    assert result["stopped_reason"] in ("stabilized", "max_depth")
    assert sim.G.has_node(MANIPAL_HIGH_DEGREE)


def test_manipal_hospital_failure():
    sim = _manipal_simulator()
    result = CascadeEngine(sim).simulate_cascade([MANIPAL_HOSPITAL])
    assert result["stopped_reason"] in ("stabilized", "max_depth")
    assert result["events"][0]["reason"] == "initial_failure"
    assert sim.G.has_node(MANIPAL_HOSPITAL)
    node_secondary = [
        e for e in result["events"]
        if e["reason"] == "last_remaining_corridor" and e["asset_type"] == "node"
    ]
    assert node_secondary == []


def test_manipal_depot_failure():
    sim = _manipal_simulator()
    result = CascadeEngine(sim).simulate_cascade([MANIPAL_DEPOT])
    assert result["stopped_reason"] in ("stabilized", "max_depth")
    assert sim.G.has_node(MANIPAL_DEPOT)


def test_manipal_leaf_edge_failure():
    sim = _manipal_simulator()
    result = CascadeEngine(sim).simulate_cascade([MANIPAL_LEAF_EDGE])
    phase1 = sim.simulate_failure([MANIPAL_LEAF_EDGE])
    assert result["steps"][0]["impact_score"] == phase1["impact_score"]
    assert result["events"][0]["asset_type"] == "edge"
    assert result["stopped_reason"] in ("stabilized", "max_depth")
    assert any(d.get("id") == MANIPAL_LEAF_EDGE for _, _, d in sim.G.edges(data=True))


def test_manipal_hub_edge_failure():
    sim = _manipal_simulator()
    result = CascadeEngine(sim).simulate_cascade([MANIPAL_HUB_EDGE])
    phase1 = sim.simulate_failure([MANIPAL_HUB_EDGE])
    assert result["steps"][0]["impact_score"] == phase1["impact_score"]
    assert result["stopped_reason"] in ("stabilized", "max_depth")
    assert any(d.get("id") == MANIPAL_HUB_EDGE for _, _, d in sim.G.edges(data=True))


def test_manipal_graph_unchanged_after_all_scenarios():
    sim = _manipal_simulator()
    nodes_before = sim.G.number_of_nodes()
    edges_before = sim.G.number_of_edges()
    engine = CascadeEngine(sim)
    for failed in (
        [MANIPAL_LOW_IMPACT],
        [MANIPAL_HIGH_DEGREE],
        [MANIPAL_HOSPITAL],
        [MANIPAL_DEPOT],
        [MANIPAL_LEAF_EDGE],
        [MANIPAL_HUB_EDGE],
    ):
        engine.simulate_cascade(failed)
    assert sim.G.number_of_nodes() == nodes_before
    assert sim.G.number_of_edges() == edges_before


def test_manipal_no_forced_cascade_on_redundant_click():
    """A leaf failure may stay depth 1. That is a valid Phase-6 outcome."""
    result = _manipal_engine().simulate_cascade([MANIPAL_LOW_IMPACT])
    assert result["cascade_depth"] >= 1
    if result["cascade_depth"] == 1:
        assert result["stopped_reason"] == "stabilized"
        assert all(e["reason"] == "initial_failure" for e in result["events"])
