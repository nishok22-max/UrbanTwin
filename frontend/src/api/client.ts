/**
 * Typed API client for UrbanTwin backend.
 * All calls go through /api (proxied to http://localhost:8000 by Vite).
 */

const BASE_URL = '/api'

// ---------------------------------------------------------------------------
// Type definitions (mirrors backend Pydantic models)
// ---------------------------------------------------------------------------

export interface UncertaintyRange {
  value: number
  low: number
  high: number
}

export interface ConsequenceVector {
  cost: number
  risk_reduction: UncertaintyRange
  population_protected: UncertaintyRange
  mobility_disruption_min: UncertaintyRange
  service_availability: number
  nodes_flooded_baseline: number
  nodes_flooded_with_intervention: number
  roads_blocked_baseline: number
  roads_blocked_with_intervention: number
}

export interface CascadeHop {
  node_id: number
  node_type: string
  lat: number
  lon: number
  flood_depth_m: number
  travel_time_delta_min: number
  hop: number
}

export interface SimulationResult {
  scenario_id: string
  consequence: ConsequenceVector
  cascade_path: CascadeHop[]
  confidence: 'high' | 'medium' | 'low'
  dominant_uncertainty: string
  computation_time_ms: number
  conservation_ok: boolean
  fallback_used: boolean
  meta: Record<string, unknown>
}

export interface SimulationRequest {
  scenario_id: string
  intervention_ids: string[]
  rainfall_mm?: number
  max_cascade_hops?: number
  monte_carlo_runs?: number
}

export interface InterventionEffect {
  drain_capacity_mult: number
  elevation_raise_m: number
  road_capacity_mult: number
  runoff_reduction: number
  travel_time_mult: number
}

export interface Intervention {
  id: string
  name: string
  description: string
  target_node: number
  intervention_type: string
  cost: number
  effect: InterventionEffect
  duration_weeks: number
  priority_area: boolean
  node_lat: number
  node_lon: number
  elevation_m: number
  population_served: number
}

export interface NodeProperties {
  osmid: number
  x: number
  y: number
  elevation_m: number
  population_served: number
  node_type: string
  flood_depth_m: number
  flooded: boolean
}

export interface NodeFeature {
  type: 'Feature'
  id: string
  properties: NodeProperties
  geometry: { type: 'Point'; coordinates: [number, number] }
}

export interface EdgeProperties {
  u: number
  v: number
  highway: string
  length: number
  travel_time: number
  flood_depth_m: number
  flooded: boolean
}

export interface EdgeFeature {
  type: 'Feature'
  properties: EdgeProperties
  geometry: { type: 'LineString'; coordinates: [number, number][] }
}

export interface GraphData {
  type: 'FeatureCollection'
  nodes: NodeFeature[]
  edges: EdgeFeature[]
  meta: Record<string, unknown>
}

export interface HealthCheck {
  status: string
  city: string
  graph_nodes: number
  graph_edges: number
  milestone: string
}

// ---------------------------------------------------------------------------
// M3: Optimizer & Recommendation types
// ---------------------------------------------------------------------------

export interface RankedScenario {
  scenario_id: string
  rank: number
  score: number
  consequence: ConsequenceVector
  intervention_ids: string[]
  total_cost: number
}

export interface Recommendation {
  id: string
  budget: number
  ranked: RankedScenario[]
  explanation: string
  explanation_source: 'template' | 'llm'
  weights_used: Record<string, number>
  meta: Record<string, unknown>
}

export interface OptimizeRequest {
  budget: number
  intervention_ids?: string[]
  rainfall_mm?: number
  objective_weights?: Record<string, number>
  max_bundles?: number
}

// ---------------------------------------------------------------------------
// Generic fetch helper
// ---------------------------------------------------------------------------

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? `API error ${res.status}`)
  }
  return res.json()
}

// ---------------------------------------------------------------------------
// API methods
// ---------------------------------------------------------------------------

export const api = {
  health(): Promise<HealthCheck> {
    return apiFetch<HealthCheck>('/healthz')
  },

  getGraph(maxNodes = 2296, maxEdges = 5481): Promise<GraphData> {
    return apiFetch<GraphData>(`/graph?max_nodes=${maxNodes}&max_edges=${maxEdges}`)
  },

  getInterventions(): Promise<{ count: number; interventions: Intervention[] }> {
    return apiFetch('/interventions')
  },

  simulate(req: SimulationRequest): Promise<SimulationResult> {
    return apiFetch<SimulationResult>('/simulate', {
      method: 'POST',
      body: JSON.stringify(req),
    })
  },

  whatIf(interventionId: string, rainfallMm = 160): Promise<SimulationResult> {
    return apiFetch<SimulationResult>(
      `/simulate/what-if?intervention_id=${interventionId}&rainfall_mm=${rainfallMm}`,
      { method: 'POST' }
    )
  },

  /** POST /optimize — find best intervention bundles under budget. */
  optimize(req: OptimizeRequest): Promise<Recommendation> {
    return apiFetch<Recommendation>('/optimize', {
      method: 'POST',
      body: JSON.stringify(req),
    })
  },

  /** GET /recommendation/{id} — retrieve a stored recommendation. */
  getRecommendation(id: string): Promise<Recommendation> {
    return apiFetch<Recommendation>(`/recommendation/${id}`)
  },
}
