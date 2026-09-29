"""
Capacity Service — Ford-Fulkerson Max-Flow for EV Charging Network Analysis.

Builds a directed flow network:
    SOURCE  →  EV nodes  →  Station nodes  →  SINK

Edge capacities (all values are simulated/estimated — not real utility data):
    SOURCE  → EV:       demand_units  (EV charging demand)
    EV      → Station:  demand_units  (allowed assignment; Hungarian if provided)
    Station → SINK:     capacity_units (station's simulated serving capacity)

All capacity values are labelled "simulated_capacity" in responses.
"""
import logging
from typing import Any, Dict, List, Optional

from app.algorithms.ford_fulkerson import ford_fulkerson_max_flow
from app.graph.weighted_graph import WeightedGraph

logger = logging.getLogger(__name__)

# Virtual node identifiers — unlikely to collide with real node IDs
_SOURCE = "__SOURCE__"
_SINK = "__SINK__"

# Default simulated capacity per station (demand units) if none supplied
DEFAULT_STATION_CAPACITY = 5


class CapacityService:
    """
    Orchestrates Ford-Fulkerson max-flow analysis on the EV charging flow network.

    All capacity values are simulated/estimated for planning purposes.
    This service does NOT represent real electrical grid capacity,
    actual substation limits, real feeder capacity, or utility data.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze_capacity(
        self,
        evs: List[Dict[str, Any]],
        stations: List[Dict[str, Any]],
        assignments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze the maximum flow of EV charging demand through the station network.

        Parameters
        ----------
        evs:
            List of EV dicts, each with:
              - 'ev_id'        (str)
              - 'demand_units' (int, optional — defaults to 1)
        stations:
            List of station dicts, each with:
              - 'station_id'     (str)
              - 'capacity_units' (int, optional — defaults to DEFAULT_STATION_CAPACITY)
        assignments:
            Optional list of Hungarian assignment dicts, each with:
              - 'ev_id'      (str)
              - 'station_id' (str)
            If provided, only matched EV→Station edges are built.
            If None, every EV is connected to every station.

        Returns
        -------
        Dict with keys:
            algorithm, network_status, max_flow, total_demand,
            station_utilization, bottleneck_station_ids,
            flow_edges, note
        """
        if not evs:
            raise ValueError("At least one EV must be provided.")
        if not stations:
            raise ValueError("At least one station must be provided.")

        # Validate and normalise inputs
        ev_map = self._validate_evs(evs)
        station_map = self._validate_stations(stations)

        # Build directed flow graph
        graph = self._build_flow_graph(ev_map, station_map, assignments)

        # Run Edmonds-Karp max-flow
        ff_result = ford_fulkerson_max_flow(graph, source=_SOURCE, sink=_SINK)

        max_flow = ff_result["maximum_flow"]
        edge_flows = ff_result["edge_flows"]  # "u->v": flow

        # Compute per-station utilization
        total_demand = sum(d["demand_units"] for d in ev_map.values())
        station_utilization = self._compute_station_utilization(
            station_map, edge_flows
        )

        # Detect bottleneck stations (fully saturated)
        bottleneck_ids = [
            s["station_id"]
            for s in station_utilization
            if s["is_saturated"]
        ]

        # Determine network status
        network_status = self._determine_network_status(
            max_flow, total_demand, station_map
        )

        # Summarise flow edges (exclude source/sink virtual edges for clarity)
        flow_edges = self._extract_meaningful_flow_edges(edge_flows, ev_map, station_map)

        return {
            "algorithm": "ford_fulkerson_edmonds_karp",
            "network_status": network_status,
            "max_flow": max_flow,
            "total_demand": total_demand,
            "station_utilization": station_utilization,
            "bottleneck_station_ids": bottleneck_ids,
            "flow_edges": flow_edges,
            "note": (
                "All capacity values are simulated/estimated for planning purposes. "
                "This does not represent real electrical grid capacity, actual substation limits, "
                "real feeder capacity, real-time charging queue measurements, or actual utility data."
            ),
        }

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_evs(evs: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Validate EV inputs and return a keyed dict."""
        seen: set = set()
        result: Dict[str, Dict[str, Any]] = {}
        for ev in evs:
            ev_id = str(ev.get("ev_id", "")).strip()
            if not ev_id:
                raise ValueError("Each EV must have a non-empty 'ev_id'.")
            if ev_id in seen:
                raise ValueError(f"Duplicate ev_id: '{ev_id}'.")
            seen.add(ev_id)
            demand = int(ev.get("demand_units", 1))
            if demand <= 0:
                raise ValueError(f"EV '{ev_id}' demand_units must be >= 1.")
            result[ev_id] = {"ev_id": ev_id, "demand_units": demand}
        return result

    @staticmethod
    def _validate_stations(stations: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Validate station inputs and return a keyed dict."""
        seen: set = set()
        result: Dict[str, Dict[str, Any]] = {}
        for st in stations:
            st_id = str(st.get("station_id", "")).strip()
            if not st_id:
                raise ValueError("Each station must have a non-empty 'station_id'.")
            if st_id in seen:
                raise ValueError(f"Duplicate station_id: '{st_id}'.")
            seen.add(st_id)
            cap = int(st.get("capacity_units", DEFAULT_STATION_CAPACITY))
            if cap <= 0:
                raise ValueError(f"Station '{st_id}' capacity_units must be >= 1.")
            result[st_id] = {"station_id": st_id, "capacity_units": cap}
        return result

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------

    def _build_flow_graph(
        self,
        ev_map: Dict[str, Dict[str, Any]],
        station_map: Dict[str, Dict[str, Any]],
        assignments: Optional[List[Dict[str, Any]]],
    ) -> WeightedGraph:
        """
        Construct a directed flow network WeightedGraph.

        Topology:
            SOURCE → each EV  (capacity = EV demand_units)
            each EV → assigned stations  (capacity = EV demand_units)
            each Station → SINK  (capacity = station capacity_units)
        """
        graph = WeightedGraph(directed=True)

        # Add virtual source and sink
        graph.add_node(_SOURCE)
        graph.add_node(_SINK)

        # Add EV nodes + SOURCE→EV edges
        for ev_id, ev_data in ev_map.items():
            node_id = f"ev_{ev_id}"
            graph.add_node(node_id)
            graph.add_edge(
                _SOURCE,
                node_id,
                weight=float(ev_data["demand_units"]),
                capacity=float(ev_data["demand_units"]),
                directed=True,
            )

        # Add Station nodes + Station→SINK edges
        for st_id, st_data in station_map.items():
            node_id = f"st_{st_id}"
            graph.add_node(node_id)
            graph.add_edge(
                node_id,
                _SINK,
                weight=float(st_data["capacity_units"]),
                capacity=float(st_data["capacity_units"]),
                directed=True,
            )

        # EV→Station edges
        if assignments is not None:
            # Only build edges for assigned pairs
            for assignment in assignments:
                ev_id = str(assignment.get("ev_id", "")).strip()
                st_id = str(assignment.get("station_id", "")).strip()
                if ev_id not in ev_map:
                    logger.debug("Assignment ev_id '%s' not in EV list — skipping.", ev_id)
                    continue
                if st_id not in station_map:
                    logger.debug("Assignment station_id '%s' not in station list — skipping.", st_id)
                    continue
                demand = float(ev_map[ev_id]["demand_units"])
                graph.add_edge(
                    f"ev_{ev_id}",
                    f"st_{st_id}",
                    weight=demand,
                    capacity=demand,
                    directed=True,
                )
        else:
            # Full bipartite: every EV to every station
            for ev_id, ev_data in ev_map.items():
                for st_id in station_map:
                    graph.add_edge(
                        f"ev_{ev_id}",
                        f"st_{st_id}",
                        weight=float(ev_data["demand_units"]),
                        capacity=float(ev_data["demand_units"]),
                        directed=True,
                    )

        return graph

    # ------------------------------------------------------------------
    # Post-processing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_station_utilization(
        station_map: Dict[str, Dict[str, Any]],
        edge_flows: Dict[str, float],
    ) -> List[Dict[str, Any]]:
        """
        For each station, determine how much flow reaches it (Station→SINK flow).
        """
        utilization = []
        for st_id, st_data in station_map.items():
            node_id = f"st_{st_id}"
            # The Station→SINK edge carries the utilized flow
            key = f"{node_id}->{_SINK}"
            utilized = edge_flows.get(key, 0.0)
            available = float(st_data["capacity_units"])
            is_saturated = utilized >= available - 1e-9 and available > 0

            utilization.append({
                "station_id": st_id,
                "available_capacity": available,
                "utilized_capacity": utilized,
                "unused_capacity": max(0.0, available - utilized),
                "utilization_pct": round((utilized / available * 100) if available > 0 else 0.0, 2),
                "is_saturated": is_saturated,
                "simulated_capacity": True,
            })
        return utilization

    @staticmethod
    def _determine_network_status(
        max_flow: float,
        total_demand: float,
        station_map: Dict[str, Dict[str, Any]],
    ) -> str:
        """
        Determine network status string.

        Returns one of:
            "fully_satisfied"    — max_flow == total_demand
            "capacity_limited"   — max_flow < total_demand
            "capacity_available" — demand satisfied AND unused station capacity remains
        """
        total_station_capacity = sum(
            d["capacity_units"] for d in station_map.values()
        )
        demand_met = abs(max_flow - total_demand) < 1e-9

        if not demand_met:
            return "capacity_limited"
        # Demand fully met — check if there is remaining station capacity
        if total_station_capacity > total_demand:
            return "capacity_available"
        return "fully_satisfied"

    @staticmethod
    def _extract_meaningful_flow_edges(
        edge_flows: Dict[str, float],
        ev_map: Dict[str, Dict[str, Any]],
        station_map: Dict[str, Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Return only EV→Station flow edges (strip virtual SOURCE/SINK edges).
        """
        ev_prefixes = {f"ev_{ev_id}" for ev_id in ev_map}
        st_prefixes = {f"st_{st_id}" for st_id in station_map}

        result = []
        for edge_key, flow in edge_flows.items():
            if "->" not in edge_key:
                continue
            u, v = edge_key.split("->", 1)
            if u in ev_prefixes and v in st_prefixes:
                result.append({
                    "from_ev_id": u[3:],   # strip "ev_" prefix
                    "to_station_id": v[3:],  # strip "st_" prefix
                    "flow_units": round(flow, 6),
                })
        return result


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_capacity_service_instance: Optional[CapacityService] = None


def get_capacity_service() -> CapacityService:
    """Return the shared CapacityService singleton."""
    global _capacity_service_instance
    if _capacity_service_instance is None:
        _capacity_service_instance = CapacityService()
    return _capacity_service_instance
