"""Graph Service — loads T.Nagar GeoJSON into in-memory NetworkX graph; exposes queries.

The graph is loaded once at startup (lifespan) and held in memory.
All simulation requests read from this shared read-model.
"""
from __future__ import annotations

import json
import logging
import math
import random
from pathlib import Path
from typing import Any, Optional

import networkx as nx

from app.config import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level singleton (populated by load_graph())
# ---------------------------------------------------------------------------
_G: Optional[nx.MultiDiGraph] = None
_nodes_geojson: Optional[dict] = None
_edges_geojson: Optional[dict] = None
_intervention_catalog: Optional[list[dict]] = None

# Low-lying elevation threshold for T.Nagar (metres above MSL)
# T.Nagar is ~6–14 m above MSL; nodes below this are flood-prone
FLOOD_PRONE_ELEVATION = 8.5


# ---------------------------------------------------------------------------
# Graph loading
# ---------------------------------------------------------------------------

def load_graph() -> nx.MultiDiGraph:
    """Load T.Nagar graph from prepared GeoJSON files into a NetworkX MultiDiGraph."""
    global _G, _nodes_geojson, _edges_geojson

    settings = get_settings()
    nodes_path = settings.nodes_geojson
    edges_path = settings.edges_geojson

    logger.info("Loading graph from %s", nodes_path)

    with open(nodes_path, encoding="utf-8") as f:
        _nodes_geojson = json.load(f)
    with open(edges_path, encoding="utf-8") as f:
        _edges_geojson = json.load(f)

    G = nx.MultiDiGraph()

    # --- Add nodes ---
    for feat in _nodes_geojson["features"]:
        props = feat["properties"]
        coords = feat["geometry"]["coordinates"]  # [lon, lat]
        osmid = int(props["osmid"])

        elevation = props.get("elevation_m") or 10.0
        population = props.get("population") or 0.0

        # Classify node type based on OSM highway tag + elevation
        highway = props.get("highway")
        if highway and "pump" in str(highway):
            node_type = "pump"
        elif elevation < FLOOD_PRONE_ELEVATION:
            node_type = "flood_prone_junction"
        else:
            node_type = "road_junction"

        # Road capacity (vehicles/hr) — heuristic based on street_count
        street_count = props.get("street_count") or 2
        capacity = street_count * 600.0  # ~600 veh/hr per lane approach

        G.add_node(
            osmid,
            x=coords[0],
            y=coords[1],
            lon=coords[0],
            lat=coords[1],
            elevation_m=float(elevation),
            population_served=float(population),
            street_count=int(street_count),
            node_type=node_type,
            capacity=float(capacity),
            flood_depth_m=0.0,  # runtime attribute; 0 = not flooded
            flooded=False,
        )

    # --- Add edges ---
    for feat in _edges_geojson["features"]:
        props = feat["properties"]
        u = int(props["u"])
        v = int(props["v"])
        key = int(props.get("key", 0))

        length = props.get("length") or 100.0
        travel_time = props.get("travel_time") or 30.0
        speed_kph = props.get("speed_kph") or 30.0
        highway = props.get("highway") or "residential"

        # Road flow capacity heuristic
        road_capacity = _road_capacity(highway)

        G.add_edge(
            u, v,
            key=key,
            osmid=props.get("osmid"),
            highway=highway,
            length=float(length),
            travel_time=float(travel_time),
            speed_kph=float(speed_kph),
            capacity=float(road_capacity),
            edge_type="road",
            weight=1.0,        # dependency strength (physics-initialized)
            flooded=False,
            flood_depth_m=0.0,
            geometry=feat.get("geometry", {}),
            name=props.get("name"),
        )

    logger.info(
        "Graph loaded: %d nodes, %d edges", G.number_of_nodes(), G.number_of_edges()
    )
    _G = G
    return G


def _road_capacity(highway: str) -> float:
    """Heuristic road capacity in vehicles/hour."""
    capacities = {
        "motorway": 4000, "trunk": 3000, "primary": 2000,
        "secondary": 1500, "tertiary": 1000, "residential": 600,
        "service": 300, "unclassified": 400, "living_street": 200,
    }
    for k, v in capacities.items():
        if k in str(highway):
            return float(v)
    return 600.0


# ---------------------------------------------------------------------------
# Graph accessor
# ---------------------------------------------------------------------------

def get_graph() -> nx.MultiDiGraph:
    """Return the loaded graph, raising if not initialised."""
    if _G is None:
        raise RuntimeError("Graph not loaded — call load_graph() during startup.")
    return _G


