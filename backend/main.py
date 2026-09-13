from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import time
import logging

from config import settings
from schemas import (
    NetworkResponse,
    SimulateRequest,
    SimulationResponse,
    CriticalityItem,
    ExplainRequest,
    ExplainResponse,
    HealthResponse
)
from dependencies import get_network_data, get_simulator
from services.algorithms import CascadeSimulator
from services.ai import generate_incident_brief

logger = logging.getLogger("api")

app = FastAPI(
    title="CascadeMap API",
    description="Disaster-resilience and critical-infrastructure simulator API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = f"{process_time * 1000:.2f} ms"
    logger.info(f"{request.method} {request.url.path} completed in {process_time * 1000:.2f} ms - Status {response.status_code}")
    return response

@app.on_event("startup")
def startup_event():
    logger.info("Starting up CascadeMap backend...")
    get_simulator()
    logger.info("Startup complete.")

@app.get("/health", response_model=HealthResponse, summary="Health Check")
def health_check(network_data: dict = Depends(get_network_data)):
    return {
        "status": "ok",
        "nodes": len(network_data["nodes"]),
        "edges": len(network_data["edges"])
    }

@app.get("/network", response_model=NetworkResponse, summary="Get Network Topology")
def get_network(network_data: dict = Depends(get_network_data)):
    """Returns the full nodes and edges arrays for the current graph."""
    return network_data

@app.get("/criticality", response_model=List[CriticalityItem], summary="Get Network Criticality")
def get_criticality(simulator: CascadeSimulator = Depends(get_simulator)):
    """Returns the top 100 most critical nodes based on betweenness centrality."""
    # Deterministically sort: by score descending, then by node_id ascending
    sorted_criticality = sorted(
        simulator.criticality_ranking,
        key=lambda x: (-x["centrality_score"], str(x["node_id"]))
    )
    return sorted_criticality[:100]

@app.post("/simulate-failure", response_model=SimulationResponse, summary="Simulate Infrastructure Failure")
def simulate_failure(req: SimulateRequest, simulator: CascadeSimulator = Depends(get_simulator)):
    """Simulates the removal of specific nodes or edges from the network and calculates the impact."""
    for failed_id in req.failed_ids:
        is_node = simulator.G.has_node(failed_id)
        is_edge = any(d.get("id") == failed_id for u, v, d in simulator.G.edges(data=True))
        if not is_node and not is_edge:
            logger.warning(f"Simulation rejected: Unknown ID {failed_id}")
            raise HTTPException(status_code=400, detail=f"Unknown ID: {failed_id}")

    try:
        result = simulator.simulate_failure(req.failed_ids)
        
        # Ensure deterministic output arrays by sorting them
        result["affected_routes"] = sorted(result.get("affected_routes", []), key=str)
        result["stranded_nodes"] = sorted(result.get("stranded_nodes", []), key=str)
        
        return result
    except Exception as e:
        logger.error(f"Simulation failed with error: {str(e)}")
        raise HTTPException(status_code=500, detail="Simulation execution failed")

@app.post("/explain", response_model=ExplainResponse, summary="Generate AI Explanation")
def explain(req: ExplainRequest):
    """Generates a brief narrative and recommendation based on simulation outputs."""
    result_dict = req.model_dump()
    brief = generate_incident_brief(result_dict)
    return brief
