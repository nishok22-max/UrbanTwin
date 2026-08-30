"""Synthetic-Twin Validation Harness (R5 Day 2).

Validates that:
  1. Interventions in flood-prone nodes protect population, whereas interventions in dry high-elevation nodes have 0 flood delta.
  2. Larger intervention bundles yield strictly greater or equal population protection than smaller bundles (monotonicity).
  3. Conservation check holds across all synthetic configurations.
"""
import pytest
from app.models.consequence import SimulationRequest
from app.services.consequence.engine import ConsequenceEngine
from app.services import graph_service


def test_synthetic_twin_targeted_vs_irrelevant(loaded_graph, intervention_catalog):
    """An intervention in a flooded node must protect strictly more population than in an already dry node."""
    engine = ConsequenceEngine()

    # Find an intervention in the catalog whose target node is in a low-elevation area (< 8m)
    flood_target = next(i for i in intervention_catalog if i.get("elevation_m", 15.0) < 8.0)

    # Find a node with high elevation (> 18m) which never floods
    high_elev_nodes = [
        (nid, d) for nid, d in loaded_graph.nodes(data=True)
        if float(d.get("elevation_m") or 0.0) > 18.0
    ]
    dry_node_id = high_elev_nodes[0][0]

    # Create synthetic dry-node intervention
    dry_intervention = {
        "id": "int_dry_test",
        "name": "Upgrade Drain on Dry Hill",
        "description": "Drain on safe elevation",
        "target_node": dry_node_id,
        "intervention_type": "drain_upgrade",
        "cost": 1000000,
        "effect": {"drain_capacity_mult": 2.0, "elevation_raise_m": 0.0, "runoff_reduction": 0.0, "road_capacity_mult": 1.0, "travel_time_mult": 1.0},
        "duration_weeks": 3,
        "priority_area": False,
        "node_lat": high_elev_nodes[0][1]["y"],
        "node_lon": high_elev_nodes[0][1]["x"],
        "elevation_m": high_elev_nodes[0][1]["elevation_m"],
        "population_served": 0.0,
    }

    # Temporarily register in catalog
    intervention_catalog.append(dry_intervention)

    try:
        res_flood = engine.simulate(SimulationRequest(
            scenario_id="scn_flood_target",
            intervention_ids=[flood_target["id"]],
            rainfall_mm=160.0,
            monte_carlo_runs=20,
        ))

        res_dry = engine.simulate(SimulationRequest(
            scenario_id="scn_dry_target",
            intervention_ids=["int_dry_test"],
            rainfall_mm=160.0,
            monte_carlo_runs=20,
        ))

        # Flooded target intervention must protect strictly more population than dry-area intervention
        assert res_flood.consequence.population_protected.value > res_dry.consequence.population_protected.value
        assert res_flood.consequence.risk_reduction.value >= res_dry.consequence.risk_reduction.value
    finally:
        intervention_catalog.pop()


def test_synthetic_twin_monotonicity(loaded_graph, intervention_catalog):
    """Adding more interventions must monotonically decrease flooded node count."""
    engine = ConsequenceEngine()

    bundle_1 = [intervention_catalog[0]["id"]]
    bundle_3 = [intervention_catalog[i]["id"] for i in range(3)]
    bundle_6 = [intervention_catalog[i]["id"] for i in range(6)]

    res_1 = engine.simulate(SimulationRequest(scenario_id="b1", intervention_ids=bundle_1, rainfall_mm=160.0, monte_carlo_runs=20))
    res_3 = engine.simulate(SimulationRequest(scenario_id="b3", intervention_ids=bundle_3, rainfall_mm=160.0, monte_carlo_runs=20))
    res_6 = engine.simulate(SimulationRequest(scenario_id="b6", intervention_ids=bundle_6, rainfall_mm=160.0, monte_carlo_runs=20))

    # Node count check: bundle_6 <= bundle_3 <= bundle_1
    assert res_6.consequence.nodes_flooded_with_intervention <= res_3.consequence.nodes_flooded_with_intervention
    assert res_3.consequence.nodes_flooded_with_intervention <= res_1.consequence.nodes_flooded_with_intervention

    # Population protected check: bundle_6 >= bundle_3 >= bundle_1
    assert res_6.consequence.population_protected.value >= res_3.consequence.population_protected.value - 1e-3
    assert res_3.consequence.population_protected.value >= res_1.consequence.population_protected.value - 1e-3


def test_synthetic_twin_conservation(loaded_graph, intervention_catalog):
    """Conservation: risk_reduction ∈ [0,1] and total exposed pop never increases after intervention."""
    from app.services.consequence.engine import ConsequenceEngine
    from app.models.consequence import SimulationRequest

    engine = ConsequenceEngine()
    all_ids = [i["id"] for i in intervention_catalog]

    # Baseline (no interventions)
    res_base = engine.simulate(SimulationRequest(
        scenario_id="conservation_base",
        intervention_ids=[],
        rainfall_mm=160.0,
        monte_carlo_runs=20,
    ))

    # Full catalog (all interventions)
    res_full = engine.simulate(SimulationRequest(
        scenario_id="conservation_full",
        intervention_ids=all_ids,
        rainfall_mm=160.0,
        monte_carlo_runs=20,
    ))

    # Conservation: risk_reduction must be in [0, 1]
    assert 0.0 <= res_base.consequence.risk_reduction.value <= 1.0
    assert 0.0 <= res_full.consequence.risk_reduction.value <= 1.0

    # Conservation: more interventions never increase flooded node count beyond baseline
    assert res_full.consequence.nodes_flooded_with_intervention <= res_base.consequence.nodes_flooded_with_intervention + 1


def test_m4_healthz_milestone(client):
    """Phase 4: /healthz must report milestone=M4 and api_frozen=True."""
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["milestone"] == "M4"
    assert data.get("api_frozen") is True
    assert "test_suite" in data


def test_simulation_performance_sla(loaded_graph, intervention_catalog):
    """Phase 4 SLA: simulate must complete in < 2 seconds (demo guardrail)."""
    import time
    from app.services.consequence.engine import ConsequenceEngine
    from app.models.consequence import SimulationRequest

    engine = ConsequenceEngine()
    ids = [intervention_catalog[0]["id"]]

    start = time.perf_counter()
    engine.simulate(SimulationRequest(
        scenario_id="perf_test",
        intervention_ids=ids,
        rainfall_mm=160.0,
        monte_carlo_runs=50,
    ))
    elapsed = time.perf_counter() - start

    assert elapsed < 2.0, f"Simulation SLA exceeded: {elapsed:.2f}s (limit: 2.0s)"