def get_node(node_id: int) -> dict[str, Any]:
    G = get_graph()
    if node_id not in G.nodes:
        raise KeyError(f"Node {node_id} not found in graph")
    return dict(G.nodes[node_id])


def get_neighbors(node_id: int, hops: int = 1) -> list[int]:
    """Return all nodes within N hops (BFS), undirected."""
    G = get_graph()
    visited = set()
    frontier = {node_id}
    for _ in range(hops):
        next_frontier = set()
        for n in frontier:
            for nb in list(G.successors(n)) + list(G.predecessors(n)):
                if nb not in visited:
                    next_frontier.add(nb)
        visited |= frontier
        frontier = next_frontier
    return list(visited | frontier)


def subgraph_around(node_ids: list[int]) -> nx.MultiDiGraph:
    """Extract a subgraph containing the given nodes + their direct neighbours."""
    G = get_graph()
    extended = set(node_ids)
    for n in node_ids:
        extended.update(G.successors(n))
        extended.update(G.predecessors(n))
    return G.subgraph(extended).copy()


# ---------------------------------------------------------------------------
# GeoJSON serialisation (for API responses)
# ---------------------------------------------------------------------------

def graph_to_geojson(
    max_nodes: int = 2296,
    max_edges: int = 5481,
    flood_state: Optional[dict[int, float]] = None,
) -> dict:
    """Serialise the in-memory graph to a GeoJSON-like dict for the frontend.

    flood_state: mapping node_id -> flood_depth_m (from simulation result)
    """
    G = get_graph()
    flood_state = flood_state or {}

    nodes_out = []
    for node_id, data in list(G.nodes(data=True))[:max_nodes]:
        depth = flood_state.get(node_id, 0.0)
        nodes_out.append({
            "type": "Feature",
            "id": str(node_id),
            "properties": {
                "osmid": node_id,
                "x": data["x"],
                "y": data["y"],
                "elevation_m": data.get("elevation_m", 10.0),
                "population_served": data.get("population_served", 0.0),
                "node_type": data.get("node_type", "road_junction"),
                "capacity": data.get("capacity", 600.0),
                "flood_depth_m": depth,
                "flooded": depth > 0.1,
            },
            "geometry": {
                "type": "Point",
                "coordinates": [data["x"], data["y"]],
            },
        })

    edges_out = []
    for u, v, key, data in list(G.edges(keys=True, data=True))[:max_edges]:
        geom = data.get("geometry") or {
            "type": "LineString",
            "coordinates": [
                [G.nodes[u]["x"], G.nodes[u]["y"]],
                [G.nodes[v]["x"], G.nodes[v]["y"]],
            ],
        }
        u_depth = flood_state.get(u, 0.0)
        v_depth = flood_state.get(v, 0.0)
        edge_flood = max(u_depth, v_depth)

        edges_out.append({
            "type": "Feature",
            "properties": {
                "u": u,
                "v": v,
                "key": key,
                "highway": data.get("highway", "residential"),
                "length": data.get("length", 100.0),
                "travel_time": data.get("travel_time", 30.0),
                "edge_type": data.get("edge_type", "road"),
                "weight": data.get("weight", 1.0),
                "flood_depth_m": edge_flood,
                "flooded": edge_flood > 0.1,
                "name": data.get("name"),
            },
            "geometry": geom,
        })

    return {
        "type": "FeatureCollection",
        "nodes": nodes_out,
        "edges": edges_out,
        "meta": {
            "city": "T.Nagar, Chennai",
            "node_count": len(nodes_out),
            "edge_count": len(edges_out),
            "crs": "EPSG:4326",
        },
    }


# ---------------------------------------------------------------------------
# Intervention catalog
# ---------------------------------------------------------------------------

