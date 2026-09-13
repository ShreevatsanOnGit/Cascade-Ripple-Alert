"use client";

import { MapContainer, TileLayer, CircleMarker, Polyline, Tooltip, useMapEvents } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { useState } from "react";

// A sub-component to handle zoom level state
function ZoomListener({ onZoomChange }) {
    useMapEvents({
        zoomend: (e) => {
            onZoomChange(e.target.getZoom());
        }
    });
    return null;
}

export default function MapComponent({ networkData, onNodeClick, simulationResult, criticalityData = [] }) {
    const [zoomLevel, setZoomLevel] = useState(15);
    
    if (!networkData || !networkData.nodes) return <div className="p-4 text-white">Loading map data...</div>;

    const center = networkData.nodes.length > 0 
        ? [networkData.nodes[0].lat, networkData.nodes[0].lon] 
        : [13.340881, 74.742142];

    const failedIds = simulationResult ? simulationResult.failed_ids || [] : [];
    const strandedNodes = simulationResult ? simulationResult.stranded_nodes || [] : [];
    const affectedRoutes = simulationResult ? simulationResult.affected_routes || [] : [];

    const getNodeColor = (node) => {
        if (failedIds.includes(node.id)) return "#ef4444"; // Strong red
        if (strandedNodes.includes(node.id)) return "#dc2626"; // Red for stranded
        switch(node.type) {
            case "hospital": return "#fca5a5";
            case "depot": return "#93c5fd";
            default: return "#4b5563"; // Darker, subtle gray for regular junctions
        }
    };

    const getEdgeColor = (edge) => {
        if (failedIds.includes(edge.id)) return "#ef4444"; // Strong red
        if (affectedRoutes.includes(edge.from_node) || affectedRoutes.includes(edge.to_node)) return "#f97316"; // Bright orange
        return edge.type === "bridge" ? "#3b82f6" : "#374151"; // Muted
    };

    // Calculate node radius dynamically based on zoom and type
    const getRadius = (node) => {
        const isPOI = node.type === "hospital" || node.type === "depot";
        const isFailed = failedIds.includes(node.id) || strandedNodes.includes(node.id);
        
        let baseRadius = isPOI ? 6 : 2;
        if (isFailed) baseRadius += 2;
        
        // Scale down if zoomed out
        if (zoomLevel < 14) return baseRadius * 0.6;
        if (zoomLevel > 16) return baseRadius * 1.5;
        return baseRadius;
    };

    return (
        <MapContainer center={center} zoom={15} style={{ height: "100%", width: "100%", backgroundColor: '#111827' }}>
            <ZoomListener onZoomChange={setZoomLevel} />
            <TileLayer
                url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}"
                attribution='&copy; <a href="https://www.esri.com/">Esri</a>'
            />
            
            {networkData.edges.map((edge) => {
                const fromNode = networkData.nodes.find(n => n.id === edge.from_node);
                const toNode = networkData.nodes.find(n => n.id === edge.to_node);
                if (!fromNode || !toNode) return null;
                const isAffected = affectedRoutes.includes(edge.from_node) || affectedRoutes.includes(edge.to_node);
                return (
                    <Polyline 
                        key={edge.id}
                        positions={[[fromNode.lat, fromNode.lon], [toNode.lat, toNode.lon]]}
                        color={getEdgeColor(edge)}
                        weight={isAffected ? 4 : (edge.type === "bridge" ? 2 : 1)}
                        opacity={isAffected ? 1 : 0.3}
                    />
                );
            })}

            {networkData.nodes.map((node) => {
                const crit = criticalityData.find(c => c.node_id === node.id);
                const isStranded = strandedNodes.includes(node.id);
                const isFailed = failedIds.includes(node.id);
                
                // Optional LOD: hide regular junctions if zoomed out too far (unless they are failed)
                if (zoomLevel < 13 && node.type === "junction" && !isFailed) return null;

                return (
                    <CircleMarker
                        key={node.id}
                        center={[node.lat, node.lon]}
                        radius={getRadius(node)}
                        color={isFailed || isStranded ? "#ffffff" : getNodeColor(node)} // white outline for failed nodes
                        weight={isFailed || isStranded ? 1.5 : 0.5} // stroke width
                        fillColor={getNodeColor(node)}
                        fillOpacity={isFailed || isStranded ? 1 : 0.8}
                        className={isStranded ? "animate-pulse" : ""}
                        eventHandlers={{ click: () => onNodeClick(node) }}
                    >
                        <Tooltip>
                            <div className="text-black text-sm">
                                <strong>{node.name || node.id}</strong><br/>
                                Type: <span className="capitalize">{node.type}</span><br/>
                                Population Weight: {node.population_weight}
                                {crit && (
                                    <><br/>Criticality: {crit.centrality_score.toFixed(4)}</>
                                )}
                            </div>
                        </Tooltip>
                    </CircleMarker>
                );
            })}
        </MapContainer>
    );
}
