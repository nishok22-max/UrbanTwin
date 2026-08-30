"""Comprehensive tests for Consequence Engine (M2).

Covers:
  - FloodModule (hydrology rules, elevation-deficit, drain capacity)
  - MobilityModule (traffic flow, BPR travel time degradation)
  - CouplingResolver (2-3 hop bounded BFS cascade propagation)
  - UncertaintyRunner (Monte Carlo sampling, p10/p90 ranges, confidence)
  - ConsequenceEngine (orchestration, conservation checks, performance)
  - MarginalCache
  - API Endpoints (/healthz, /graph, /interventions, /simulate, /simulate/what-if)
"""
import pytest
from app.models.consequence import SimulationRequest, SimulationResult
from app.services.consequence.domains.flood import FloodModule
from app.services.consequence.domains.mobility import MobilityModule
from app.services.consequence.coupling import CouplingResolver
from app.services.consequence.uncertainty import UncertaintyRunner
from app.services.consequence.engine import ConsequenceEngine
from app.services.optimizer.marginal_cache import MarginalCache


def test_healthz_endpoint(client):
    """Test /healthz liveness endpoint."""
    res = client.get("/healthz")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["city"] == "tnagar"
    assert data["graph_nodes"] > 0
    assert data["graph_edges"] > 0
    assert data["milestone"] == "M4"


def test_get_graph_endpoint(client):
    """Test GET /graph returns GeoJSON structure."""
    res = client.get("/graph?max_nodes=100&max_edges=100")
    assert res.status_code == 200
    data = res.json()
    assert data["type"] == "FeatureCollection"
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) <= 100
    assert len(data["edges"]) <= 100
    assert "osmid" in data["nodes"][0]["properties"]
    assert "elevation_m" in data["nodes"][0]["properties"]


def test_get_interventions_endpoint(client):
    """Test GET /interventions returns catalog."""
    res = client.get("/interventions")
    assert res.status_code == 200
    data = res.json()
    assert data["count"] > 0
    assert len(data["interventions"]) == data["count"]
    item = data["interventions"][0]
    assert "id" in item
    assert "cost" in item
    assert "intervention_type" in item
    assert "effect" in item
    assert item["cost"] > 0


def test_flood_module_physics(loaded_graph, intervention_catalog):
    """Test FloodModule: higher rainfall -> more flooding; interventions -> less flooding."""
    flood = FloodModule()

    # 1. Rainfall monotonicity
    res_80 = flood.compute_impact(loaded_graph, [], intervention_catalog, 80.0, 42)
    res_160 = flood.compute_impact(loaded_graph, [], intervention_catalog, 160.0, 42)
    flooded_80 = sum(1 for i in res_80.values() if i.flooded)
    flooded_160 = sum(1 for i in res_160.values() if i.flooded)
    assert flooded_160 >= flooded_80

    # 2. Interventions reduce or maintain flood count
    active_ids = [intervention_catalog[0]["id"], intervention_catalog[1]["id"]]
    res_int = flood.compute_impact(loaded_graph, active_ids, intervention_catalog, 160.0, 42)
    flooded_int = sum(1 for i in res_int.values() if i.flooded)
    assert flooded_int <= flooded_160


def test_mobility_module_coupling(loaded_graph, intervention_catalog):
    """Test MobilityModule: flooded roads result in higher travel-time deltas."""
    flood = FloodModule()
    mobility = MobilityModule()

    flood_res = flood.compute_impact(loaded_graph, [], intervention_catalog, 160.0, 42)
    mob_res = mobility.compute_impact(
        loaded_graph, [], intervention_catalog, 160.0, 42, flood_impacts=flood_res
    )

    assert len(mob_res) == len(loaded_graph.nodes)
    avg_delay = sum(i.travel_time_delta_min for i in mob_res.values()) / len(mob_res)
    assert avg_delay >= 0.0


