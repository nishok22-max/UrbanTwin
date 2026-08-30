/**
 * ScenarioBuilder — scenario configuration form.
 *
 * Presented as a numbered sequence, in the order an officer would work through
 * it: design storm → sanctioned budget → schedule of candidate works →
 * actions. Each step is a labelled panel so the form structure is legible to
 * screen readers as well as sighted users.
 */
import React, { useCallback, useMemo, useState } from 'react'
import { api } from '../api/client'
import type { Intervention } from '../api/client'
import { useStore } from '../state/store'
import { GuidedPresets } from './GuidedPresets'
import { IconRainfall, IconBudget, IconWorks, IconCheck, IconWater } from './GovIcons'

/** Works categories, with the short code used in the register listing. */
const WORK_TYPES: Record<string, { label: string; code: string }> = {
  drain_upgrade: { label: 'Drain upgrade', code: 'DRN' },
  road_elevation: { label: 'Road elevation', code: 'ELV' },
  pump_install: { label: 'Pumping station', code: 'PMP' },
  retention_pond: { label: 'Retention pond', code: 'RET' },
  permeable_surface: { label: 'Permeable paving', code: 'PRM' },
  channel_widen: { label: 'Channel widening', code: 'CHN' },
}

function formatCost(n: number): string {
  if (n >= 10_000_000) return `₹${(n / 10_000_000).toFixed(2)} Cr`
  if (n >= 100_000) return `₹${(n / 100_000).toFixed(1)} L`
  return `₹${(n / 1000).toFixed(0)} K`
}

const BUDGET_PRESETS = [
  { label: '₹2 Cr', value: 20_000_000 },
  { label: '₹5 Cr', value: 50_000_000 },
  { label: '₹8 Cr', value: 80_000_000 },
  { label: '₹10 Cr', value: 100_000_000 },
]

/** Design storm bands, stated as return-period language rather than adjectives. */
function stormBand(mm: number): { label: string; tone: string } {
  if (mm < 100) return { label: 'Below design threshold', tone: 'var(--gov-green-700)' }
  if (mm < 150) return { label: 'Design storm', tone: 'var(--gov-saffron-700)' }
  if (mm < 200) return { label: 'Above design storm', tone: 'var(--gov-saffron-700)' }
  return { label: 'Record event (2015 magnitude)', tone: 'var(--gov-red-700)' }
}

// ---------------------------------------------------------------------------
// Step wrapper
// ---------------------------------------------------------------------------

const Step: React.FC<{
  index: number
  title: string
  icon: React.ReactNode
  aside?: React.ReactNode
  children: React.ReactNode
}> = ({ index, title, icon, aside, children }) => (
  <section className="gov-panel">
    <div className="gov-panel__header">
      <h2 className="gov-panel__title">
        <span className="gov-step" aria-hidden="true">
          {index}
        </span>
        {icon}
        {title}
      </h2>
      {aside}
    </div>
    <div className="gov-panel__body">{children}</div>
  </section>
)

// ---------------------------------------------------------------------------
// Works register row
// ---------------------------------------------------------------------------

