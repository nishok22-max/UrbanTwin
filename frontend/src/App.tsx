/**
 * Root application component.
 *
 * Layout — government portal chrome (GovShell) wrapping a two-column working
 * area:
 *
 *   ┌──────────────────────────────────────────────────────────┐
 *   │ utility strip · masthead · primary nav · breadcrumb       │
 *   ├──────────────────────┬───────────────────────────────────┤
 *   │ working panel (400px)│  map (persists across sections)   │
 *   │  Scenario            │                                   │
 *   │  Assessment          │  locality nav · legend · record    │
 *   │  Advisory            │                                   │
 *   │  About               │                                   │
 *   ├──────────────────────┴───────────────────────────────────┤
 *   │ footer — disclaimer, sources, method, last updated        │
 *   └──────────────────────────────────────────────────────────┘
 *
 * The three former sidebar tabs are promoted into the primary navigation, so
 * the section structure is visible at the top level rather than buried in the
 * panel. The map stays mounted in every section.
 */
import React, { useEffect, useMemo, useState } from 'react'
import { api } from './api/client'
import { useStore } from './state/store'
import { MapView } from './components/MapView'
import { ScenarioBuilder } from './components/ScenarioBuilder'
import { ResultPanel } from './components/ResultPanel'
import { TradeoffTable } from './components/TradeoffTable'
import { CascadeLegend } from './components/CascadeLayer'
import { GovShell } from './components/GovShell'
import type { ShellSection } from './components/GovShell'
import {
  IconWorks,
  IconChart,
  IconTable,
  IconInfo,
  IconAlert,
  IconCheck,
} from './components/GovIcons'
import {
  VALIDATION_CHECK_COUNT,
  VALIDATION_PROPERTIES,
  VALIDATION_SEED,
} from './validation'
import './styles/index.css'

type SectionId = 'scenario' | 'assessment' | 'advisory' | 'about'

const SECTION_LEAF: Record<SectionId, string> = {
  scenario: 'Scenario configuration',
  assessment: 'Consequence assessment',
  advisory: 'Investment advisory',
  about: 'About this system',
}

// ---------------------------------------------------------------------------
// Masthead aside — operational status and loaded dataset
// ---------------------------------------------------------------------------

const STATUS_TEXT: Record<string, { label: string; tone: string }> = {
  idle: { label: 'Initialising', tone: 'var(--gov-grey-500)' },
  'loading-graph': { label: 'Loading network', tone: 'var(--gov-saffron-700)' },
  'loading-interventions': { label: 'Loading works register', tone: 'var(--gov-saffron-700)' },
  simulating: { label: 'Simulation in progress', tone: 'var(--gov-saffron-700)' },
  optimizing: { label: 'Optimisation in progress', tone: 'var(--gov-saffron-700)' },
  'ai-reasoning': { label: 'Optimisation in progress', tone: 'var(--gov-saffron-700)' },
  ready: { label: 'Ready', tone: 'var(--gov-green-700)' },
  error: { label: 'Service unavailable', tone: 'var(--gov-red-700)' },
}

const MastheadAside: React.FC = () => {
  const graphData = useStore((s) => s.graphData)
  const status = useStore((s) => s.status)
  const meta = STATUS_TEXT[status] ?? STATUS_TEXT.idle

  return (
    <div style={{ display: 'flex', alignItems: 'stretch', gap: 'var(--space-4)' }}>
      {graphData && (
        <dl
          style={{
            display: 'flex',
            gap: 'var(--space-4)',
            paddingRight: 'var(--space-4)',
            borderRight: '1px solid var(--clr-border)',
            margin: 0,
          }}
        >
          {[
            { term: 'Nodes', value: graphData.meta['node_count'] as number },
            { term: 'Links', value: graphData.meta['edge_count'] as number },
          ].map((item) => (
            <div key={item.term} style={{ textAlign: 'right' }}>
              <dt
                style={{
                  fontSize: '10px',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  color: 'var(--clr-text-secondary)',
                  fontWeight: 600,
                }}
              >
                {item.term}
              </dt>
              <dd
                className="tabular"
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: 'var(--font-size-sm)',
                  fontWeight: 700,
                  color: 'var(--gov-navy-900)',
                }}
              >
                {Number(item.value ?? 0).toLocaleString('en-IN')}
              </dd>
            </div>
          ))}
        </dl>
      )}

      {/* Status is announced politely so screen reader users hear pipeline
          transitions without losing their place. */}
      <div
        role="status"
        aria-live="polite"
        style={{ display: 'flex', alignItems: 'center', gap: '7px', minWidth: '150px' }}
      >
        <span className="status-dot" style={{ background: meta.tone }} />
        <span
          style={{
            fontSize: 'var(--font-size-xs)',
            fontWeight: 600,
            color: 'var(--clr-text-secondary)',
          }}
        >
          {meta.label}
        </span>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// About — method, provenance and limitations