def test_coupling_resolver_bounded_hops(loaded_graph, intervention_catalog):
    """Test CouplingResolver respects max_hops constraint."""
    flood = FloodModule()
    mobility = MobilityModule()
    resolver = CouplingResolver(max_hops=2)

    flood_res = flood.compute_impact(loaded_graph, [], intervention_catalog, 160.0, 42)
    mob_res = mobility.compute_impact(
        loaded_graph, [], intervention_catalog, 160.0, 42, flood_impacts=flood_res
    )

    cascade = resolver.propagate(loaded_graph, flood_res, mob_res)
    assert cascade.max_hop <= 2
    for node in cascade.path:
        assert node.hop <= 2


def test_uncertainty_runner(loaded_graph, intervention_catalog):
    """Test UncertaintyRunner produces consistent p10 <= mean <= p90 bounds."""
    flood = FloodModule()
    mobility = MobilityModule()
    runner = UncertaintyRunner()

    f_null = flood.compute_impact(loaded_graph, [], intervention_catalog, 160.0, 42)
    m_null = mobility.compute_impact(loaded_graph, [], intervention_catalog, 160.0, 42, flood_impacts=f_null)

    active_ids = [intervention_catalog[0]["id"]]
    f_with = flood.compute_impact(loaded_graph, active_ids, intervention_catalog, 160.0, 42)
    m_with = mobility.compute_impact(loaded_graph, active_ids, intervention_catalog, 160.0, 42, flood_impacts=f_with)

    res = runner.run(f_with, m_with, f_null, m_null, 160.0, n_trials=30, rng_seed=42)

    assert res.risk_reduction_low <= res.risk_reduction_value <= res.risk_reduction_high + 1e-5
    assert res.population_protected_low <= res.population_protected_value <= res.population_protected_high + 1e-5
    assert res.confidence in ("high", "medium", "low")


def test_consequence_engine_full_simulation(loaded_graph, intervention_catalog):
    """Test end-to-end simulation through ConsequenceEngine."""
    engine = ConsequenceEngine()
    req = SimulationRequest(
        scenario_id="test_engine",
        intervention_ids=[intervention_catalog[0]["id"], intervention_catalog[1]["id"]],
        rainfall_mm=160.0,
        max_cascade_hops=3,
        monte_carlo_runs=30,
    )
    result = engine.simulate(req)

    assert isinstance(result, SimulationResult)
    assert result.scenario_id == "test_engine"
    assert result.conservation_ok is True
    assert result.computation_time_ms < 2000  # under 2 seconds performance target
    assert result.consequence.cost > 0
    assert len(result.cascade_path) > 0


def test_api_simulate(client, intervention_catalog):
    """Test POST /simulate endpoint."""
    payload = {
        "scenario_id": "api_test_scenario",
        "intervention_ids": [intervention_catalog[0]["id"]],
        "rainfall_mm": 160.0,
        "max_cascade_hops": 3,
        "monte_carlo_runs": 20,
    }
    res = client.post("/simulate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["scenario_id"] == "api_test_scenario"
    assert "consequence" in data
    assert "cascade_path" in data
    assert "confidence" in data
    assert data["conservation_ok"] is True


def test_api_what_if(client, intervention_catalog):
    """Test POST /simulate/what-if convenience endpoint."""
    int_id = intervention_catalog[0]["id"]
    res = client.post(f"/simulate/what-if?intervention_id={int_id}&rainfall_mm=160")
    assert res.status_code == 200
    data = res.json()
    assert f"whatif_{int_id}" in data["scenario_id"]
    assert "consequence" in data


def test_marginal_cache(intervention_catalog):
    """Test MarginalCache caching behavior."""
    cache = MarginalCache()
    int_id = intervention_catalog[0]["id"]

    res1 = cache.get_marginal(int_id, 160.0)
    res2 = cache.get_marginal(int_id, 160.0)

    # Second call should return the exact same object from cache
    assert res1 is res2
    assert res1.scenario_id == f"marginal_{int_id}_160.0"
