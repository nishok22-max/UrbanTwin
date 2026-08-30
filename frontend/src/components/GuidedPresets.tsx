/**
 * GuidedPresets — standard appraisal templates and objective weightings.
 *
 * Replaces the former "AI Copilot" panel. Two substantive changes beyond the
 * visual redesign:
 *
 *  1. The scripted "neural reasoning" sequence (four 220 ms sleeps before the
 *     request was even sent) is removed. The panel now reports only what is
 *     actually happening: a request is in flight.
 *  2. The free-text prompt box is removed. It discarded whatever was typed and
 *     ran the optimiser on the current settings regardless, which misrepresents
 *     the system's capability. The templates below do the same job honestly —
 *     each states the exact budget, design storm and weightings it applies.
 */
import React, { useMemo, useState } from 'react'
import { api } from '../api/client'
import { useStore } from '../state/store'
import { IconAppraisal, IconSettings, IconChevronDown, IconAlert } from './GovIcons'

interface AppraisalTemplate {
  id: string
  label: string
  purpose: string
  budget: number
  rainfall: number
  weights: Record<string, number>
}

const TEMPLATES: AppraisalTemplate[] = [
  {
    id: 'extreme-event',
    label: 'Extreme event defence',
    purpose: 'Maximum risk reduction against a record-magnitude storm',
    budget: 50_000_000,
    rainfall: 220,
    weights: {
      risk_reduction: 0.65,
      population_protected: 0.25,
      mobility_disruption_min: 0.05,
      service_availability: 0.05,
    },
  },
  {
    id: 'population-priority',
    label: 'Population priority',
    purpose: 'Protect the greatest number of residents in low-lying wards',
    budget: 80_000_000,
    rainfall: 180,
    weights: {
      risk_reduction: 0.2,
      population_protected: 0.7,
      mobility_disruption_min: 0.05,
      service_availability: 0.05,
    },
  },
  {
    id: 'corridor-continuity',
    label: 'Corridor continuity',
    purpose: 'Keep hospital and commercial arterial routes passable',
    budget: 30_000_000,
    rainfall: 140,
    weights: {
      risk_reduction: 0.3,
      population_protected: 0.2,
      mobility_disruption_min: 0.35,
      service_availability: 0.15,
    },
  },
  {
    id: 'constrained-budget',
    label: 'Constrained budget',
    purpose: 'Highest benefit per rupee where funds are limited',
    budget: 20_000_000,
    rainfall: 160,
    weights: {
      risk_reduction: 0.4,
      population_protected: 0.35,
      mobility_disruption_min: 0.15,
      service_availability: 0.1,
    },
  },
]

const WEIGHT_FIELDS = [
  { key: 'risk_reduction', label: 'Flood risk reduction' },
  { key: 'population_protected', label: 'Population protected' },
  { key: 'mobility_disruption_min', label: 'Mobility preserved' },
  { key: 'service_availability', label: 'Service availability' },
] as const

function formatCrore(n: number): string {
  return `₹${(n / 10_000_000).toFixed(n % 10_000_000 === 0 ? 0 : 1)} Cr`
}

