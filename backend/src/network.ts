import { Node, Edge, SimulationResult, CascadeResult, CascadeRound } from './types';

export class Network {
  private nodes: Map<string, Node> = new Map();
  private edges: Edge[] = [];
  private adj: Map<string, string[]> = new Map();

  constructor(nodes: Node[], edges: Edge[]) {
    nodes.forEach(n => this.nodes.set(n.id, n));
    this.edges = edges;
    edges.forEach(e => {
      if (!this.adj.has(e.from_node)) this.adj.set(e.from_node, []);
      if (!this.adj.has(e.to_node)) this.adj.set(e.to_node, []);
      this.adj.get(e.from_node)!.push(e.to_node);
      this.adj.get(e.to_node)!.push(e.from_node);
    });
  }

  public getNodes() { return Array.from(this.nodes.values()); }
  public getEdges() { return this.edges; }

  public simulateFailure(failedIds: string[]): SimulationResult {
    const allNodeIds = Array.from(this.nodes.keys());
    const failedSet = new Set(failedIds);

    // In a real city, we'd have multiple components.
    // We calculate reachability from the largest remaining component.
    const result = this.calculateReachability(failedSet);

    return {
      affected_routes: [],
      stranded_nodes: result.stranded,
      impact_score: result.impact
    };
  }

  public simulateCascade(initialFailedIds: string[]): CascadeResult {
    const failedNodes = new Set<string>(initialFailedIds);
    const failedEdges = new Set<string>();
    const rounds: CascadeRound[] = [];
    let roundNum = 0;
    let stabilized = false;

    while (!stabilized) {
      roundNum++;
      const currentNewlyFailedEdges: string[] = [];

      // 1. Calculate current load on all surviving edges
      const loads = this.calculateEdgeLoads(failedNodes, failedEdges);

      // 2. Identify edges that exceed capacity
      for (const edge of this.edges) {
        if (failedEdges.has(edge.id)) continue;
        const load = loads.get(edge.id) || 0;
        if (load > edge.capacity) {
          currentNewlyFailedEdges.push(edge.id);
        }
      }

      if (currentNewlyFailedEdges.length === 0) {
        stabilized = true;
        break;
      }

      // 3. Update failed edges
      currentNewlyFailedEdges.forEach(id => failedEdges.add(id));

      // 4. Calculate impact for this round
      const { stranded, impact } = this.calculateReachability(failedNodes, failedEdges);

      rounds.push({
        round_number: roundNum,
        newly_failed: currentNewlyFailedEdges,
        stranded_nodes: stranded,
        cumulative_impact_score: impact
      });

      // Safety break to prevent infinite loops in degenerate graphs
      if (roundNum > 100) stabilized = true;
    }

    const finalImpact = rounds.length > 0 ? rounds[rounds.length - 1].cumulative_impact_score : 0;
    const totalPossibleImpact = this.calculateTotalWeight();

    return {
      rounds,
      final_impact_score: finalImpact,
      resilience_score: Math.max(0, 1 - (finalImpact / totalPossibleImpact))
    };
  }

  public getCriticality(): { node_id: string, centrality_score: number }[] {
    return Array.from(this.nodes.keys()).map(id => ({
      node_id: id,
      centrality_score: (this.adj.get(id)?.length || 0)
    })).sort((a, b) => b.centrality_score - a.centrality_score);
  }

  private calculateReachability(failedNodes: Set<string>, failedEdges: Set<string> = new Set()): { stranded: string[], impact: number } {
    const allNodeIds = Array.from(this.nodes.keys());
    const startNode = allNodeIds.find(id => !failedNodes.has(id));

    if (!startNode) return { stranded: allNodeIds, impact: this.calculateTotalWeight() };

    const visited = new Set<string>();
    const queue = [startNode];
    visited.add(startNode);

    while (queue.length > 0) {
      const curr = queue.shift()!;
      for (const neighbor of this.adj.get(curr) || []) {
        if (visited.has(neighbor) || failedNodes.has(neighbor)) continue;

        // Check if the edge between curr and neighbor is failed
        const edge = this.edges.find(e =>
          (e.from_node === curr && e.to_node === neighbor) ||
          (e.from_node === neighbor && e.to_node === curr)
        );

        if (edge && failedEdges.has(edge.id)) continue;

        visited.add(neighbor);
        queue.push(neighbor);
      }
    }

    const stranded = allNodeIds.filter(id => !visited.has(id));
    const impact = stranded.reduce((sum, id) => sum + (this.nodes.get(id)?.population_weight || 0), 0);
    return { stranded, impact };
  }

  private calculateEdgeLoads(failedNodes: Set<string>, failedEdges: Set<string>): Map<string, number> {
    const loads = new Map<string, number>();
    const nodes = Array.from(this.nodes.values());

    // Load Model: For every pair of nodes, find the shortest path.
    // Traffic = product of population weights (simple gravity model).
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const start = nodes[i];
        const end = nodes[j];
        if (failedNodes.has(start.id) || failedNodes.has(end.id)) continue;

        const path = this.findShortestPath(start.id, end.id, failedNodes, failedEdges);
        if (path) {
          const traffic = (start.population_weight * end.population_weight) / 1000;
          for (let k = 0; k < path.length - 1; k++) {
            const u = path[k];
            const v = path[k+1];
            const edge = this.edges.find(e =>
              (e.from_node === u && e.to_node === v) ||
              (e.from_node === v && e.to_node === u)
            );
            if (edge) {
              loads.set(edge.id, (loads.get(edge.id) || 0) + traffic);
            }
          }
        }
      }
    }
    return loads;
  }

  private findShortestPath(start: string, end: string, failedNodes: Set<string>, failedEdges: Set<string>): string[] | null {
    const queue: [string, string[]][] = [[start, [start]]];
    const visited = new Set<string>([start]);

    while (queue.length > 0) {
      const [curr, path] = queue.shift()!;
      if (curr === end) return path;

      for (const neighbor of this.adj.get(curr) || []) {
        if (visited.has(neighbor) || failedNodes.has(neighbor)) continue;

        const edge = this.edges.find(e =>
          (e.from_node === curr && e.to_node === neighbor) ||
          (e.from_node === neighbor && e.to_node === curr)
        );
        if (edge && failedEdges.has(edge.id)) continue;

        visited.add(neighbor);
        queue.push([neighbor, [...path, neighbor]]);
      }
    }
    return null;
  }

  private calculateTotalWeight(): number {
    return Array.from(this.nodes.values()).reduce((sum, n) => sum + n.population_weight, 0);
  }
}
