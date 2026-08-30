/**
 * ResultPanel — consequence assessment for the selected schedule of works.
 *
 * Presents modelled outcomes as a measures table with explicit uncertainty
 * intervals rather than as headline figures. Every quantity is shown with its
 * 10th–90th percentile band, because a single point estimate from a 50-trial
 * Monte-Carlo would overstate the precision available.
 */
import React from 'react'
import { useStore } from '../state/store'
import { IconChart, IconWater, IconInfo, IconCheck } from './GovIcons'

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)} M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)} K`
  return n.toFixed(0)
}

function formatCost(n: number): string {
  if (n >= 10_000_000) return `₹${(n / 10_000_000).toFixed(2)} Cr`
  if (n >= 100_000) return `₹${(n / 100_000).toFixed(1)} L`
  return `₹${n.toLocaleString('en-IN')}`
}

const CONFIDENCE_LABEL: Record<string, string> = {
  high: 'High',
  medium: 'Medium',
  low: 'Low',
}

export const ResultPanel: React.FC = () => {
  const result = useStore((s) => s.simulationResult)
  const status = useStore((s) => s.status)

  if (status === 'simulating') {
    return (
      <div className="gov-notice gov-notice--info" role="status" aria-live="polite">
        <span className="spinner gov-notice__icon" />
        <div>
          <strong>Simulation in progress</strong>
          <div>Propagating inundation through the network and running trials.</div>
        </div>
      </div>
    )
  }

  if (!result) {
    return (
      <section className="gov-panel">
        <div className="gov-panel__header">
          <h2 className="gov-panel__title">
            <IconChart size={14} />
            Consequence assessment
          </h2>
        </div>
        <div className="gov-panel__body">
          <div className="gov-notice">
            <IconInfo size={15} className="gov-notice__icon" />
            <div>
              No assessment has been run. Select works under{' '}
              <strong>Scenario</strong> and run a consequence simulation, or
              apply a standard appraisal template.
            </div>
          </div>
        </div>
      </section>
    )
  }

  const c = result.consequence
  const nodesAvoided = c.nodes_flooded_baseline - c.nodes_flooded_with_intervention
  const floodReductionPct =
    c.nodes_flooded_baseline > 0 ? (nodesAvoided / c.nodes_flooded_baseline) * 100 : 0

  const measures = [
    {
      measure: 'Flood risk reduction',
      value: `${(c.risk_reduction.value * 100).toFixed(1)}%`,
      interval: `${(c.risk_reduction.low * 100).toFixed(1)} – ${(c.risk_reduction.high * 100).toFixed(1)}%`,
    },
    {
      measure: 'Population protected',
      value: formatNumber(c.population_protected.value),
      interval: `${formatNumber(c.population_protected.low)} – ${formatNumber(c.population_protected.high)}`,
    },
    {
      measure: 'Added journey time',
      value: `${c.mobility_disruption_min.value.toFixed(1)} min`,
      interval: `${c.mobility_disruption_min.low.toFixed(1)} – ${c.mobility_disruption_min.high.toFixed(1)} min`,
    },
    {
      measure: 'Service availability',
      value: `${(c.service_availability * 100).toFixed(0)}%`,
      interval: 'Deterministic',
    },
  ]

  const comparison = [
    {
      label: 'Without works',
      value: c.nodes_flooded_baseline,
      colour: 'var(--gov-red-700)',
    },
    {
      label: 'With works',
      value: c.nodes_flooded_with_intervention,
      colour: 'var(--gov-green-700)',
    },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
      {/* ── Summary ──────────────────────────────────────────────────── */}
      <div className={`gov-notice ${nodesAvoided > 0 ? 'gov-notice--success' : 'gov-notice--warn'}`}>
        {nodesAvoided > 0 ? (
          <IconCheck size={15} className="gov-notice__icon" />
        ) : (
          <IconInfo size={15} className="gov-notice__icon" />
        )}
        <div>
          <strong>
            {nodesAvoided > 0
              ? `${nodesAvoided} junctions kept clear of flooding`
              : 'No reduction in flooded junctions'}
          </strong>
          <div>
            {nodesAvoided > 0
              ? `A ${floodReductionPct.toFixed(floodReductionPct < 10 ? 1 : 0)}% reduction against the do-nothing baseline at the modelled design storm.`
              : 'The selected works do not alter flooding extent at this design storm.'}
          </div>
        </div>
      </div>

      {/* ── Measures ─────────────────────────────────────────────────── */}
      <div className="gov-table-wrap">
      <table className="gov-table">
        <caption>Modelled measures</caption>
        <thead>
          <tr>
            <th scope="col">Measure</th>
            <th scope="col" className="num">
              Estimate
            </th>
            <th scope="col" className="num">
              80% interval
            </th>
          </tr>
        </thead>
        <tbody>
          {measures.map((row) => (
            <tr key={row.measure}>
              <th
                scope="row"
                style={{
                  background: 'transparent',
                  color: 'var(--clr-text-primary)',
                  textTransform: 'none',
                  letterSpacing: 0,
                  fontSize: 'var(--font-size-xs)',
                  fontWeight: 600,
                  borderRight: 'none',
                  borderTop: '1px solid var(--clr-border)',
                  whiteSpace: 'normal',
                }}
              >
                {row.measure}
              </th>
              <td
                className="num"
                style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, whiteSpace: 'nowrap' }}
              >
                {row.value}
              </td>
              <td
                className="num"
                style={{
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--clr-text-secondary)',
                  whiteSpace: 'nowrap',
                }}
              >
                {row.interval}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>

      {/* ── Flooding extent ──────────────────────────────────────────── */}
      <section className="gov-panel">
        <div className="gov-panel__header">
          <h2 className="gov-panel__title">
            <IconWater size={14} />
            Flooded junctions
          </h2>
        </div>
        <div className="gov-panel__body" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          {comparison.map((row) => {
            const pct =
              c.nodes_flooded_baseline > 0 ? (row.value / c.nodes_flooded_baseline) * 100 : 0
            return (
              <div key={row.label}>
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'baseline',
                    marginBottom: '3px',
                  }}
                >
                  <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 600 }}>
                    {row.label}
                  </span>
                  <span
                    className="tabular"
                    style={{
                      fontSize: 'var(--font-size-xs)',
                      fontFamily: 'var(--font-mono)',
                      color: row.colour,
                      fontWeight: 700,
                    }}
                  >
                    {row.value} junctions ({pct.toFixed(1)}%)
                  </span>
                </div>
                <div
                  className="progress-bar"
                  role="img"
                  aria-label={`${row.label}: ${row.value} flooded junctions, ${pct.toFixed(1)} percent of the baseline`}
                >
                  <div
                    className="progress-bar-fill"
                    style={{ width: `${pct}%`, background: row.colour }}
                  />
                </div>
              </div>
            )
          })}

          <dl className="gov-dl">
            <dt>Roads impassable (baseline)</dt>
            <dd>{c.roads_blocked_baseline}</dd>
            <dt>Roads impassable (with works)</dt>
            <dd
              style={{
                color:
                  c.roads_blocked_with_intervention === 0
                    ? 'var(--gov-green-700)'
                    : 'var(--gov-red-700)',
              }}
            >
              {c.roads_blocked_with_intervention}
            </dd>
            <dt>Cost of works</dt>
            <dd>{c.cost > 0 ? formatCost(c.cost) : '—'}</dd>
          </dl>
        </div>
      </section>

      {/* ── Provenance ───────────────────────────────────────────────── */}
      <section className="gov-panel">
        <div className="gov-panel__header">
          <h2 className="gov-panel__title">Basis of assessment</h2>
          <span
            className="badge badge-muted"
            style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}
          >
            <span className={`confidence-dot confidence-${result.confidence}`} />
            {CONFIDENCE_LABEL[result.confidence] ?? result.confidence} confidence
          </span>
        </div>
        <div className="gov-panel__body">
          <dl className="gov-dl">
            <dt>Monte-Carlo trials</dt>
            <dd>{(result.meta['n_mc_trials'] as number) ?? '—'}</dd>
            <dt>Cascade nodes evaluated</dt>
            <dd>{result.cascade_path.length}</dd>
            <dt>Dominant uncertainty</dt>
            <dd style={{ fontFamily: 'var(--font-sans)', fontWeight: 400 }}>
              {result.dominant_uncertainty.replace(/_/g, ' ')}
            </dd>
            <dt>Volume conservation check</dt>
            <dd
              style={{
                color: result.conservation_ok ? 'var(--gov-green-700)' : 'var(--gov-red-700)',
                fontFamily: 'var(--font-sans)',
                fontWeight: 600,
              }}
            >
              {result.conservation_ok ? 'Passed' : 'Failed'}
            </dd>
            <dt>Computation time</dt>
            <dd>{result.computation_time_ms.toFixed(0)} ms</dd>
          </dl>

          {result.fallback_used && (
            <div className="gov-notice gov-notice--warn" style={{ marginTop: 'var(--space-3)' }}>
              <IconInfo size={13} className="gov-notice__icon" />
              <span>
                Produced by the physical model rather than the learned surrogate.
                Results remain valid; runtime is longer.
              </span>
            </div>
          )}
        </div>
      </section>
    </div>
  )
}
