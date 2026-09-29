# Graph-Based EV Charging Station Optimization

An optimization platform integrating graph algorithms, GIS geospatial analysis, and real-time navigation to optimize electric vehicle (EV) charging station placement, power grid transmission lines, vehicle-to-charger bipartite matching, and shortest path navigation with live user GPS tracking.

---

## Current Implementation Status

- **Phase 1 (Backend Foundation & Core Graph Algorithms)**: **COMPLETE**
  - Custom `WeightedGraph` representation (Adjacency List, coordinate storage, Haversine distance weighting)
  - Dijkstra's Algorithm for single-source shortest path routing
  - Minimum Dominating Set (MDS) Greedy Approximation for strategic station placement
  - Prim's Minimum Spanning Tree (MST) for minimal electrical grid infrastructure layout
  - Kuhn-Munkres (Hungarian) Algorithm for optimal bipartite EV-to-charger slot allocation
  - Ford-Fulkerson (Edmonds-Karp BFS) for maximum power flow and min-cut bottleneck detection
- **Phase 2 (GIS / OSM Ingestion + Spatial Snapping)**: **COMPLETE**
  - Overpass API road-network ingestion with configurable bounding boxes
  - Local JSON network caching and offline sample network fallback
  - GPS coordinate validation (rejecting NaN, Inf, non-numeric, out-of-bounds)
  - Nearest-road-node spatial snapping via Haversine distance
  - Candidate EV charging station generation, feasibility scoring, and filtering
- **Phase 3 (Backend REST API + Live GPS Routing Integration)**: **COMPLETE**
  - FastAPI REST service with automated OpenAPI / Swagger documentation (`/docs`)
  - Live GPS routing pipeline integrating validation → snapping → station selection → Dijkstra shortest path
  - Feasible charging station selection based on shortest graph distance
  - Privacy-preserving request-time GPS handling (no storage, no logging of coordinates)
  - 128 automated unit and integration tests passing
- **Phase 4 (Web Frontend + Live GPS + Interactive Map)**: **COMPLETE**
  - Modern, responsive single-page application built with React, Vite, TypeScript, and Tailwind CSS
  - Interactive Leaflet map (`react-leaflet`) with OpenStreetMap tiles
  - Live GPS location retrieval via Browser Geolocation API
  - "Use My Location" action triggering full end-to-end routing pipeline
  - Real-time route polyline rendering, station markers, distance, and estimated travel time
  - Clean error and loading feedback states with privacy protection
- **Phase 5A (MDS-Based Optimal EV Charging Station Placement)**: **COMPLETE**
  - Greedy Minimum Dominating Set optimization service mapping feasible candidates to road graph coverage
  - REST endpoint `POST /api/optimize/dominating-set` supporting configurable coverage radius and feasibility thresholds
  - Frontend "Optimize Charging Stations" button rendering coverage-oriented station markers and coverage statistics
  - 143 automated unit, integration, and API tests passing
- **Phase 5B (Hungarian EV-to-Station Assignment)**: **COMPLETE**
  - Kuhn-Munkres (Hungarian) optimal bipartite matching service connecting EVs to MDS-selected charging stations
  - Automated cost matrix generation supporting network distance via Dijkstra shortest paths with geodesic Haversine fallback
  - REST endpoint `POST /api/optimize/assignment` supporting rectangular matrices, unassigned EV tracking, and unassigned station reporting
  - Frontend "Assign EVs to Stations" controls, orange dashed matching polylines, and detailed matching summary metrics
  - 164 automated unit, integration, and API tests passing
- **Phase 5C (Prim MST Infrastructure Optimization)**: **COMPLETE**
  - Prim's Minimum Spanning Tree (MST) service estimating the minimum spanning infrastructure connection network between selected charging stations
  - Direct pairwise shortest path routing across the road network graph via Dijkstra with geodesic Haversine fallback
  - REST endpoint `POST /api/optimize/infrastructure` resolving selected MDS stations, tracking connected/unconnected station components without fabricating artificial edges
  - Frontend "Optimize Infrastructure" controls, teal dashed infrastructure connection polylines with interactive popups, and comprehensive distance metrics
  - 185 automated unit, integration, and API tests passing
