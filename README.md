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
- **Future Phases**:
  - Phase 5B+: Prim's MST grid design, Hungarian matching, and Ford-Fulkerson max-flow integrations

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
| `GET` | `/docs` | Interactive Swagger UI API documentation |
| `GET` | `/openapi.json` | OpenAPI 3.1 JSON specification |

### Privacy & Ephemeral Location Handling
- **Zero Permanent Storage**: User GPS coordinates are processed exclusively in memory during the request lifecycle.
- **Zero Coordinate Logging**: Server logs record only the snapped road node ID and distance; raw latitude/longitude coordinates are never logged.
- **No Location Tracking**: Geolocation uses one-shot position queries; continuous background tracking (`watchPosition`) is disabled.

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

# Run ground-truth tests (128 tests)
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