// ---------------------------------------------------------------------------

const AboutPanel: React.FC = () => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
    <section className="gov-panel">
      <div className="gov-panel__header">
        <h2 className="gov-panel__title">
          <IconInfo size={14} />
          Purpose
        </h2>
      </div>
      <div className="gov-panel__body">
        <p style={{ fontSize: 'var(--font-size-xs)', lineHeight: 1.6 }}>
          This system estimates the cascading consequences of candidate flood
          mitigation works across the T. Nagar road and drainage network, and
          ranks affordable combinations of those works against a sanctioned
          capital budget. It is a decision-support aid: outputs inform
          engineering appraisal and are not a substitute for it.
        </p>
      </div>
    </section>

    <section className="gov-panel">
      <div className="gov-panel__header">
        <h2 className="gov-panel__title">Method</h2>
      </div>
      <div className="gov-panel__body">
        <dl className="gov-dl">
          {[
            ['Network model', 'Directed graph, 2,296 nodes / 5,481 links'],
            ['Hydrology', 'Depth–elevation cascade, up to 3 hops'],
            ['Uncertainty', 'Monte-Carlo, 50 trials, 10th–90th percentile'],
            ['Allocation', 'OR-Tools 0-1 knapsack, branch and bound'],
            ['Ranking', 'Weighted multi-objective composite score'],
          ].map(([term, value]) => (
            <React.Fragment key={term}>
              <dt>{term}</dt>
              <dd style={{ fontFamily: 'var(--font-sans)', fontWeight: 400 }}>{value}</dd>
            </React.Fragment>
          ))}
        </dl>
      </div>
    </section>

    <section className="gov-panel">
      <div className="gov-panel__header">
        <h2 className="gov-panel__title">Data sources</h2>
      </div>
      <div className="gov-panel__body">
        <ul
          style={{
            fontSize: 'var(--font-size-xs)',
            lineHeight: 1.7,
            paddingLeft: 'var(--space-4)',
            color: 'var(--clr-text-primary)',
          }}
        >
          <li>Road network and junction geometry — OpenStreetMap</li>
          <li>Terrain elevation — public digital elevation model</li>
          <li>Population served — modelled allocation to network nodes</li>
          <li>Unit costs — indicative schedule of rates</li>
        </ul>
      </div>
    </section>

    <div className="gov-notice gov-notice--warn">
      <IconAlert size={15} className="gov-notice__icon" />
      <div>
        <strong>Limitations.</strong> The hydrological model is simplified and
        does not represent sub-surface drainage capacity, tidal backflow, or
        pumping failure. Cost figures are indicative. Results should not be
        cited in a statutory process.
      </div>
    </div>

    <div className="gov-notice gov-notice--success">
      <IconCheck size={15} className="gov-notice__icon" />
      <div>
        <strong>Validation.</strong> {VALIDATION_CHECK_COUNT} of{' '}
        {VALIDATION_CHECK_COUNT} automated checks pass against a synthetic twin.{' '}
        {VALIDATION_PROPERTIES}. Seed {VALIDATION_SEED}, reproducible.
      </div>
    </div>
  </div>
)

// ---------------------------------------------------------------------------
// Overlays
// ---------------------------------------------------------------------------

const LoadingOverlay: React.FC<{ status: string }> = ({ status }) => (
  <div
    style={{
      position: 'absolute',
      inset: 0,
      background: 'rgba(244, 246, 249, 0.94)',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 200,
      gap: 'var(--space-3)',
    }}
  >
    <div className="spinner" style={{ width: '28px', height: '28px' }} />
    <p style={{ fontSize: 'var(--font-size-base)', fontWeight: 600, color: 'var(--gov-navy-900)' }}>
      {status === 'loading-graph'
        ? 'Loading T. Nagar infrastructure network…'
        : 'Loading schedule of candidate works…'}
    </p>
    <p className="tabular gov-hint">2,296 nodes · 5,481 links</p>
  </div>
)