- **Phase 6 (Ford-Fulkerson Max-Flow Capacity & Bottleneck Analysis)**: **COMPLETE**
  - Ford-Fulkerson Edmonds-Karp max-flow service building a directed flow network `SOURCE → EVs → Stations → SINK` with simulated capacity edges
  - Detects bottleneck stations (saturated flow), computes per-station simulated utilization, and classifies network status as `fully_satisfied`, `capacity_limited`, or `capacity_available`
  - REST endpoint `POST /api/optimize/capacity` accepting EV demand, station capacity, and optional Hungarian assignment constraints
  - Frontend "Analyze Charging Capacity" button (violet), result card with network status badge, per-station utilization breakdown, bottleneck indicator, and flow summary
  - Station map popups enriched with simulated capacity utilization data when Phase 6 analysis is active
  - All capacity values explicitly labelled as simulated/estimated — not real electrical grid capacity, actual substation limits, real feeder capacity, or utility data
  - 219 automated unit, integration, and API tests passing
- **Phase 7 (Integration, OSM Reliability & Final Validation)**: **COMPLETE**
  - Robust Overpass API integration with RFC-compliant `User-Agent` and `Accept` headers, exponential backoff retry on HTTP 429/5xx, and environment-configurable `OVERPASS_URL`.
  - Transparent 3-tier road network provenance (`osm` → `cache` → `sample` offline fallback), surfaced explicitly in API schemas and UI badges.
  - User-friendly error categorization distinguishing out-of-coverage GPS locations, disconnected road graphs, and missing feasible stations.
  - End-to-end pipeline integration test suite validating sequential algorithmic handoffs: GPS Snapping → Dijkstra → Candidate Generation → Greedy MDS → Hungarian Matching → Prim MST → Ford-Fulkerson Max-Flow.
  - UI honesty enhancements: greedy MDS labeling, network source indicators, and explicit planning disclaimers.
  - Privacy review confirmed: zero persistent GPS storage, zero database writes, no cookies, no `watchPosition`.
  - 242 automated unit, integration, and end-to-end pipeline tests passing.

---

## Web Frontend (Phase 4)

The user-facing website allows EV drivers to locate the nearest feasible charging station and obtain turn-by-turn road network routes calculated by the backend Dijkstra engine using their device's live GPS coordinates.

### Frontend Technology Stack
- **Framework**: React 18 + Vite + TypeScript
- **Styling**: Tailwind CSS (fully responsive desktop and mobile layout)
- **Mapping**: Leaflet 1.9 + React Leaflet 4.2 (OpenStreetMap vector tiles)
- **Icons**: Lucide React
- **Geolocation**: Browser Geolocation API (`navigator.geolocation.getCurrentPosition()`)

### User Workflow
1. User opens the application and views the interactive map.
2. User clicks **"Use My Location"**.
3. Browser requests location access permission.
4. User's location is identified and marked on the map with a distinctive blue pinpoint.
5. The frontend transmits the coordinates to `POST /api/route/live`.
6. The FastAPI backend validates coordinates, snaps them to the nearest road vertex, selects the closest feasible charging station, and computes the Dijkstra shortest path.
7. The map smoothly fits bounds to display the calculated route polyline, user origin, and charging station marker with detailed travel metrics (distance and estimated travel time).

> **Note on Browser Permissions**: The browser will request location permission upon clicking "Use My Location". If permission is denied or geolocation is unavailable, the UI presents a clear, user-friendly notice with an option to retry or test with simulated coordinates.

---