const WorkRow: React.FC<{
  item: Intervention
  selected: boolean
  onToggle: () => void
  onLocate: () => void
}> = ({ item, selected, onToggle, onLocate }) => {
  const type = WORK_TYPES[item.intervention_type] ?? {
    label: item.intervention_type,
    code: 'GEN',
  }

  return (
    <li>
      <div
        className={`intervention-item ${selected ? 'selected' : ''}`}
        id={`intervention-${item.id}`}
        role="checkbox"
        aria-checked={selected}
        tabIndex={0}
        onClick={() => {
          onToggle()
          onLocate()
        }}
        onKeyDown={(e) => {
          if (e.key === ' ' || e.key === 'Enter') {
            e.preventDefault()
            onToggle()
            onLocate()
          }
        }}
      >
        <span className="intervention-checkbox" aria-hidden="true">
          {selected && <IconCheck size={11} style={{ color: 'var(--gov-white)' }} />}
        </span>

        <span style={{ flex: 1, minWidth: 0 }}>
          <span
            style={{
              display: 'flex',
              alignItems: 'baseline',
              justifyContent: 'space-between',
              gap: 'var(--space-2)',
            }}
          >
            <span
              style={{
                fontSize: 'var(--font-size-xs)',
                fontWeight: 600,
                color: 'var(--clr-text-primary)',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {item.name.split(' — ')[0]}
            </span>
            <span
              className="tabular"
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: 'var(--font-size-xs)',
                fontWeight: 600,
                color: 'var(--gov-saffron-700)',
                whiteSpace: 'nowrap',
              }}
            >
              {formatCost(item.cost)}
            </span>
          </span>

          <span
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              marginTop: '2px',
            }}
          >
            <span
              className="tabular"
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '10px',
                fontWeight: 700,
                color: 'var(--gov-navy-800)',
                letterSpacing: '0.04em',
              }}
            >
              {type.code}
            </span>
            <span style={{ fontSize: '10px', color: 'var(--clr-text-secondary)' }}>
              {type.label}
            </span>
            {item.priority_area && (
              <span className="badge badge-danger" style={{ fontSize: '9px' }}>
                Priority area
              </span>
            )}
          </span>
        </span>
      </div>
    </li>
  )
}

// ---------------------------------------------------------------------------
// ScenarioBuilder
// ---------------------------------------------------------------------------

