"""Internal multi-round cascade engine.

Wraps the existing Phase-1 CascadeSimulator. Does not change Phase-1 math.
Secondary failures use only newly created last-remaining facility corridors.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Literal, Optional, Set

import networkx as nx

from services.algorithms import CascadeSimulator

MAX_CASCADE_STEPS = 10
StoppedReason = Literal["stabilized", "max_depth"]
AssetType = Literal["node", "edge"]

# Stable event order: edges before nodes, then ID.
_ASSET_TYPE_ORDER = {"edge": 0, "node": 1}


class CascadeEngine:
    """Deterministic cascade loop around an existing CascadeSimulator.

    Public interface:
        CascadeEngine(simulator)
        simulate_cascade(failed_ids) -> dict
    """

    def __init__(
        self,
        simulator: CascadeSimulator,
        max_steps: int = MAX_CASCADE_STEPS,
    ) -> None:
        if max_steps < 1:
            raise ValueError("max_steps must be >= 1")
        self.simulator = simulator
        self.max_steps = max_steps

    def simulate_cascade(self, failed_ids: List[str]) -> Dict[str, Any]:
        """Run a cascade starting from the given node/edge IDs.

        Round 1 applies the caller's IDs. Later rounds apply every newly
        created last-remaining facility corridor together.
        """
        initial_ids = self._validate_and_normalize_ids(failed_ids)

        G_work = self.simulator.G.copy()
        failed_set: Set[str] = set()
        events: List[Dict[str, Any]] = []
        steps: List[Dict[str, Any]] = []
        previous_stranded: Set[str] = set()
        previous_newly_failed: List[str] = []
        previous_corridors = self._facility_last_corridors(G_work)

        self._apply_failures(G_work, initial_ids)
        failed_set.update(initial_ids)

        metrics = self._phase1_metrics(failed_set)
        step_stranded = self._step_stranded(metrics["stranded_nodes"], previous_stranded)
        events.extend(
            self._make_events(
                asset_ids=initial_ids,
                step=1,
                reason="initial_failure",
                triggered_by=[],
            )
        )
        steps.append(
            self._make_step(
                step=1,
                newly_failed=initial_ids,
                newly_stranded=step_stranded,
                metrics=metrics,
            )
        )
        previous_stranded = set(metrics["stranded_nodes"])
        previous_newly_failed = list(initial_ids)

        stopped_reason: StoppedReason = "stabilized"

        while True:
            raw_candidates = self._find_candidate_failures(
                G_work, failed_set, previous_corridors
            )
            candidates = self._normalize_candidates(raw_candidates, failed_set, G_work)

            if not candidates:
                stopped_reason = "stabilized"
                break
            if len(steps) >= self.max_steps:
                stopped_reason = "max_depth"
                break

            next_step = len(steps) + 1
            previous_corridors = self._facility_last_corridors(G_work)
            self._apply_failures(G_work, candidates)
            failed_set.update(candidates)

            metrics = self._phase1_metrics(failed_set)
            step_stranded = self._step_stranded(metrics["stranded_nodes"], previous_stranded)
            events.extend(
                self._make_events(
                    asset_ids=candidates,
                    step=next_step,
                    reason="last_remaining_corridor",
                    triggered_by=previous_newly_failed,
                )
            )
            steps.append(
                self._make_step(
                    step=next_step,
                    newly_failed=candidates,
                    newly_stranded=step_stranded,
                    metrics=metrics,
                )
            )
            previous_stranded = set(metrics["stranded_nodes"])
            previous_newly_failed = list(candidates)

        events = self._sort_events(events)
        final_metrics = self._phase1_metrics(failed_set)

        return {
            "affected_routes": self._sort_ids(final_metrics["affected_routes"]),
            "stranded_nodes": self._sort_ids(final_metrics["stranded_nodes"]),
            "impact_score": final_metrics["impact_score"],
            "events": events,
            "steps": steps,
            "cascade_depth": len(steps),
            "stopped_reason": stopped_reason,
        }

    def _find_candidate_failures(
        self,
        G_work: Any,
        failed_set: Set[str],
        previous_corridors: Optional[Set[str]] = None,
    ) -> List[str]:
        """Return edge IDs that became last-remaining facility corridors.

        Evaluated on a frozen working graph. Only edges that are corridors
        now, were not corridors before this round, and are not already failed.
        Does not fail stranded nodes.
        """
        previous = set(previous_corridors or [])
        current = self._facility_last_corridors(G_work)
        return self._sort_ids(current - previous - failed_set)

    def _remaining_targets(self, graph: Any) -> Set[str]:
        return {target for target in self.simulator.targets if target in graph}

    def _facility_last_corridors(self, graph: Any) -> Set[str]:
        """Edges whose removal would cut some still-served node from all facilities."""
        targets = self._remaining_targets(graph)
        if not targets or graph.number_of_edges() == 0:
            return set()

        corridors: Set[str] = set()
        for u, v in list(nx.bridges(graph)):
            edge_attrs = dict(graph.get_edge_data(u, v) or {})
            edge_id = edge_attrs.get("id")
            if edge_id is None:
                continue

            graph.remove_edge(u, v)
            try:
                side_u = nx.node_connected_component(graph, u)
                side_v = nx.node_connected_component(graph, v)
            finally:
                graph.add_edge(u, v, **edge_attrs)

            has_u = bool(side_u & targets)
            has_v = bool(side_v & targets)
            if has_u == has_v:
                continue

            no_facility_side = side_v if has_u else side_u
            if no_facility_side - targets:
                corridors.add(edge_id)
        return corridors

    def _validate_and_normalize_ids(self, failed_ids: Iterable[str]) -> List[str]:
        if failed_ids is None:
            raise ValueError("failed_ids is required")
        if isinstance(failed_ids, (str, bytes)):
            raise ValueError("failed_ids must be a list of IDs, not a string")
        try:
            ids = list(failed_ids)
        except TypeError as exc:
            raise ValueError("failed_ids must be a list of IDs") from exc

        seen: Set[str] = set()
        unique: List[str] = []
        for failed_id in ids:
            if failed_id in seen:
                continue
            if not self._is_known_asset(failed_id):
                raise ValueError(f"Unknown ID: {failed_id}")
            seen.add(failed_id)
            unique.append(failed_id)
        return self._sort_ids(unique)

    def _is_known_asset(self, asset_id: str) -> bool:
        if self.simulator.G.has_node(asset_id):
            return True
        return any(d.get("id") == asset_id for _, _, d in self.simulator.G.edges(data=True))

    def _asset_type(self, asset_id: str) -> AssetType:
        if self.simulator.G.has_node(asset_id):
            return "node"
        return "edge"

    def _apply_failures(self, graph: Any, failed_ids: Iterable[str]) -> None:
        """Remove nodes/edges from a working copy. Same rules as Phase 1."""
        ids = list(failed_ids)
        graph.remove_nodes_from([n for n in ids if n in graph])
        edges_to_remove = [
            (u, v) for u, v, d in graph.edges(data=True) if d.get("id") in ids
        ]
        graph.remove_edges_from(edges_to_remove)

    def _phase1_metrics(self, failed_set: Set[str]) -> Dict[str, Any]:
        """Delegate scoring to CascadeSimulator.simulate_failure (healthy baseline)."""
        result = self.simulator.simulate_failure(self._sort_ids(failed_set))
        return {
            "affected_routes": self._sort_ids(result.get("affected_routes", [])),
            "stranded_nodes": self._sort_ids(result.get("stranded_nodes", [])),
            "impact_score": result["impact_score"],
        }

    def _normalize_candidates(
        self,
        raw_candidates: Iterable[str],
        failed_set: Set[str],
        G_work: Any,
    ) -> List[str]:
        seen: Set[str] = set()
        cleaned: List[str] = []
        for asset_id in raw_candidates:
            if asset_id in failed_set or asset_id in seen:
                continue
            if not self._is_present_on_working_graph(G_work, asset_id):
                continue
            seen.add(asset_id)
            cleaned.append(asset_id)
        return self._sort_ids(cleaned)

    def _is_present_on_working_graph(self, graph: Any, asset_id: str) -> bool:
        if graph.has_node(asset_id):
            return True
        return any(d.get("id") == asset_id for _, _, d in graph.edges(data=True))

    def _make_events(
        self,
        asset_ids: List[str],
        step: int,
        reason: str,
        triggered_by: List[str],
    ) -> List[Dict[str, Any]]:
        parents = self._sort_ids(triggered_by)
        events = [
            {
                "asset_id": asset_id,
                "asset_type": self._asset_type(asset_id),
                "step": step,
                "reason": reason,
                "triggered_by": list(parents),
            }
            for asset_id in asset_ids
        ]
        return self._sort_events(events)

    def _make_step(
        self,
        step: int,
        newly_failed: List[str],
        newly_stranded: List[str],
        metrics: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "step": step,
            "newly_failed": self._sort_ids(newly_failed),
            "newly_stranded": self._sort_ids(newly_stranded),
            "affected_routes": self._sort_ids(metrics["affected_routes"]),
            "impact_score": metrics["impact_score"],
        }

    @staticmethod
    def _step_stranded(stranded_vs_baseline: Iterable[str], previous: Set[str]) -> List[str]:
        return sorted(set(stranded_vs_baseline) - previous, key=str)

    @staticmethod
    def _sort_ids(ids: Iterable[str]) -> List[str]:
        return sorted(ids, key=str)

    @staticmethod
    def _sort_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return sorted(
            events,
            key=lambda e: (
                e["step"],
                _ASSET_TYPE_ORDER.get(e["asset_type"], 99),
                str(e["asset_id"]),
            ),
        )
