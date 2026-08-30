/**
 * Zustand app state store.
 * Holds: graph data, intervention catalog, selected interventions,
 * simulation result, recommendation (M3), active strategy, and UI state.
 */
import { create } from 'zustand'
import type { GraphData, Intervention, SimulationResult, Recommendation, RankedScenario } from '../api/client'

export type AppStatus =
  | 'idle'
  | 'loading-graph'
  | 'loading-interventions'
  | 'simulating'
  | 'optimizing'
  | 'ai-reasoning'
  | 'ready'
  | 'error'

export type ObjectiveWeights = Record<string, number>

interface AppState {
  // Data
  graphData: GraphData | null
  interventions: Intervention[]
  simulationResult: SimulationResult | null
  recommendation: Recommendation | null
  activeStrategy: RankedScenario | null

  // UI state
  status: AppStatus
  error: string | null
  selectedInterventionIds: Set<string>
  rainfallMm: number
  budget: number
  objectiveWeights: ObjectiveWeights
  hoveredNodeId: number | null
  selectedNodeId: number | null
  focusCoordinates: [number, number] | null
  showCascade: boolean
  cascadeAnimating: boolean
  aiReasoningStep: string | null

  // Actions
  setGraphData: (data: GraphData) => void
  setInterventions: (list: Intervention[]) => void
  setSimulationResult: (result: SimulationResult | null) => void
  setRecommendation: (rec: Recommendation | null) => void
  setActiveStrategy: (strategy: RankedScenario | null) => void
  setBudget: (b: number) => void
  setObjectiveWeights: (w: Partial<ObjectiveWeights>) => void
  setStatus: (s: AppStatus) => void
  setError: (e: string | null) => void
  toggleIntervention: (id: string) => void
  setSelectedInterventions: (ids: string[]) => void
  clearInterventions: () => void
  setRainfallMm: (mm: number) => void
  setHoveredNodeId: (id: number | null) => void
  setSelectedNodeId: (id: number | null) => void
  setFocusCoordinates: (coords: [number, number] | null) => void
  setShowCascade: (v: boolean) => void
  setCascadeAnimating: (v: boolean) => void
  setAiReasoningStep: (step: string | null) => void
}

export const useStore = create<AppState>((set) => ({
  // Initial state
  graphData: null,
  interventions: [],
  simulationResult: null,
  recommendation: null,
  activeStrategy: null,
  status: 'idle',
  error: null,
  selectedInterventionIds: new Set(),
  rainfallMm: 160,
  budget: 10_000_000,   // default ₹1 Cr
  objectiveWeights: {
    risk_reduction: 0.40,
    population_protected: 0.35,
    mobility_disruption_min: 0.15,
    service_availability: 0.10,
  },
  hoveredNodeId: null,
  selectedNodeId: null,
  focusCoordinates: null,
  showCascade: true,
  cascadeAnimating: false,
  aiReasoningStep: null,

  // Actions
  setGraphData: (data) => set({ graphData: data }),
  setInterventions: (list) => set({ interventions: list }),
  setSimulationResult: (result) => set({ simulationResult: result }),
  setRecommendation: (recommendation) => {
    set({
      recommendation,
      activeStrategy: recommendation?.ranked[0] ?? null,
      selectedInterventionIds: new Set(recommendation?.ranked[0]?.intervention_ids ?? []),
    })
  },
  setActiveStrategy: (strategy) => {
    set({
      activeStrategy: strategy,
      selectedInterventionIds: new Set(strategy?.intervention_ids ?? []),
    })
  },
  setBudget: (budget) => set({ budget }),
  setObjectiveWeights: (weights) =>
    set((state) => ({
      objectiveWeights: { ...state.objectiveWeights, ...weights } as Record<string, number>,
    })),
  setStatus: (status) => set({ status }),
  setError: (error) => set({ error }),

  toggleIntervention: (id) =>
    set((state) => {
      const next = new Set(state.selectedInterventionIds)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return { selectedInterventionIds: next }
    }),

  setSelectedInterventions: (ids) =>
    set({ selectedInterventionIds: new Set(ids) }),

  clearInterventions: () =>
    set({ selectedInterventionIds: new Set(), simulationResult: null, recommendation: null, activeStrategy: null }),

  setRainfallMm: (rainfallMm) => set({ rainfallMm }),
  setHoveredNodeId: (hoveredNodeId) => set({ hoveredNodeId }),
  setSelectedNodeId: (selectedNodeId) => set({ selectedNodeId }),
  setFocusCoordinates: (focusCoordinates) => set({ focusCoordinates }),
  setShowCascade: (showCascade) => set({ showCascade }),
  setCascadeAnimating: (cascadeAnimating) => set({ cascadeAnimating }),
  setAiReasoningStep: (aiReasoningStep) => set({ aiReasoningStep }),
}))