def _build_intervention_catalog(G: nx.MultiDiGraph) -> list[dict]:
    """Build a deterministic intervention catalog from graph nodes.

    Selects interesting nodes (low-elevation, high-population, high-connectivity)
    and creates typed interventions for them.
    """
    rng = random.Random(42)

    # Score nodes: low elevation + high population + high street_count = good target
    candidates = []
    for nid, data in G.nodes(data=True):
        elev = data.get("elevation_m", 10.0)
        pop = data.get("population_served", 0.0)
        sc = data.get("street_count", 2)
        score = (pop / 1000.0) * (1.0 / max(elev, 1.0)) * sc
        candidates.append((score, nid, data))

    candidates.sort(reverse=True)
    top_nodes = candidates[:30]  # top 30 by priority

    catalog = []
    intervention_types = [
        ("drain_upgrade",    "Upgrade Storm Drain",     lambda n, d: {
            "cost": rng.uniform(800_000, 2_000_000),
            "effect": {"drain_capacity_mult": 1.8, "elevation_raise_m": 0.0, "road_capacity_mult": 1.0, "runoff_reduction": 0.15, "travel_time_mult": 1.0},
            "duration_weeks": 3,
        }),
        ("road_elevation",   "Raise Road Elevation",    lambda n, d: {
            "cost": rng.uniform(2_000_000, 5_000_000),
            "effect": {"drain_capacity_mult": 1.0, "elevation_raise_m": 0.5, "road_capacity_mult": 1.1, "runoff_reduction": 0.0, "travel_time_mult": 0.9},
            "duration_weeks": 8,
        }),
        ("pump_install",     "Install Pump Station",    lambda n, d: {
            "cost": rng.uniform(1_500_000, 3_500_000),
            "effect": {"drain_capacity_mult": 2.0, "elevation_raise_m": 0.0, "road_capacity_mult": 1.0, "runoff_reduction": 0.25, "travel_time_mult": 1.0},
            "duration_weeks": 6,
        }),
        ("retention_pond",   "Retention Pond",          lambda n, d: {
            "cost": rng.uniform(3_000_000, 6_000_000),
            "effect": {"drain_capacity_mult": 1.5, "elevation_raise_m": 0.0, "road_capacity_mult": 1.0, "runoff_reduction": 0.35, "travel_time_mult": 1.0},
            "duration_weeks": 12,
        }),
        ("permeable_surface","Permeable Pavement",      lambda n, d: {
            "cost": rng.uniform(600_000, 1_500_000),
            "effect": {"drain_capacity_mult": 1.2, "elevation_raise_m": 0.0, "road_capacity_mult": 0.95, "runoff_reduction": 0.20, "travel_time_mult": 1.0},
            "duration_weeks": 2,
        }),
        ("channel_widen",    "Widen Drainage Channel",  lambda n, d: {
            "cost": rng.uniform(1_200_000, 3_000_000),
            "effect": {"drain_capacity_mult": 1.6, "elevation_raise_m": 0.0, "road_capacity_mult": 1.0, "runoff_reduction": 0.10, "travel_time_mult": 1.0},
            "duration_weeks": 5,
        }),
    ]

    itype_cycle = intervention_types * 5  # enough to cover 20+ items

    descriptions = {
        "drain_upgrade": "Upgrade storm drain capacity to handle higher rainfall volumes and prevent road flooding.",
        "road_elevation": "Raise road surface elevation to protect against flood inundation.",
        "pump_install": "Install high-capacity electric pump station to actively remove floodwater.",
        "retention_pond": "Construct a retention pond to absorb excess runoff during heavy rainfall events.",
        "permeable_surface": "Replace impermeable surface with permeable pavement to increase groundwater recharge.",
        "channel_widen": "Widen existing drainage channel to increase carrying capacity.",
    }

    for idx, (score, nid, data) in enumerate(top_nodes[:22]):
        itype_name, itype_label, itype_fn = itype_cycle[idx % len(intervention_types)]
        params = itype_fn(nid, data)
        int_id = f"int_{idx+1:02d}"

        catalog.append({
            "id": int_id,
            "name": f"{itype_label} — Node {nid}",
            "description": descriptions.get(itype_name, ""),
            "target_node": nid,
            "intervention_type": itype_name,
            "cost": round(params["cost"], -3),
            "effect": params["effect"],
            "duration_weeks": params["duration_weeks"],
            "priority_area": score > 5.0,
            "node_lat": data.get("y"),
            "node_lon": data.get("x"),
            "elevation_m": data.get("elevation_m"),
            "population_served": data.get("population_served"),
        })

    return catalog


def get_intervention_catalog() -> list[dict]:
    """Return (or lazily build) the intervention catalog."""
    global _intervention_catalog
    if _intervention_catalog is None:
        G = get_graph()
        _intervention_catalog = _build_intervention_catalog(G)
    return _intervention_catalog


def get_intervention_by_id(int_id: str) -> Optional[dict]:
    catalog = get_intervention_catalog()
    for item in catalog:
        if item["id"] == int_id:
            return item
    return None
