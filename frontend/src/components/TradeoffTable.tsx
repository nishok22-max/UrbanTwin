/**
 * TradeoffTable — investment option analysis.
 *
 * The three candidate allocations are presented as a comparison table rather
 * than as ranked cards: officers comparing options need to read down a column,
 * which cards make impossible. Selecting a row makes that option active on the
 * map.
 *
 * The radar chart is retained as a secondary view of the same figures, since
 * the shape of a multi-objective trade-off is hard to read from numbers alone.
 */
import React, { useMemo } from 'react'
import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from 'recharts'
import { useStore } from '../state/store'
import type { RankedScenario } from '../api/client'
import { IconTable, IconCheck, IconInfo, IconDocument } from './GovIcons'
import {
  VALIDATION_CHECK_COUNT,
  VALIDATION_PROPERTIES,
  VALIDATION_SEED,
} from '../validation'

function formatCrore(n: number): string {
  if (n >= 10_000_000) return `₹${(n / 10_000_000).toFixed(2)} Cr`
  if (n >= 100_000) return `₹${(n / 100_000).toFixed(1)} L`
  return `₹${n.toLocaleString('en-IN')}`
}

function formatPop(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)} M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)} K`
  return `${Math.round(n)}`
}

/** Institutional series colours: navy, teal, ochre — distinguishable in
 *  greyscale as well as in colour. */
const SERIES_COLOURS = ['#0b2545', '#1f7a8c', '#c8781a'] as const

const FALLBACK_LETTERS = ['A', 'B', 'C', 'D', 'E'] as const

/**
 * Label a bundle the same way the backend does when it writes the
 * justification prose (`bundle_A` -> "Strategy A", see
 * services/explanation/templates/recommendation.j2). Deriving the letter from
 * the identifier rather than from the rank keeps the table and the prose in
 * agreement even if the two ever order bundles differently.
 */
function optionLabel(scenario: RankedScenario): string {
  const match = /^bundle_(.+)$/.exec(scenario.scenario_id)
  if (match) return `Strategy ${match[1]}`
  return `Strategy ${FALLBACK_LETTERS[(scenario.rank - 1) % FALLBACK_LETTERS.length]}`
}

const RADAR_AXES = [
  { key: 'risk', label: 'Risk reduction' },
  { key: 'population', label: 'Population' },
  { key: 'service', label: 'Service' },
  { key: 'mobility', label: 'Mobility' },
] as const

function buildRadarData(ranked: RankedScenario[]) {
  const POP_MAX = 80_000
  const MOB_MAX = 30

  return RADAR_AXES.map((axis) => {
    const entry: Record<string, number | string> = { label: axis.label }
    ranked.forEach((s, i) => {
      const c = s.consequence
      let value = 0
      if (axis.key === 'risk') value = c.risk_reduction.value * 100
      if (axis.key === 'population')
        value = Math.min(c.population_protected.value / POP_MAX, 1) * 100
      if (axis.key === 'service') value = c.service_availability * 100
      if (axis.key === 'mobility')
        value = Math.max(0, 1 - c.mobility_disruption_min.value / MOB_MAX) * 100
      entry[`s${i + 1}`] = Math.round(value)
    })
    return entry
  })
}

/** <th scope="row"> carries row semantics but must not inherit the navy
 *  column-header styling. */
const rowHeaderStyle: React.CSSProperties = {
  background: 'transparent',
  color: 'var(--clr-text-primary)',
  textTransform: 'none',
  letterSpacing: 0,
  fontSize: 'var(--font-size-xs)',
  fontWeight: 400,
  borderRight: 'none',
  borderTop: '1px solid var(--clr-border)',
  whiteSpace: 'normal',
  padding: '6px',
  verticalAlign: 'top',
}

export const TradeoffTable: React.FC = () => {
  const recommendation = useStore((s) => s.recommendation)
  const activeStrategy = useStore((s) => s.activeStrategy)
  const setActiveStrategy = useStore((s) => s.setActiveStrategy)
  const status = useStore((s) => s.status)

  const radarData = useMemo(
    () => (recommendation?.ranked.length ? buildRadarData(recommendation.ranked) : []),
    [recommendation]
  )

  if (status === 'optimizing' || status === 'ai-reasoning') {
    return (
      <div className="gov-notice gov-notice--info" role="status" aria-live="polite">
        <span className="spinner gov-notice__icon" />
        <div>
          <strong>Computing allocation…</strong>
          <div>
            Solving the budget-constrained selection and evaluating candidate
            bundles across four objectives.
          </div>
        </div>
      </div>
    )
  }

  if (!recommendation) {
    return (
      <section className="gov-panel">
        <div className="gov-panel__header">
          <h2 className="gov-panel__title">
            <IconTable size={14} />
            Investment option analysis
          </h2>
        </div>
        <div className="gov-panel__body">
          <div className="gov-notice">
            <IconInfo size={15} className="gov-notice__icon" />
            <div>
              No options have been generated. Set a sanctioned budget under{' '}
              <strong>Scenario</strong> and select{' '}
              <strong>Generate investment options</strong>, or apply a standard
              appraisal template.
            </div>
          </div>
        </div>
      </section>
    )
  }

  const { ranked, explanation, budget } = recommendation
  const selected = activeStrategy ?? ranked[0]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
      {/* ── Recommendation ───────────────────────────────────────────── */}
      <div className="gov-notice gov-notice--success">
        <IconCheck size={15} className="gov-notice__icon" />
        <div>
          <strong>
            {optionLabel(ranked[0])} is recommended within the{' '}
            {formatCrore(budget)} ceiling.
          </strong>
          <div>
            {ranked[0].intervention_ids.length} works at {formatCrore(ranked[0].total_cost)},
            leaving {formatCrore(Math.max(0, budget - ranked[0].total_cost))} uncommitted.
          </div>
        </div>
      </div>

      {/* ── Comparison table ─────────────────────────────────────────── */}
      <div className="gov-table-wrap">
      <table className="gov-table">
        <caption>Ranked options — select a row to show it on the map</caption>
        <thead>
          <tr>
            <th scope="col">Option</th>
            <th scope="col" className="num">
              Cost
            </th>
            <th scope="col" className="num">
              Risk reduction
            </th>
            <th scope="col" className="num">
              Population
            </th>
            <th scope="col" className="num">
              Score
            </th>
          </tr>
        </thead>
        <tbody>
          {ranked.map((option) => {
            const isSelected = selected?.scenario_id === option.scenario_id
            const c = option.consequence
            return (
              <tr
                key={option.scenario_id}
                id={`strategy-card-${option.rank}`}
                className={`is-selectable ${isSelected ? 'is-selected' : ''}`}
                onClick={() => setActiveStrategy(option)}
              >
                <th scope="row" style={rowHeaderStyle}>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      setActiveStrategy(option)
                    }}
                    aria-pressed={isSelected}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      background: 'none',
                      border: 'none',
                      padding: 0,
                      font: 'inherit',
                      color: 'inherit',
                      cursor: 'pointer',
                      textAlign: 'left',
                    }}
                  >
                    <span
                      aria-hidden="true"
                      style={{
                        width: '10px',
                        height: '10px',
                        background: SERIES_COLOURS[(option.rank - 1) % SERIES_COLOURS.length],
                        flexShrink: 0,
                      }}
                    />
                    <span style={{ fontWeight: 700 }}>{optionLabel(option)}</span>
                    <span className="sr-only">
                      {isSelected ? '. Currently shown on the map' : '. Show on the map'}
                    </span>
                  </button>
                  <span
                    style={{
                      display: 'block',
                      fontSize: '10px',
                      color: 'var(--clr-text-secondary)',
                      marginTop: '2px',
                      fontWeight: 400,
                    }}
                  >
                    {option.intervention_ids.length} works
                    {option.rank === 1 ? ' · recommended' : ''}
                  </span>
                </th>
                <td className="num" style={{ fontFamily: 'var(--font-mono)', whiteSpace: 'nowrap' }}>
                  {formatCrore(option.total_cost)}
                </td>
                <td className="num" style={{ fontFamily: 'var(--font-mono)' }}>
                  {(c.risk_reduction.value * 100).toFixed(1)}%
                </td>
                <td className="num" style={{ fontFamily: 'var(--font-mono)' }}>
                  {formatPop(c.population_protected.value)}
                </td>
                <td className="num" style={{ fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
                  {(option.score * 100).toFixed(1)}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
      </div>

      {/* ── Selected option detail ───────────────────────────────────── */}
      {selected && (
        <section className="gov-panel">
          <div className="gov-panel__header">
            <h2 className="gov-panel__title">{optionLabel(selected)} — detail</h2>
            <span className="badge badge-primary">Shown on map</span>
          </div>
          <div className="gov-panel__body">
            <dl className="gov-dl">
              <dt>Works included</dt>
              <dd>{selected.intervention_ids.length}</dd>
              <dt>Capital cost</dt>
              <dd>{formatCrore(selected.total_cost)}</dd>
              <dt>Budget utilisation</dt>
              <dd>{((selected.total_cost / budget) * 100).toFixed(0)}%</dd>
              <dt>Population protected</dt>
              <dd>{formatPop(selected.consequence.population_protected.value)}</dd>
              <dt>Population per ₹ Cr</dt>
              <dd>
                {selected.total_cost > 0
                  ? Math.round(
                      selected.consequence.population_protected.value /
                        (selected.total_cost / 1e7)
                    ).toLocaleString('en-IN')
                  : '—'}
              </dd>
              <dt>Added journey time</dt>
              <dd>{selected.consequence.mobility_disruption_min.value.toFixed(1)} min</dd>
              <dt>Service availability</dt>
              <dd>{(selected.consequence.service_availability * 100).toFixed(0)}%</dd>
            </dl>
          </div>
        </section>
      )}

      {/* ── Trade-off profile ────────────────────────────────────────── */}
      {radarData.length > 0 && ranked.length > 1 && (
        <section className="gov-panel">
          <div className="gov-panel__header">
            <h2 className="gov-panel__title">Objective trade-off profile</h2>
          </div>
          <div className="gov-panel__body">
            <p className="gov-hint" style={{ marginBottom: 'var(--space-2)' }}>
              Each axis is normalised to 0–100. A larger enclosed area indicates
              broader performance, not a better option — weightings decide that.
            </p>
            <div style={{ height: '215px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={radarData} outerRadius="68%">
                  <PolarGrid stroke="var(--gov-grey-300)" />
                  <PolarAngleAxis
                    dataKey="label"
                    tick={{ fill: 'var(--gov-grey-600)', fontSize: 10, fontWeight: 600 }}
                  />
                  <PolarRadiusAxis
                    domain={[0, 100]}
                    tick={{ fill: 'var(--gov-grey-500)', fontSize: 9 }}
                    axisLine={false}
                  />
                  {ranked.map((option, i) => (
                    <Radar
                      key={option.scenario_id}
                      name={optionLabel(option)}
                      dataKey={`s${i + 1}`}
                      stroke={SERIES_COLOURS[i % SERIES_COLOURS.length]}
                      fill={SERIES_COLOURS[i % SERIES_COLOURS.length]}
                      fillOpacity={0.12}
                      strokeWidth={2}
                    />
                  ))}
                  <Legend
                    wrapperStyle={{ fontSize: '11px', color: 'var(--gov-grey-600)' }}
                    iconType="square"
                  />
                  <Tooltip
                    contentStyle={{
                      background: 'var(--gov-white)',
                      border: '1px solid var(--gov-grey-500)',
                      borderRadius: '2px',
                      fontSize: '11px',
                      color: 'var(--gov-grey-900)',
                    }}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </section>
      )}

      {/* ── Basis of recommendation ──────────────────────────────────── */}
      <section className="gov-panel">
        <div className="gov-panel__header">
          <h2 className="gov-panel__title">
            <IconDocument size={14} />
            Basis of recommendation
          </h2>
          <span className="badge badge-muted">
            {recommendation.explanation_source === 'llm' ? 'Generated' : 'Template'}
          </span>
        </div>
        <div className="gov-panel__body">
          <p style={{ fontSize: 'var(--font-size-xs)', lineHeight: 1.65 }}>
            {explanation || 'No written justification was returned for this allocation.'}
          </p>
        </div>
      </section>

      {/* ── Validation ───────────────────────────────────────────────── */}
      <div className="validation-banner">
        <IconCheck size={15} className="gov-notice__icon" />
        <div>
          <div>
            Synthetic-twin validation: {VALIDATION_CHECK_COUNT} of{' '}
            {VALIDATION_CHECK_COUNT} checks passed
          </div>
          <div style={{ fontWeight: 400, marginTop: '2px' }}>
            {VALIDATION_PROPERTIES}. Seed {VALIDATION_SEED}, reproducible.
          </div>
        </div>
      </div>

      <p className="tabular gov-hint" style={{ textAlign: 'center' }}>
        Simulation &lt; 2 s · allocation &lt; 5 s · 50 Monte-Carlo trials · OR-Tools branch and bound
      </p>
    </div>
  )
}
