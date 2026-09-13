from pydantic import BaseModel, Field
from typing import List, Literal

class Node(BaseModel):
    id: str = Field(..., description="Unique identifier for the node", example="n1")
    name: str = Field(..., description="Human readable name", example="Central Hub")
    lat: float = Field(..., description="Latitude coordinate", example=40.7128)
    lon: float = Field(..., description="Longitude coordinate", example=-74.0060)
    type: Literal["junction", "bridge", "hospital", "depot"] = Field(..., description="Type of infrastructure asset", example="junction")
    population_weight: int = Field(..., description="Population affected by this node", example=500)

class Edge(BaseModel):
    id: str = Field(..., description="Unique identifier for the edge", example="e1")
    from_node: str = Field(..., description="Source node ID", example="n1")
    to_node: str = Field(..., description="Destination node ID", example="n2")
    weight: float = Field(..., description="Base routing weight/cost (must be >= 0)", example=2.0)
    type: Literal["road", "bridge"] = Field(..., description="Type of connection", example="road")
    capacity: float = Field(100.0, description="Optional capacity constraint", example=100.0)

class NetworkResponse(BaseModel):
    nodes: List[Node] = Field(..., description="List of all nodes in the network")
    edges: List[Edge] = Field(..., description="List of all edges in the network")

class SimulateRequest(BaseModel):
    failed_ids: List[str] = Field(..., description="List of node or edge IDs to fail", example=["n4"])

class SimulationResponse(BaseModel):
    affected_routes: List[str] = Field(..., description="Nodes forced to reroute", example=["n7", "n9"])
    stranded_nodes: List[str] = Field(..., description="Nodes isolated from targets", example=["n10"])
    impact_score: float = Field(..., description="Calculated impact score", example=8.12)

class CriticalityItem(BaseModel):
    node_id: str = Field(..., description="Node ID", example="n4")
    centrality_score: float = Field(..., description="NetworkX betweenness centrality", example=0.472)

class ExplainRequest(BaseModel):
    affected_routes: List[str] = Field(..., description="Nodes forced to reroute", example=["n7", "n9"])
    stranded_nodes: List[str] = Field(..., description="Nodes isolated from targets", example=["n10"])
    impact_score: float = Field(..., description="Calculated impact score", example=8.12)

class ExplainResponse(BaseModel):
    narrative: str = Field(..., description="AI generated summary", example="Critical failure detected.")
    recommendation: str = Field(..., description="AI generated recommendation", example="Dispatch emergency services.")

class HealthResponse(BaseModel):
    status: str = Field(..., example="ok")
    nodes: int = Field(..., example=1369)
    edges: int = Field(..., example=1678)
