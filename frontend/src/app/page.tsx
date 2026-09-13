"use client";
// @ts-nocheck

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { AlertTriangle, Activity, Map as MapIcon, ArrowLeftRight } from "lucide-react";

// Dynamically import Map to prevent Next.js SSR from crashing on window object
const MapComponent = dynamic(() => import("../components/Map"), { ssr: false });

export default function Home() {
  const [network, setNetwork] = useState<any>(null);
  const [criticality, setCriticality] = useState<any[]>([]);
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [simulationResult, setSimulationResult] = useState<any>(null);
  const [explainResult, setExplainResult] = useState<any>(null);
  const [showAfter, setShowAfter] = useState(true);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Fetch Network
    fetch("http://localhost:8000/network")
      .then(res => res.json())
      .then(data => setNetwork(data))
      .catch(err => console.error("Failed to load network", err));
      
    // Fetch Criticality
    fetch("http://localhost:8000/criticality")
      .then(res => res.json())
      .then(data => setCriticality(data.slice(0, 5))) // Top 5
      .catch(err => console.error("Failed to load criticality", err));
  }, []);

    const [loadingStage, setLoadingStage] = useState("");

    // ... inside handleSimulate
  const handleSimulate = async () => {
    if (!selectedNode) return;
    setLoading(true);
    setLoadingStage("SIMULATING FAILURE...");
    setExplainResult(null);
    
    try {
      const res = await fetch("http://localhost:8000/simulate-failure", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ failed_ids: [selectedNode.id] })
      });
      const data = await res.json();
      setSimulationResult({ ...data, failed_ids: [selectedNode.id] });
      setShowAfter(true);

      setLoadingStage("ANALYZING INCIDENT...");
      // Fetch mocked explain
      const explainRes = await fetch("http://localhost:8000/explain", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
      });
      const explainData = await explainRes.json();
      setExplainResult(explainData);
    } catch (err) {
      console.error("Simulation failed", err);
    } finally {
      setLoading(false);
      setLoadingStage("");
    }
  };

  const handleReset = () => {
    setSimulationResult(null);
    setExplainResult(null);
    setSelectedNode(null);
    setShowAfter(true);
  };

  const getSelectedNodeCriticality = () => {
    if (!selectedNode) return null;
    return criticality.find(c => c.node_id === selectedNode.id);
  };

  const critInfo = getSelectedNodeCriticality();

  return (
    <main className="flex h-screen w-full bg-gray-950 text-white overflow-hidden">
      {/* Sidebar */}
      <div className="w-96 flex flex-col h-full bg-gray-900 border-r border-gray-800 shadow-xl z-10 overflow-y-auto">
        <div className="p-6 border-b border-gray-800 sticky top-0 bg-gray-900 z-20">
          <h1 className="text-2xl font-bold text-blue-400 flex items-center gap-2">
            <Activity className="w-6 h-6" /> CascadeMap
          </h1>
          <p className="text-gray-400 text-sm mt-2">Disaster Resilience Simulator</p>
        </div>

        <div className="flex-1 p-6 space-y-8">
          
          {/* Controls */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold uppercase tracking-wider text-gray-500 text-sm">Action Center</h2>
            {selectedNode ? (
              <div className="bg-gray-800 p-4 rounded-lg border border-gray-700">
                <h3 className="font-bold text-white mb-2 uppercase">{selectedNode.name || selectedNode.id}</h3>
                <div className="space-y-1 mb-4 text-sm text-gray-300">
                  <p>Type: <span className="capitalize">{selectedNode.type}</span></p>
                  <p>Population Weight: {selectedNode.population_weight}</p>
                  {critInfo && <p>Criticality: <span className="text-blue-400 font-mono">{critInfo.centrality_score.toFixed(4)}</span></p>}
                </div>
                
                {simulationResult && critInfo && (
                  <div className="mt-4 pt-4 border-t border-gray-700">
                    <p className="text-xs text-gray-400 mb-1">Why it matters:</p>
                    <p className="text-sm italic text-gray-300">
                      {critInfo.centrality_score > 0.01 ? "Connects an otherwise isolated section of the network." : "Plays a minor role in overall routing efficiency."}
                    </p>
                  </div>
                )}

                <div className="flex gap-2 mt-4">
                  <button 
                    onClick={handleSimulate}
                    disabled={loading}
                    className="flex-1 bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white py-2 px-4 rounded transition flex justify-center items-center gap-2 font-medium"
                  >
                    <AlertTriangle className="w-4 h-4" /> {loading ? loadingStage : "Simulate Failure"}
                  </button>
                  <button 
                    onClick={handleReset}
                    className="bg-gray-700 hover:bg-gray-600 px-4 py-2 rounded transition font-medium"
                  >
                    Reset
                  </button>
                </div>
              </div>
            ) : (
              <div className="bg-gray-800 p-4 rounded-lg border border-gray-700 border-dashed text-center">
                <MapIcon className="w-8 h-8 mx-auto text-gray-500 mb-2" />
                <p className="text-sm text-gray-400">Click any node on the map to target it for failure simulation.</p>
              </div>
            )}
          </div>

          {/* Results */}
          {simulationResult && (
            <div className="space-y-4 animate-in fade-in slide-in-from-bottom-4">
              <h2 className="text-lg font-semibold uppercase tracking-wider text-red-400 text-sm">Impact Report</h2>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-800 p-4 rounded-lg border border-red-900/30">
                  <p className="text-xs text-gray-400">Impact Score</p>
                  <p className="text-2xl font-bold text-red-500">{simulationResult.impact_score}</p>
                </div>
                <div className="bg-gray-800 p-4 rounded-lg border border-orange-900/30">
                  <p className="text-xs text-gray-400">Stranded Nodes</p>
                  <p className="text-2xl font-bold text-orange-500">{simulationResult.stranded_nodes.length}</p>
                </div>
              </div>
              
              <div className="bg-gray-800 p-4 rounded-lg border border-gray-700">
                <p className="text-xs text-gray-400 mb-2">AI Incident Brief</p>
                {explainResult ? (
                  <>
                    <p className="text-sm text-gray-300 mb-2">{explainResult.narrative}</p>
                    <p className="text-sm text-blue-300 font-semibold">Recommendation: {explainResult.recommendation}</p>
                  </>
                ) : (
                  <p className="text-sm text-gray-500 italic animate-pulse">Generating brief...</p>
                )}
              </div>
            </div>
          )}

          {/* Criticality Leaderboard */}
          <div className="space-y-4 pb-8">
            <h2 className="text-lg font-semibold uppercase tracking-wider text-gray-500 text-sm">Most Critical Assets</h2>
            <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
              {criticality.map((c, idx) => (
                <div key={c.node_id} className="flex justify-between p-3 border-b border-gray-700/50 last:border-0 hover:bg-gray-700/50 cursor-pointer">
                  <span className="text-sm font-mono text-gray-300">#{idx + 1} {c.node_id.substring(0,8)}</span>
                  <span className="text-sm text-blue-400 font-bold">{c.centrality_score.toFixed(4)}</span>
                </div>
              ))}
            </div>
          </div>

        </div>
      </div>

      {/* Map Area */}
      <div className="flex-1 relative bg-gray-900">
        
        {simulationResult && (
          <div className="absolute top-6 left-1/2 -translate-x-1/2 z-[1000] bg-gray-900/90 border border-gray-700 p-2 rounded-full shadow-lg backdrop-blur-sm flex items-center gap-4">
            <span className={`text-sm font-bold px-3 py-1 rounded-full cursor-pointer transition ${!showAfter ? 'bg-blue-600 text-white' : 'text-gray-400'}`} onClick={() => setShowAfter(false)}>
              Before
            </span>
            <ArrowLeftRight className="w-4 h-4 text-gray-500" />
            <span className={`text-sm font-bold px-3 py-1 rounded-full cursor-pointer transition ${showAfter ? 'bg-red-600 text-white' : 'text-gray-400'}`} onClick={() => setShowAfter(true)}>
              After
            </span>
          </div>
        )}

        <MapComponent 
          networkData={network} 
          onNodeClick={(node: any) => setSelectedNode(node)}
          simulationResult={showAfter ? simulationResult : null}
          criticalityData={criticality}
        />
        
        {/* Map Legend Overlay */}
        <div className="absolute bottom-6 right-6 bg-gray-900/90 p-4 rounded-lg border border-gray-700 shadow-lg z-[1000] backdrop-blur-sm">
          <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-3">Legend</h3>
          <div className="space-y-2 text-sm">
            <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-[#fca5a5]"></div> Hospital</div>
            <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-[#93c5fd]"></div> Depot</div>
            <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-[#6b7280]"></div> Junction</div>
            <div className="flex items-center gap-2 mt-2 pt-2 border-t border-gray-700"><div className="w-3 h-3 rounded-full bg-[#ef4444] shadow-[0_0_8px_red]"></div> Failed</div>
            <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-[#dc2626] animate-pulse"></div> Stranded</div>
            <div className="flex items-center gap-2"><div className="w-3 h-3 bg-[#f97316]"></div> Affected Route</div>
          </div>
        </div>
      </div>
    </main>
  );
}
