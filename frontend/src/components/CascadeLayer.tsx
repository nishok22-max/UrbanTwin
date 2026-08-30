/**
 * CascadeLayer — map legend for modelled inundation.
 *
 * The cascade itself is drawn by MapLibre layers in MapView; this module owns
 * the legend that explains that ramp. Depth bands are stated numerically
 * rather than as adjectives, so the map can be read without reference to the
 * colours alone.
 */
import React from 'react'
import type { CascadeHop } from '../api/client'
import { useStore } from '../state/store'

interface Props {
  cascadePath: CascadeHop[]
}

const DEPTH_BANDS = [
  { label: '40 cm and above', colour: '#a4262c' },
  { label: '20 – 40 cm', colour: '#d97706' },
  { label: '4 – 20 cm', colour: '#f0b429' },
  { label: 'Below 4 cm', colour: '#9aa5b1' },
  { label: 'Dry junction', colour: '#1a5fa8' },
]

export const CascadeLegend: React.FC = () => {
  const result = useStore((s) => s.simulationResult)
  if (!result || result.cascade_path.length === 0) return null

  const cascadeTotal = (result.meta['n_cascade_nodes'] as number) ?? result.cascade_path.length

  return (
    <div
      className="hud-box"
      role="region"
      aria-label="Map legend"
      style={{
        position: 'absolute',
        bottom: 'var(--space-8)',
        right: 'var(--space-3)',
        zIndex: 10,
        minWidth: '178px',
      }}
    >
      <div className="gov-panel__header">
        <h3 className="gov-panel__title">Modelled depth</h3>
      </div>

      <div style={{ padding: 'var(--space-2) var(--space-3)' }}>
        <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {DEPTH_BANDS.map((band) => (
            <li
              key={band.label}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '7px',
                fontSize: 'var(--font-size-xs)',
              }}
            >
              <span
                aria-hidden="true"
                style={{
                  width: '12px',
                  height: '12px',
                  background: band.colour,
                  border: '1px solid rgba(0,0,0,0.2)',
                  flexShrink: 0,
                }}
              />
              <span style={{ color: 'var(--clr-text-primary)' }}>{band.label}</span>
            </li>
          ))}
        </ul>

        <p
          className="tabular gov-hint"
          style={{
            marginTop: 'var(--space-2)',
            paddingTop: 'var(--space-2)',
            borderTop: '1px solid var(--clr-border)',
          }}
        >
          {result.cascade_path.length} junctions affected
          <br />
          {cascadeTotal} in the full cascade
        </p>
      </div>
    </div>
  )
}

/**
 * Retained for API compatibility. Cascade geometry is rendered by the MapLibre
 * layers in MapView, so this component contributes no DOM of its own.
 */
export const CascadeLayer: React.FC<Props> = () => null