export const ScenarioBuilder: React.FC<{ onOptimizeSuccess?: () => void }> = ({
  onOptimizeSuccess,
}) => {
  const interventions = useStore((s) => s.interventions)
  const selectedInterventionIds = useStore((s) => s.selectedInterventionIds)
  const rainfallMm = useStore((s) => s.rainfallMm)
  const budget = useStore((s) => s.budget)
  const status = useStore((s) => s.status)
  const toggleIntervention = useStore((s) => s.toggleIntervention)
  const clearInterventions = useStore((s) => s.clearInterventions)
  const setRainfallMm = useStore((s) => s.setRainfallMm)
  const setBudget = useStore((s) => s.setBudget)
  const setFocusCoordinates = useStore((s) => s.setFocusCoordinates)
  const setSimulationResult = useStore((s) => s.setSimulationResult)
  const setRecommendation = useStore((s) => s.setRecommendation)
  const setStatus = useStore((s) => s.setStatus)
  const setError = useStore((s) => s.setError)

  const budgetCr = budget / 10_000_000
  const [budgetDraft, setBudgetDraft] = useState(budgetCr.toFixed(1))
  const [budgetFocused, setBudgetFocused] = useState(false)

  const selectedList = useMemo(
    () => interventions.filter((i) => selectedInterventionIds.has(i.id)),
    [interventions, selectedInterventionIds]
  )
  const totalCost = useMemo(
    () => selectedList.reduce((sum, i) => sum + i.cost, 0),
    [selectedList]
  )

  const isSimulating = status === 'simulating'
  const isOptimizing = status === 'optimizing' || status === 'ai-reasoning'
  const isBusy = isSimulating || isOptimizing
  const overBudget = totalCost > budget
  const storm = stormBand(rainfallMm)

  const handleSimulate = useCallback(async () => {
    if (selectedInterventionIds.size === 0) return
    setStatus('simulating')
    setError(null)
    try {
      const result = await api.simulate({
        scenario_id: `scenario_${Date.now()}`,
        intervention_ids: Array.from(selectedInterventionIds),
        rainfall_mm: rainfallMm,
        max_cascade_hops: 3,
        monte_carlo_runs: 50,
      })
      setSimulationResult(result)
      setStatus('ready')
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Simulation failed')
      setStatus('error')
    }
  }, [selectedInterventionIds, rainfallMm, setStatus, setError, setSimulationResult])

  const handleOptimize = useCallback(async () => {
    if (budget <= 0) return
    setStatus('optimizing')
    setError(null)
    try {
      const rec = await api.optimize({ budget, rainfall_mm: rainfallMm, max_bundles: 3 })
      setRecommendation(rec)
      setStatus('ready')
      onOptimizeSuccess?.()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Optimisation failed')
      setStatus('error')
    }
  }, [budget, rainfallMm, setStatus, setError, setRecommendation, onOptimizeSuccess])

  const commitBudget = () => {
    setBudgetFocused(false)
    const parsed = parseFloat(budgetDraft)
    if (!Number.isNaN(parsed) && parsed > 0) setBudget(Math.round(parsed * 10_000_000))
    else setBudgetDraft(budgetCr.toFixed(1))
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
      {/* Shortcut: applies a whole configuration at once, so it sits above
          the numbered steps rather than inside them. */}
      <GuidedPresets onComplete={onOptimizeSuccess} />

      {/* ── 1. Design storm ──────────────────────────────────────────── */}
      <Step
        index={1}
        title="Design storm"
        icon={<IconRainfall size={14} />}
        aside={
          <span
            className="badge"
            style={{
              background: 'var(--gov-grey-100)',
              color: storm.tone,
              borderColor: 'currentColor',
            }}
          >
            {storm.label}
          </span>
        }
      >
        <label className="gov-label" htmlFor="rainfall-slider">
          24-hour rainfall depth
        </label>
        <div
          style={{
            display: 'flex',
            alignItems: 'baseline',
            gap: 'var(--space-2)',
            marginBottom: 'var(--space-2)',
          }}
        >
          <span
            className="tabular"
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: 'var(--font-size-2xl)',
              fontWeight: 700,
              color: 'var(--gov-navy-900)',
            }}
          >
            {rainfallMm}
          </span>
          <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--clr-text-secondary)' }}>
            mm
          </span>
        </div>
        <input
          id="rainfall-slider"
          type="range"
          min={50}
          max={300}
          step={10}
          value={rainfallMm}
          onChange={(e) => setRainfallMm(Number(e.target.value))}
          aria-valuetext={`${rainfallMm} millimetres. ${storm.label}`}
        />
        <div
          className="tabular gov-hint"
          style={{ display: 'flex', justifyContent: 'space-between', marginTop: '2px' }}
        >
          <span>50 mm</span>
          <span>300 mm</span>
        </div>
      </Step>

      {/* ── 2. Sanctioned capital budget ─────────────────────────────── */}
      <Step index={2} title="Sanctioned capital budget" icon={<IconBudget size={14} />}>
        <label className="gov-label" htmlFor="budget-custom-input">
          Ceiling available for this allocation
        </label>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <span
            aria-hidden="true"
            style={{ fontSize: 'var(--font-size-lg)', color: 'var(--clr-text-secondary)' }}
          >
            ₹
          </span>
          <input
            id="budget-custom-input"
            type="number"
            min="0.1"
            step="0.5"
            className="gov-input"
            value={budgetFocused ? budgetDraft : budgetCr.toFixed(1)}
            onFocus={() => {
              setBudgetFocused(true)
              setBudgetDraft(budgetCr.toFixed(1))
            }}
            onChange={(e) => setBudgetDraft(e.target.value)}
            onBlur={commitBudget}
            onKeyDown={(e) => {
              if (e.key === 'Enter') (e.target as HTMLInputElement).blur()
            }}
            style={{ textAlign: 'right', fontSize: 'var(--font-size-lg)', fontWeight: 700 }}
          />
          <span
            style={{
              fontSize: 'var(--font-size-sm)',
              color: 'var(--clr-text-secondary)',
              whiteSpace: 'nowrap',
            }}
          >
            Crore
          </span>
        </div>

        <div
          role="group"
          aria-label="Common budget ceilings"
          style={{ display: 'flex', gap: '5px', marginTop: 'var(--space-2)' }}
        >
          {BUDGET_PRESETS.map((preset) => (
            <button
              key={preset.label}
              type="button"
              id={`budget-preset-${preset.label.replace(/[₹ ]/g, '')}`}
              className="btn btn-ghost btn-sm"
              aria-pressed={budget === preset.value}
              onClick={() => {
                setBudget(preset.value)
                setBudgetDraft((preset.value / 10_000_000).toFixed(1))
              }}
              style={{ flex: 1 }}
            >
              {preset.label}
            </button>
          ))}
        </div>

        <button
          id="find-best-strategy-btn"
          type="button"
          className="btn btn-primary btn-block"
          onClick={handleOptimize}
          disabled={isBusy || budget <= 0}
          style={{ marginTop: 'var(--space-3)' }}
        >
          {isOptimizing ? (
            <>
              <span className="spinner" style={{ width: '13px', height: '13px' }} />
              Computing allocation…
            </>
          ) : (
            'Generate investment options'
          )}
        </button>
      </Step>

      {/* ── 3. Schedule of candidate works ───────────────────────────── */}
      <Step
        index={3}
        title="Schedule of candidate works"
        icon={<IconWorks size={14} />}
        aside={
          <span className="badge badge-muted">
            {selectedInterventionIds.size} of {interventions.length} selected
          </span>
        }
      >
        {interventions.length === 0 ? (
          <p className="gov-hint">The works register has not been loaded.</p>
        ) : (
          <>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: 'var(--space-2)',
              }}
            >
              <span className="gov-hint">
                Select works to appraise manually, or use a template above.
              </span>
              {selectedInterventionIds.size > 0 && (
                <button type="button" className="btn btn-ghost btn-sm" onClick={clearInterventions}>
                  Clear selection
                </button>
              )}
            </div>

            <ul
              style={{
                listStyle: 'none',
                maxHeight: '260px',
                overflowY: 'auto',
                border: '1px solid var(--clr-border)',
              }}
            >
              {interventions.map((item) => (
                <WorkRow
                  key={item.id}
                  item={item}
                  selected={selectedInterventionIds.has(item.id)}
                  onToggle={() => toggleIntervention(item.id)}
                  onLocate={() => setFocusCoordinates([item.node_lon, item.node_lat])}
                />
              ))}
            </ul>
          </>
        )}
      </Step>

      {/* ── 4. Run the assessment ────────────────────────────────────── */}
      {selectedInterventionIds.size > 0 && (
        <Step index={4} title="Run consequence simulation" icon={<IconWater size={14} />}>
          <dl className="gov-dl" style={{ marginBottom: 'var(--space-3)' }}>
            <dt>Works selected</dt>
            <dd>{selectedInterventionIds.size}</dd>
            <dt>Estimated cost</dt>
            <dd style={{ color: overBudget ? 'var(--gov-red-700)' : undefined }}>
              {formatCost(totalCost)}
            </dd>
            <dt>Budget ceiling</dt>
            <dd>{formatCost(budget)}</dd>
          </dl>

          {overBudget && (
            <div className="gov-notice gov-notice--warn" style={{ marginBottom: 'var(--space-3)' }}>
              <IconWorks size={13} className="gov-notice__icon" />
              <span>
                The selected works exceed the sanctioned ceiling by{' '}
                {formatCost(totalCost - budget)}. The simulation will still run;
                the allocation tool will not propose this combination.
              </span>
            </div>
          )}

          <button
            id="run-simulation-btn"
            type="button"
            className="btn btn-primary btn-block"
            onClick={handleSimulate}
            disabled={isBusy}
          >
            {isSimulating ? (
              <>
                <span className="spinner" style={{ width: '13px', height: '13px' }} />
                Simulating…
              </>
            ) : (
              'Run consequence simulation'
            )}
          </button>
        </Step>
      )}
    </div>
  )
}