## REST API Endpoints (Phase 3)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Root service health status |
| `GET` | `/api/health` | Service operational health and version status (`{"status": "ok", "version": "0.3.0"}`) |
| `GET` | `/api/gis/network` | Road network metadata (`node_count`, `edge_count`, `data_source`) |
| `POST` | `/api/route/live` | Live GPS route calculation to the nearest feasible EV charging station |
| `POST` | `/api/optimize/dominating-set` | Greedy MDS calculation for network-wide optimal EV charging station placement |
| `POST` | `/api/optimize/assignment` | Kuhn-Munkres (Hungarian) minimum-cost bipartite EV-to-station assignment |
| `POST` | `/api/optimize/infrastructure` | Prim's Minimum Spanning Tree (MST) for EV station infrastructure connection network |
| `POST` | `/api/optimize/capacity` | Ford-Fulkerson Edmonds-Karp max-flow: simulated EV charging capacity and bottleneck analysis |
| `GET` | `/docs` | Interactive Swagger UI API documentation |
| `GET` | `/openapi.json` | OpenAPI 3.1 JSON specification |

---

## EV-to-Station Bipartite Assignment (Phase 5B)

The assignment layer connects multiple electric vehicles to charging stations selected by the Minimum Dominating Set (MDS) layer.

```
Live GPS / EV Locations
        ↓
MDS Selected Stations
        ↓
Cost Matrix (N EVs × M Stations)
        ↓
Hungarian Algorithm (Kuhn-Munkres)
        ↓
EV → Station Assignments
```

### Separation of Responsibilities: MDS vs. Hungarian
- **Minimum Dominating Set (MDS)**: Determines a strategic, coverage-oriented set of charging stations across the road network topology.
- **Hungarian Algorithm**: Solves the linear sum assignment problem to pair specific vehicles with available stations while minimizing total network assignment distance. Hungarian does **not** select stations independently; it assigns to the stations nominated by MDS (or supplied via station IDs).

### Cost Matrix & Metric
- **Rows**: Electric Vehicles ($N$)
- **Columns**: MDS-Selected Charging Stations ($M$)
- **Primary Metric (`network_distance_km`)**: Shortest road-network distance calculated via Dijkstra's algorithm between each vehicle's snapped road vertex and the station's vertex.
- **Explicit Fallback (`geographic_distance_km`)**: If vehicle snapping is not possible or the road graph is disconnected, geodesic Haversine distance is used uniformly across the entire cost matrix to avoid unit mixing.

### Rectangular Matrices & Unassigned Vehicles
- When the number of vehicles exceeds available station slots ($N > M$), the Hungarian algorithm assigns all $M$ slots to the $M$ vehicles that minimize total cost, reporting the remaining $N - M$ vehicles in `unassigned_ev_ids`.
- When available stations exceed vehicles ($M > N$), all reachable vehicles are matched, and unused stations are reported in `unassigned_station_ids`.
- Unreachable EV-station pairings on disconnected graph components are penalized and excluded rather than forced.

### Algorithm Transparency & Limitations
- The Hungarian algorithm provides an exact mathematical optimum for the **supplied cost matrix**.
- It does not model dynamic traffic conditions, station queue wait times, or grid load fluctuations.

### Privacy & Ephemeral Location Handling
- **Zero Permanent Storage**: User GPS coordinates are processed exclusively in memory during the request lifecycle.
- **Zero Coordinate Logging**: Server logs record only the snapped road node ID and distance; raw latitude/longitude coordinates are never logged.
- **No Location Tracking**: Geolocation uses one-shot position queries; continuous background tracking (`watchPosition`) is disabled.

---

## EV Charging Infrastructure Expansion via Prim's MST (Phase 5C)

The infrastructure expansion layer computes the minimum spanning infrastructure connection network between selected EV charging stations.

### Architecture & Algorithm Coordination

```
                    EV Locations
                         │
                         ▼
                       MDS
                         │
                 Selected Stations
                         │
             ┌───────────┴───────────┐
             ▼                       ▼
        Hungarian                   Prim
             │                       │
      EV → Station             Station Network
       Assignment              Infrastructure
                                  Distance
```

