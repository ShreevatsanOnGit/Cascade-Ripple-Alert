# Manipal Campus Network

This dataset provides the road network graph for the Manipal Institute of Technology (MIT) and surrounding Manipal areas, enabling targeted failure simulations on actual campus infrastructure.

## Data Source
- **Provider:** OpenStreetMap (OSM) via OSMnx
- **Geographic Area:** Center point (13.352, 74.792), spanning a 1.2km radius. This covers MIT Manipal, KMC Hospital, Kamath Circle, and surrounding student housing zones.
- **Retrieval Method:** Python script (`fetch_manipal.py`) using `ox.graph_from_point(network_type='drive')`.

## Characteristics
- **Nodes/Edges:** Represent real driveable roads and intersections.
- **Node Types:** 
  - `hospital`: KMC Hospital and medical facilities.
  - `depot`: Major bus stands, maintenance buildings, and transport hubs.
  - `junction`: Standard intersections and academic block access nodes.
- **Edge Types:**
  - `bridge`: Roads tagged as bridges in OSM.
  - `road`: Standard roads.

## Simulation Data Enhancements
- **Population Weight:** These are *simulation weights*, not official population statistics. The weights are heuristically generated based on central placement and node type (e.g., hospitals and depots have much higher weights, while random junctions have variable smaller weights).
- **Edge Weight:** Retained as Euclidean distance (meters) to remain mathematically compatible with the existing Phase 1 prototype backend.

## Assumptions
- Non-driveable pedestrian paths were excluded to focus on critical vehicle infrastructure failures.
- POIs lacking exact node matches were snapped to the nearest driveable road node using OSMnx spatial mapping.
