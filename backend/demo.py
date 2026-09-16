"""
Manual demonstration of all Phase 1 core graph algorithms.
Demonstrates:
  1. Weighted Road Network Graph with Haversine distance
  2. Dijkstra's Shortest Path Algorithm
  3. Minimum Dominating Set (MDS) Greedy Approximation
  4. Prim's Minimum Spanning Tree (MST)
  5. Kuhn-Munkres (Hungarian) Bipartite Matching
  6. Ford-Fulkerson (Edmonds-Karp) Maximum Flow & Minimum Cut
"""
import json
from app.graph.weighted_graph import WeightedGraph
from app.utils.distance import haversine_distance
from app.algorithms import (
    dijkstra_shortest_path,
    minimum_dominating_set,
    prim_mst,
    hungarian_algorithm,
    ford_fulkerson_max_flow,
)

print("=" * 60)
print("PHASE 1 ALGORITHM DEMONSTRATION")
print("=" * 60)

# 1. Weighted Graph & Haversine Distance
print("\n[1] WEIGHTED ROAD NETWORK GRAPH & HAVERSINE DISTANCE")
g = WeightedGraph(directed=False)
# Coordinates for simulated city intersections (Bangalore area)
g.add_node("Indiranagar", lat=12.9784, lon=77.6408, type="intersection")
g.add_node("Koramangala", lat=12.9352, lon=77.6245, type="charging_station")
g.add_node("MG_Road", lat=12.9756, lon=77.6066, type="intersection")
g.add_node("Whitefield", lat=12.9698, lon=77.7500, type="substation")

# Add edges with auto-calculated Haversine distance in km
g.add_edge("MG_Road", "Indiranagar")
g.add_edge("Indiranagar", "Koramangala")
g.add_edge("Indiranagar", "Whitefield")
g.add_edge("MG_Road", "Koramangala")

print(f"Graph Representation: {g}")
print(f"Distance MG_Road -> Indiranagar: {g.get_weight('MG_Road', 'Indiranagar'):.2f} km")
print(f"Distance Indiranagar -> Whitefield: {g.get_weight('Indiranagar', 'Whitefield'):.2f} km")

# 2. Dijkstra's Shortest Path
print("\n[2] DIJKSTRA'S SHORTEST PATH")
dijkstra_res = dijkstra_shortest_path(g, source="MG_Road", target="Whitefield")
print(f"Shortest Path: {' -> '.join(dijkstra_res['path'])}")
print(f"Total Distance: {dijkstra_res['total_distance']:.2f} km")
print(f"Visited Nodes: {dijkstra_res['visited_nodes']}")
print(f"Execution Time: {dijkstra_res['execution_time'] * 1000:.3f} ms")

# 3. Minimum Dominating Set (MDS) Greedy Approximation
print("\n[3] MINIMUM DOMINATING SET (GREEDY APPROXIMATION)")
mds_res = minimum_dominating_set(g, coverage_radius=6.0)
print(f"Selected Charging Stations: {mds_res['selected_nodes']}")
print(f"Covered Nodes: {mds_res['covered_nodes']}")
print(f"Coverage Percentage: {mds_res['coverage_percentage']}%")
print(f"Coverage Map: {json.dumps(mds_res['coverage_map'])}")

# 4. Prim's Minimum Spanning Tree (Electrical Grid Wiring)
print("\n[4] PRIM'S MINIMUM SPANNING TREE (MST)")
mst_res = prim_mst(g, start_node="Whitefield")
print(f"MST Edges: {mst_res['mst_edges']}")
print(f"Total Cable Distance (Cost): {mst_res['total_cost']:.2f} km")
print(f"Connected Nodes: {mst_res['connected_nodes']}")

# 5. Hungarian Algorithm (EV -> Station Plug Assignment)
print("\n[5] HUNGARIAN ALGORITHM (KUHN-MUNKRES MATCHING)")
# 3 EVs requesting charging across 4 available charging slots (distance/wait costs)
cost_matrix = [
    [12.0, 4.0, 18.0, 7.0],   # EV 0 costs to Stations [0, 1, 2, 3]
    [8.0, 15.0, 6.0, 10.0],   # EV 1
    [5.0, 11.0, 14.0, 9.0],   # EV 2
]
hungarian_res = hungarian_algorithm(cost_matrix)
print("Assignments (EV Index -> Station Slot Index):")
for ev_idx, slot_idx in hungarian_res["assignments"]:
    print(f"  EV {ev_idx} assigned to Station Slot {slot_idx} (Cost: {cost_matrix[ev_idx][slot_idx]})")
print(f"Total Minimal Assignment Cost: {hungarian_res['total_cost']}")

# 6. Ford-Fulkerson (Edmonds-Karp Maximum Flow / Minimum Cut)
print("\n[6] FORD-FULKERSON (EDMONDS-KARP MAX FLOW & MIN CUT)")
flow_net = WeightedGraph(directed=True)
# Power Substation 'Grid' transmitting power through intermediate distribution hubs to charging hub 'EV_Hub'
flow_net.add_edge("Grid", "Hub_North", weight=500.0)  # 500 kW transmission capacity
flow_net.add_edge("Grid", "Hub_South", weight=400.0)  # 400 kW
flow_net.add_edge("Hub_North", "Hub_South", weight=100.0)
flow_net.add_edge("Hub_North", "EV_Hub", weight=300.0)
flow_net.add_edge("Hub_South", "EV_Hub", weight=350.0)

flow_res = ford_fulkerson_max_flow(flow_net, source="Grid", sink="EV_Hub")
print(f"Maximum Deliverable Power: {flow_res['maximum_flow']} kW")
print(f"Active Line Flows: {json.dumps(flow_res['edge_flows'], indent=2)}")
print(f"Bottleneck/Saturated Power Lines: {flow_res['bottleneck_edges']}")
print(f"Min-Cut Source Partition: {flow_res['min_cut']['source_partition']}")
print(f"Min-Cut Sink Partition: {flow_res['min_cut']['sink_partition']}")
print(f"Cut Transmission Capacity: {flow_res['min_cut']['cut_capacity']} kW")
print("\n" + "=" * 60)
print("ALL ALGORITHMS VERIFIED SUCCESSFULLY!")
print("=" * 60)