### Purpose of Prim MST
While **MDS** determines which candidate sites to activate for optimal urban coverage and **Hungarian** matches vehicles to active charging slots, **Prim's Algorithm** calculates the minimum-distance spanning backbone required to interconnect the selected stations (e.g., for power line conduit routing, telemetry, and communications along existing road corridors).

> **Important Distinction**: Prim MST does **not** select charging stations. It operates strictly on the charging stations already selected by MDS (or supplied via station IDs).

### Infrastructure Cost Metric
- **Primary Metric (`network_distance_km`)**: The edge weight between any two stations corresponds to the shortest path distance in kilometers along the physical road network graph, computed using Dijkstra's algorithm.
- **Fallback Metric (`geographic_distance_km`)**: If the road network is unavailable or disconnected, geodesic Haversine distance in kilometers is applied uniformly across the station graph.
- **Metric Integrity**: Prim minimizes **total network connection distance**, not financial construction costs. Unless an empirically validated monetary cost model is provided, values are reported strictly as connection distance in kilometers.

### API Endpoint (`POST /api/optimize/infrastructure`)
- **Request**: Accepts an array of selected `station_ids` (or resolves them dynamically via MDS if omitted).
- **Response**: Returns:
  - `algorithm`: `"prim_mst"`
  - `cost_metric`: `"network_distance_km"`
  - `station_count` and `connected_station_count`
  - `mst_edge_count` and `total_cost_km`
  - `stations`: Evaluated station candidate metadata and connectivity status
  - `edges`: Array of MST connection edges with `from_station_id`, `to_station_id`, `cost_km`, and full road `path_coordinates`
  - `connected_station_ids` and `unconnected_station_ids`

### Disconnected Graph Handling
- The backend does **not** fabricate artificial zero-cost or infinite-cost edges between disconnected components.
- If two stations cannot be reached along the available road network, Prim's algorithm spans only the reachable component and honestly reports unreachable stations in `unconnected_station_ids`.
- For single-station inputs ($N=1$), total infrastructure distance is $0.0\text{ km}$ with $0$ edges.
- For empty station inputs ($N=0$), an empty result structure is returned cleanly.

### Limitations
- Models physical connection distance along road corridors; does not incorporate terrain slope, right-of-way easement fees, or underground electrical cable installation costs.
- Does not enforce power substation capacity limits (which will be addressed by Ford-Fulkerson in Phase 6).

---

## EV Charging Capacity & Bottleneck Analysis via Ford-Fulkerson (Phase 6)

The capacity analysis layer computes the maximum simulated flow of EV charging demand through the station network using the Ford-Fulkerson Edmonds-Karp algorithm.

> ⚠️ **All capacity values are simulated/estimated for planning purposes.** This layer does **not** represent real electrical grid capacity, actual substation limits, real feeder capacity, real-time charging queue measurements, or actual utility data.

### Flow Network Model

```
SOURCE  ──(demand_units)──►  EV₁  ──(demand_units)──►  Station_A  ──(capacity_units)──►  SINK
                          ►  EV₂  ──(demand_units)──►  Station_B  ──(capacity_units)──►
                          ►  EV₃
```

- **SOURCE → EV**: Edge capacity = EV's `demand_units` (simulated load)
- **EV → Station**: Edge capacity = EV `demand_units` if the EV is assigned to that station (from Hungarian results if supplied); otherwise all-pairs bipartite
- **Station → SINK**: Edge capacity = station's `capacity_units` (simulated serving capacity)

### Network Status Classification

| Status | Meaning |
|---|---|
| `fully_satisfied` | `max_flow == total_demand` with exactly zero spare station capacity |
| `capacity_available` | Demand fully met with remaining unused station capacity |
| `capacity_limited` | `max_flow < total_demand` — network cannot absorb all EV demand |

