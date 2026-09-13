def generate_incident_brief(simulation_result: dict) -> dict:
    affected = len(simulation_result.get("affected_routes", []))
    stranded = len(simulation_result.get("stranded_nodes", []))
    impact = simulation_result.get("impact_score", 0.0)

    if impact == 0:
        narrative = f"The selected failure has limited network impact. No nodes are stranded, and the calculated impact score is {impact:.2f}."
        rec = "No immediate action required. The network retains sufficient redundancy."
    elif stranded > 0:
        narrative = f"The simulated failure resulted in an impact score of {impact:.2f}. This failure structurally isolates {stranded} nodes from essential services, and forces rerouting for {affected} other locations."
        rec = "Emergency dispatch required for stranded zones. Prioritize immediate structural repair to restore connectivity to isolated nodes."
    else:
        narrative = f"The simulated failure resulted in an impact score of {impact:.2f}. While no nodes are completely isolated, {affected} routes are experiencing delays due to forced rerouting."
        rec = "Deploy traffic management to alternate routes to alleviate congestion."

    return {
        "narrative": narrative,
        "recommendation": rec
    }