const ErrorOverlay: React.FC<{ message: string | null }> = ({ message }) => (
  <div
    className="gov-notice gov-notice--error"
    role="alert"
    style={{
      position: 'absolute',
      top: 'var(--space-3)',
      left: '50%',
      transform: 'translateX(-50%)',
      zIndex: 200,
      maxWidth: '540px',
      background: 'var(--gov-white)',
      boxShadow: 'var(--shadow-lg)',
    }}
  >
    <IconAlert size={16} className="gov-notice__icon" />
    <div>
      <strong>The analysis service is not responding.</strong>
      <div style={{ marginTop: '2px' }}>
        {message ?? 'Confirm that the backend service is running on port 8000, then reload.'}
      </div>
    </div>
  </div>
)

// ---------------------------------------------------------------------------
// App
// ---------------------------------------------------------------------------

export const App: React.FC = () => {
  const setGraphData = useStore((s) => s.setGraphData)
  const setInterventions = useStore((s) => s.setInterventions)
  const setStatus = useStore((s) => s.setStatus)
  const setError = useStore((s) => s.setError)
  const simulationResult = useStore((s) => s.simulationResult)
  const recommendation = useStore((s) => s.recommendation)
  const status = useStore((s) => s.status)
  const error = useStore((s) => s.error)

  const [activeSection, setActiveSection] = useState<SectionId>('scenario')

  // Advance to the section that now holds output.
  useEffect(() => {
    if (simulationResult && !recommendation) setActiveSection('assessment')
  }, [simulationResult, recommendation])

  useEffect(() => {
    if (recommendation) setActiveSection('advisory')
  }, [recommendation])

  // Load the network and works register on mount.
  useEffect(() => {
    async function loadData() {
      setStatus('loading-graph')
      try {
        const graph = await api.getGraph()
        setGraphData(graph)
        setStatus('loading-interventions')
        const { interventions } = await api.getInterventions()
        setInterventions(interventions)
        setStatus('ready')
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : 'Failed to load data')
        setStatus('error')
      }
    }
    loadData()
  }, [setGraphData, setInterventions, setStatus, setError])

  const sections: ShellSection[] = useMemo(
    () => [
      {
        id: 'scenario',
        label: 'Scenario',
        description: 'Configure design storm, capital budget and candidate works',
        icon: <IconWorks size={15} />,
      },
      {
        id: 'assessment',
        label: 'Assessment',
        description: 'Modelled consequences of the selected works',
        icon: <IconChart size={15} />,
        flagged: Boolean(simulationResult),
      },
      {
        id: 'advisory',
        label: 'Advisory',
        description: 'Ranked investment options and the recommended allocation',
        icon: <IconTable size={15} />,
        flagged: Boolean(recommendation),
      },
      {
        id: 'about',
        label: 'About',
        description: 'Method, data sources and limitations',
        icon: <IconInfo size={15} />,
      },
    ],
    [simulationResult, recommendation]
  )

  return (
    <GovShell
      sections={sections}
      activeSection={activeSection}
      onSectionChange={(id) => setActiveSection(id as SectionId)}
      mastheadAside={<MastheadAside />}
      breadcrumbLeaf={SECTION_LEAF[activeSection]}
    >
      <main
        id="main-content"
        style={{ display: 'flex', flex: 1, overflow: 'hidden', minHeight: 0 }}
      >
        {/* ── Working panel ──────────────────────────────────────────── */}
        <aside
          aria-label="Working panel"
          style={{
            width: 'var(--sidebar-width)',
            minWidth: 'var(--sidebar-width)',
            background: 'var(--gov-grey-050)',
            borderRight: '1px solid var(--clr-border)',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}
        >
          <div
            role="tabpanel"
            id={`panel-${activeSection}`}
            aria-labelledby={`nav-${activeSection}`}
            tabIndex={0}
            style={{ flex: 1, overflowY: 'auto', padding: 'var(--space-3)' }}
          >
            {activeSection === 'scenario' ? (
              <ScenarioBuilder onOptimizeSuccess={() => setActiveSection('advisory')} />
            ) : activeSection === 'assessment' ? (
              <ResultPanel />
            ) : activeSection === 'advisory' ? (
              <TradeoffTable />
            ) : (
              <AboutPanel />
            )}
          </div>
        </aside>

        {/* ── Map ────────────────────────────────────────────────────── */}
        <section
          aria-label="Network map"
          style={{ flex: 1, position: 'relative', overflow: 'hidden' }}
        >
          <MapView />
          <CascadeLegend />

          {status === 'error' && <ErrorOverlay message={error} />}
          {(status === 'loading-graph' || status === 'loading-interventions') && (
            <LoadingOverlay status={status} />
          )}
        </section>
      </main>
    </GovShell>
  )
}