### Bottleneck Detection

A station is classified as **saturated** (a bottleneck) when its simulated utilized flow equals or exceeds its simulated capacity. `bottleneck_station_ids` lists all such stations.

### API Endpoint (`POST /api/optimize/capacity`)
- **Request**: Accepts lists of EVs (with `ev_id`, `demand_units`) and stations (with `station_id`, `capacity_units`), and an optional `assignments` array from Hungarian results.
- **Response**: Returns `algorithm`, `network_status`, `max_flow`, `total_demand`, `station_utilization` (per-station), `bottleneck_station_ids`, `flow_edges`, and a `note` disclaimer.

---

---

## End-to-End System Architecture

The platform coordinates five core graph algorithms across sequential stages of EV charging infrastructure planning and live driver navigation:

```
    LIVE USER LOCATION (Browser GPS)
                  │
                  ▼
          ROAD NETWORK / OSM
       (osm / cache / sample)
                  │
                  ▼
               DIJKSTRA
         (Shortest Path Routing)
                  │
                  ▼
         STATION CANDIDATES
       (Multi-Criteria Feasibility)
                  │
                  ▼
                 MDS
      (Greedy Coverage Placement)
                  │
          SELECTED STATIONS
             ↙          ↘
       HUNGARIAN       PRIM MST
      (EV Slot      (Infrastructure
     Assignment)      Connection)
             ↘          ↙
             CAPACITY MODEL
                  │
                  ▼
            FORD-FULKERSON
          (Edmonds-Karp BFS)
                  │
                  ▼
     MAX FLOW / BOTTLENECK ANALYSIS
```

---

## Implemented Core Algorithms & Theoretical Complexity

Each algorithm in the repository was inspected and verified against the actual Python implementation:

| Algorithm | Implementation File | Strategy / Data Structure | Time Complexity | Space Complexity | Notes / Approximation |
|---|---|---|---|---|---|
| **Dijkstra Shortest Path** | `app/algorithms/dijkstra.py` | Min-heap via Python `heapq` | $\mathcal{O}((V + E) \log V)$ | $\mathcal{O}(V + E)$ | Exact single-source shortest path with settled-set optimization |
| **Greedy Minimum Dominating Set** | `app/algorithms/dominating_set.py` | Bounded Dijkstra + Greedy Set Cover | $\mathcal{O}(C(V + E) \log V + k C D)$ | $\mathcal{O}(C D + V + E)$ | Greedy approximation with harmonic bound $H(\Delta) \le \ln \Delta + 1 = \mathcal{O}(\ln \|V\|)$ |
| **Hungarian Algorithm** | `app/algorithms/hungarian.py` | Kuhn-Munkres state machine with matrix zero-padding | $\mathcal{O}(\max(N, M)^4)$ | $\mathcal{O}(\max(N, M)^2)$ | Exact minimum-weight bipartite matching for arbitrary $N \times M$ rectangular cost matrices |
| **Prim Minimum Spanning Tree** | `app/algorithms/prim.py` | Min-priority queue edge relaxation | $\mathcal{O}(E \log V)$ | $\mathcal{O}(V + E)$ | Exact MST on connected component; cleanly tracks unreachable nodes |
| **Ford-Fulkerson Max Flow** | `app/algorithms/ford_fulkerson.py` | Edmonds-Karp BFS via `collections.deque` | $\mathcal{O}(V \cdot E^2)$ | $\mathcal{O}(V + E)$ | Exact max-flow and residual $S-T$ cut saturated bottleneck edge extraction |

### Detailed Algorithm Descriptions

1. **Dijkstra's Algorithm (`dijkstra_shortest_path`)**:
   - Computes turn-by-turn road paths from snapped GPS coordinates to charging candidates.
   - Halts immediately when the target vertex is popped from the min-heap.
   - Predecessor backtracking constructs the ordered node list and geographical coordinate polyline in $\mathcal{O}(V)$.