export const GuidedPresets: React.FC<{ onComplete?: () => void }> = ({ onComplete }) => {
  const [showWeights, setShowWeights] = useState(false)
  const [appliedTemplate, setAppliedTemplate] = useState<string | null>(null)

  const status = useStore((s) => s.status)
  const objectiveWeights = useStore((s) => s.objectiveWeights)
  const setBudget = useStore((s) => s.setBudget)
  const setRainfallMm = useStore((s) => s.setRainfallMm)
  const setObjectiveWeights = useStore((s) => s.setObjectiveWeights)
  const setRecommendation = useStore((s) => s.setRecommendation)
  const setStatus = useStore((s) => s.setStatus)
  const setError = useStore((s) => s.setError)

  const isBusy = status === 'optimizing' || status === 'simulating' || status === 'ai-reasoning'

  const weightTotal = useMemo(
    () => WEIGHT_FIELDS.reduce((sum, f) => sum + (objectiveWeights[f.key] ?? 0), 0),
    [objectiveWeights]
  )
  const weightsBalanced = Math.abs(weightTotal - 1) < 0.005

  const applyTemplate = async (template: AppraisalTemplate) => {
    setBudget(template.budget)
    setRainfallMm(template.rainfall)
    setObjectiveWeights(template.weights)
    setAppliedTemplate(template.id)

    setStatus('optimizing')
    setError(null)
    try {
      const rec = await api.optimize({
        budget: template.budget,
        rainfall_mm: template.rainfall,
        objective_weights: template.weights,
        max_bundles: 3,
      })
      setRecommendation(rec)
      setStatus('ready')
      onComplete?.()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Optimisation failed')
      setStatus('error')
    }
  }

  return (
    <section className="gov-panel">
      <div className="gov-panel__header">
        <h2 className="gov-panel__title">
          <IconAppraisal size={14} />
          Standard appraisal templates
        </h2>
      </div>

      <div className="gov-panel__body" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
        <p className="gov-hint">
          Each template applies a fixed budget, design storm and set of objective
          weightings, then runs the allocation. Values are shown before you
          commit.
        </p>

        <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column' }}>
          {TEMPLATES.map((template) => {
            const isApplied = appliedTemplate === template.id
            return (
              <li key={template.id}>
                <button
                  type="button"
                  id={`template-${template.id}`}
                  className={`gov-option ${isApplied ? 'is-selected' : ''}`}
                  onClick={() => applyTemplate(template)}
                  disabled={isBusy}
                  style={{ flexDirection: 'column', gap: '3px' }}
                >
                  <span
                    style={{
                      display: 'flex',
                      width: '100%',
                      justifyContent: 'space-between',
                      alignItems: 'baseline',
                      gap: 'var(--space-2)',
                    }}
                  >
                    <span
                      style={{
                        fontSize: 'var(--font-size-sm)',
                        fontWeight: 700,
                        color: 'var(--gov-navy-900)',
                      }}
                    >
                      {template.label}
                    </span>
                    <span
                      className="tabular"
                      style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: 'var(--font-size-xs)',
                        fontWeight: 700,
                        color: 'var(--gov-saffron-700)',
                      }}
                    >
                      {formatCrore(template.budget)}
                    </span>
                  </span>

                  <span className="gov-hint" style={{ display: 'block' }}>
                    {template.purpose}
                  </span>

                  <span
                    className="tabular"
                    style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: '10px',
                      color: 'var(--clr-text-muted)',
                    }}
                  >
                    Design storm {template.rainfall} mm · Risk{' '}
                    {(template.weights.risk_reduction * 100).toFixed(0)}% · Population{' '}
                    {(template.weights.population_protected * 100).toFixed(0)}%
                  </span>
                </button>
              </li>
            )
          })}
        </ul>

        {isBusy && (
          <div className="gov-notice gov-notice--info" role="status" aria-live="polite">
            <span className="spinner gov-notice__icon" />
            <div>
              <strong>Computing allocation…</strong>
              <div>
                Solving the budget-constrained selection and evaluating candidate
                bundles.
              </div>
            </div>
          </div>
        )}

        {/* ── Objective weightings ─────────────────────────────────────── */}
        <div>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => setShowWeights((v) => !v)}
            aria-expanded={showWeights}
            aria-controls="objective-weights"
            style={{ width: '100%', justifyContent: 'space-between' }}
          >
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
              <IconSettings size={13} />
              Objective weightings
            </span>
            <IconChevronDown
              size={13}
              style={{ transform: showWeights ? 'rotate(180deg)' : undefined }}
            />
          </button>

          {showWeights && (
            <div
              id="objective-weights"
              style={{
                marginTop: 'var(--space-2)',
                padding: 'var(--space-3)',
                border: '1px solid var(--clr-border)',
                background: 'var(--gov-grey-050)',
                display: 'flex',
                flexDirection: 'column',
                gap: 'var(--space-3)',
              }}
            >
              {WEIGHT_FIELDS.map((field) => {
                const value = objectiveWeights[field.key] ?? 0
                return (
                  <div key={field.key}>
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        gap: 'var(--space-2)',
                        marginBottom: '3px',
                      }}
                    >
                      <label
                        className="gov-label"
                        htmlFor={`weight-${field.key}`}
                        style={{ marginBottom: 0 }}
                      >
                        {field.label}
                      </label>
                      <span
                        className="tabular"
                        style={{
                          fontFamily: 'var(--font-mono)',
                          fontSize: 'var(--font-size-xs)',
                          fontWeight: 700,
                          color: 'var(--gov-navy-900)',
                        }}
                      >
                        {(value * 100).toFixed(0)}%
                      </span>
                    </div>
                    <input
                      id={`weight-${field.key}`}
                      type="range"
                      min={0}
                      max={1}
                      step={0.05}
                      value={value}
                      onChange={(e) =>
                        setObjectiveWeights({ [field.key]: Number(e.target.value) })
                      }
                      aria-valuetext={`${(value * 100).toFixed(0)} percent`}
                    />
                  </div>
                )
              })}

              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  paddingTop: 'var(--space-2)',
                  borderTop: '1px solid var(--clr-border)',
                  fontSize: 'var(--font-size-xs)',
                  fontWeight: 700,
                }}
              >
                <span style={{ color: 'var(--clr-text-secondary)' }}>Total</span>
                <span
                  className="tabular"
                  style={{
                    fontFamily: 'var(--font-mono)',
                    color: weightsBalanced ? 'var(--gov-green-700)' : 'var(--gov-saffron-700)',
                  }}
                >
                  {(weightTotal * 100).toFixed(0)}%
                </span>
              </div>

              {!weightsBalanced && (
                <div className="gov-notice gov-notice--warn" style={{ padding: 'var(--space-2)' }}>
                  <IconAlert size={13} className="gov-notice__icon" />
                  <span>
                    Weightings do not sum to 100%. They are normalised before
                    scoring, so only their relative proportions take effect.
                  </span>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
