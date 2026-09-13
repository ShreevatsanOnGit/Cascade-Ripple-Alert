import streamlit as st
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
import os

st.set_page_config(layout="wide", page_title="Cascading Failure Simulator")

st.title("Cascading Failure Simulator: Critical Infrastructure")
st.markdown("Simulate how a single point of failure propagates through interdependent infrastructure networks.")

# --- 1. Define the Network ---
@st.cache_data
def create_infrastructure_network():
    G = nx.DiGraph() # Directed graph for dependencies (A depends on B)
    
    # Add nodes (Infrastructure assets)
    # Power
    G.add_node("Power Plant Alpha", type="Power", group=1, title="Power Plant Alpha")
    G.add_node("Substation North", type="Power", group=1, title="Substation North")
    G.add_node("Substation South", type="Power", group=1, title="Substation South")
    
    # Water
    G.add_node("Water Treatment A", type="Water", group=2, title="Water Treatment A")
    G.add_node("Pumping Station 1", type="Water", group=2, title="Pumping Station 1")
    
    # Comm
    G.add_node("Telecom Hub X", type="Comm", group=3, title="Telecom Hub X")
    
    # Emergency/Public
    G.add_node("City Hospital", type="Hospital", group=4, title="City Hospital")
    G.add_node("Fire Station 1", type="Emergency", group=4, title="Fire Station 1")
    G.add_node("Residential Grid A", type="Public", group=5, title="Residential Grid A")

    # Add edges (Dependencies) - e.g., Water Treatment A depends on Power Plant Alpha
    edges = [
        ("Power Plant Alpha", "Substation North"),
        ("Power Plant Alpha", "Substation South"),
        
        ("Substation North", "Water Treatment A"),
        ("Substation North", "Telecom Hub X"),
        ("Substation North", "City Hospital"),
        
        ("Substation South", "Pumping Station 1"),
        ("Substation South", "Fire Station 1"),
        ("Substation South", "Residential Grid A"),
        
        ("Water Treatment A", "Pumping Station 1"),
        ("Pumping Station 1", "City Hospital"),
        ("Pumping Station 1", "Residential Grid A"),
        
        ("Telecom Hub X", "City Hospital"),
        ("Telecom Hub X", "Fire Station 1"),
        ("Telecom Hub X", "Power Plant Alpha"), # Circular dependency (SCADA needs comms)
    ]
    G.add_edges_from(edges)
    return G

G = create_infrastructure_network()

# --- 2. Cascading Failure Logic ---
def simulate_cascade(graph, initial_failed_nodes):
    failed = set(initial_failed_nodes)
    new_failures = True
    
    while new_failures:
        new_failures = False
        for node in graph.nodes():
            if node not in failed:
                # If ANY incoming dependency fails, the node fails.
                incoming_edges = list(graph.in_edges(node))
                for source, target in incoming_edges:
                    if source in failed:
                        failed.add(node)
                        new_failures = True
                        break 
    return failed

# --- 3. UI Controls ---
st.sidebar.header("Simulation Controls")
nodes = list(G.nodes())
failed_nodes_input = st.sidebar.multiselect("Select Initial Failures:", nodes, default=[])

if st.sidebar.button("Run Simulation"):
    failed_nodes = simulate_cascade(G, failed_nodes_input)
else:
    failed_nodes = set(failed_nodes_input)

# --- 4. Visualization ---
def draw_graph(graph, failed_nodes):
    net = Network(height="600px", width="100%", bgcolor="#222222", font_color="white", directed=True)
    
    for node in graph.nodes():
        node_type = graph.nodes[node]['type']
        
        # Default colors
        color = "#97c2fc" 
        if node_type == "Power": color = "#ffcc00" 
        elif node_type == "Water": color = "#3399ff" 
        elif node_type == "Comm": color = "#cc99ff" 
        elif node_type == "Hospital" or node_type == "Emergency": color = "#ff9999" 
        elif node_type == "Public": color = "#a3a3a3"
        
        if node in failed_nodes:
            color = "#ff0000" # Bright red for failure
            label = f"FAILED: {node}"
        else:
            label = node
            
        net.add_node(node, label=label, color=color, title=node_type)
        
    for source, target in graph.edges():
        color = "#ff0000" if source in failed_nodes else "#ffffff"
        net.add_edge(source, target, color=color)
        
    net.set_options("""
    var options = {
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -50,
          "springLength": 100
        },
        "minVelocity": 0.75,
        "solver": "forceAtlas2Based"
      }
    }
    """)
    
    # Save to a temporary html file and display in streamlit
    html_file = "network.html"
    net.save_graph(html_file)
    with open(html_file, "r", encoding="utf-8") as f:
         html = f.read()
    components.html(html, height=620)
    
col1, col2 = st.columns([1, 3])
with col1:
    st.subheader("Network Status")
    st.write(f"Total Assets: {len(G.nodes())}")
    st.write(f"Failed Assets: {len(failed_nodes)}")
    
    if len(failed_nodes) > 0:
        st.error(f"System Degradation: {len(failed_nodes)/len(G.nodes())*100:.1f}%")
    else:
        st.success("System Normal")
        
    st.markdown("### Legend")
    st.markdown("🟨 Power  \n🟦 Water  \n🟪 Communications  \n🟥 Emergency/Hospital  \n🔴 **FAILED**")

with col2:
    draw_graph(G, failed_nodes)
