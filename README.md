# Graph-Based EV Charging Station Optimization

An optimization platform integrating graph algorithms, GIS geospatial analysis, and real-time navigation to optimize electric vehicle (EV) charging station placement, power grid transmission lines, vehicle-to-charger bipartite matching, and shortest path navigation with live user GPS tracking.

---

## Current Implementation Status (Phase 1 Completed)

- **Phase 1 (Backend Foundation & Core Graph Algorithms)**: **COMPLETE**
  - Custom `WeightedGraph` representation (Adjacency List, coordinate storage, Haversine distance weighting)
  - Dijkstra's Algorithm for single-source shortest path routing
  - Minimum Dominating Set (MDS) Greedy Approximation for strategic station placement
  - Prim's Minimum Spanning Tree (MST) for minimal electrical grid infrastructure layout
  - Kuhn-Munkres (Hungarian) Algorithm for optimal bipartite EV-to-charger slot allocation
  - Ford-Fulkerson (Edmonds-Karp BFS) for maximum power flow and min-cut bottleneck detection
  - Full automated test suite (48 tests passing)
  - Baseline FastAPI service exposing `GET /`
- **Future Phases**:
  - Phase 2: GIS Ingestion, OpenStreetMap (OSM) Overpass API, and Live GPS Coordinate Snapping
  - Phase 3: RESTful Optimization API Endpoints
  - Phase 4: Frontend Development (React + Leaflet + Live GPS Tracking + Dashboard)
  - Phase 5: Verification & End-to-End Integration

---

## Implemented Core Algorithms

1. **Weighted Road Network Graph (`WeightedGraph`)**:
   - Adjacency list representation \(G = (V, E, W)\).
   - Supports geographical coordinate tracking (latitude/longitude), directed and undirected topologies, and automatic Haversine edge distance calculation.
2. **Dijkstra's Algorithm (`dijkstra_shortest_path`)**:
   - Min-priority queue implementation finding exact shortest path, distance, predecessor chain, and visited node logs.
3. **Minimum Dominating Set (`minimum_dominating_set`)**:
   - Practical station-placement strategy using a **greedy set-cover approximation** over graph distance within a specified coverage radius.
   > **Note**: MDS currently uses a greedy approximation rather than an exact exponential solver, providing an $O(\ln |V|)$ approximation suitable for large-scale urban road networks.
4. **Prim's Minimum Spanning Tree (`prim_mst`)**:
   - Priority-queue Prim's algorithm computing the minimum-cost cable/interconnection backbone connecting charging stations and power distribution hubs.
5. **Hungarian Algorithm (`hungarian_algorithm`)**:
   - Kuhn-Munkres $O(n^3)$ optimal bipartite matching for square and rectangular cost matrices (e.g., $N$ EV charging requests matched to $M$ charging slots).
6. **Ford-Fulkerson Maximum Flow / Minimum Cut (`ford_fulkerson_max_flow`)**:
   - Edmonds-Karp BFS implementation computing network maximum power flow capacity and identifying critical saturated bottleneck transmission lines via Min-Cut.

---

## Backend Setup & Installation

### Prerequisites
- Python 3.10+ (tested on Python 3.13.5)

### 1. Create Virtual Environment
```bash
python3 -m venv .venv
```

### 2. Activate Virtual Environment
On Linux / macOS:
```bash
source .venv/bin/activate
```
On Windows:
```cmd
.venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r backend/requirements.txt
```

### 4. Running Tests
Run the comprehensive ground-truth test suite:
```bash
cd backend
pytest
```

### 5. Running Backend Server
```bash
cd backend
uvicorn app.main:app --reload
```
The API will be available at `http://127.0.0.1:8000/`.

---

## Algorithm Demonstration Script
To execute a standalone manual verification of all Phase 1 algorithms:
```bash
cd backend
python demo.py
```