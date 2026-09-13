export type NodeType = "junction" | "bridge" | "hospital" | "depot";
export type EdgeType = "road" | "bridge";

export interface Node {
  id: string;
  name: string;
  lat: number;
  lon: number;
  type: NodeType;
  population_weight: number;
  flood_prone?: boolean;
}

export interface Edge {
  id: string;
  from_node: string;
  to_node: string;
  weight: number;
  type: EdgeType;
  capacity: number; // Now required for Phase 2
}

export interface SimulationResult {
  affected_routes: string[];
  stranded_nodes: string[];
  impact_score: number;
}

export interface CriticalityScore {
  node_id: string;
  centrality_score: number;
}

export interface CascadeRound {
  round_number: number;
  newly_failed: string[];
  stranded_nodes: string[];
  cumulative_impact_score: number;
}

export interface CascadeResult {
  rounds: CascadeRound[];
  final_impact_score: number;
  resilience_score: number;
}