2. **Minimum Dominating Set (`minimum_dominating_set`)**:
   - Reduces the distance-constrained station placement problem to Greedy Set Cover.
   - Precomputes candidate coverage areas using bounded Dijkstra searches within `coverage_radius_km`.
   - Iteratively selects the candidate covering the largest number of uncovered network demand nodes until coverage criteria are satisfied.
   - **Theoretical Guarantee**: Polynomial-time greedy heuristic providing an $\mathcal{O}(\ln |V|)$ approximation factor for an NP-hard problem.

3. **Hungarian Algorithm (`hungarian_algorithm`)**:
   - Solves the linear sum assignment problem matching $N$ electric vehicles to $M$ charging stations.
   - Automatically pads rectangular matrices with dummy zero-cost rows/columns to handle supply/demand imbalances without loss of optimality.
   - Dual variable adjustment and augmenting path traversal ensures globally minimal assignment distance.

4. **Prim's Algorithm (`prim_mst`)**:
   - Estimates the minimal transmission corridor or conduit distance required to interconnect active charging stations along existing road corridors.
   - Handles disconnected network topologies gracefully by computing the MST for the primary component and explicitly enumerating unreachable stations.
   - Reports physical road network distance in kilometers rather than fictitious currency amounts.

5. **Ford-Fulkerson / Edmonds-Karp (`ford_fulkerson_max_flow`)**:
   - Constructs a directed flow graph: `__SOURCE__` $\to$ EVs $\to$ Stations $\to$ `__SINK__`.
   - Finds augmenting paths using Breadth-First Search (Edmonds-Karp), guaranteeing termination in $\mathcal{O}(V \cdot E^2)$ operations even with non-integer capacities.
   - Identifies saturated transmission bottlenecks across the minimum $S-T$ cut.

---

## Technical Honesty & Modeling Disclaimers

The platform maintains strict distinction between real-world measurements and optimization models:

- **Live User Location**: Retrieved ephemerally via browser Geolocation API (`getCurrentPosition`) at request time. No location tracking, no GPS history, no database writes, no cookies, and no `localStorage` persistence.
- **Road Network Provenance**: Clearly labeled as `osm` (live Overpass download), `cache` (locally cached OSM geometry), or `sample` (deterministic 15-node offline fallback).
- **MDS Station Optimization**: Explicitly designated as a **Greedy Set-Cover Approximation**, not a mathematically guaranteed global minimum.
- **Estimated Travel Time (ETA)**: Calculated using a fixed average speed ($40\text{ km/h}$) across road distances; does **not** model dynamic real-time traffic congestion.
- **Feasibility Scores**: Multi-criteria weighted ratings ($0.0 - 1.0$) based on topological accessibility, estimated land availability, and simulated grid proximity; not physical engineering or title surveys.
- **Charging Station Capacity**: Modeled in discrete planning units ($1$ demand unit per vehicle, $3-5$ capacity units per station); does **not** represent real electrical grid feeder ampacity, substation transformer ratings, or utility queue measurements.

---

## Setup & Running the Project

### Prerequisites
- Python 3.10+ (tested on Python 3.13.5)
- Node.js 18+ & npm (tested on Node v20.19.2)

### 1. Backend Setup & Startup
```bash
# From repository root
cd backend
source ../.venv/bin/activate
pip install -r requirements.txt

# Run ground-truth tests (242 tests)
pytest -q


# Start backend server
uvicorn app.main:app --reload --port 8000
```
Backend will be active at:
- API Root: `http://127.0.0.1:8000/`
- Swagger UI Docs: `http://127.0.0.1:8000/docs`

### 2. Frontend Setup & Startup
In a separate terminal:
```bash
# From repository root
cd frontend
npm install

# Build for production verification
npm run build

# Start local development server
npm run dev
```
Frontend will be active at:
- Web App: `http://localhost:5173/`