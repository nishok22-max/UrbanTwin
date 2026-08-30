/**
 * MapView — MapLibre GL rendering of the T. Nagar network.
 *
 * Cartographic conventions rather than decorative ones: a light basemap so
 * that overlaid data carries the contrast, plan view (no camera pitch) so that
 * distances read true, and a sequential depth ramp from neutral grey through
 * amber to red.
 *
 * Layers
 *   1. Basemap (light)
 *   2. Road links, coloured by modelled inundation depth
 *   3. Junction nodes, coloured by the same ramp
 *   4. Rings marking the works in the active schedule
 */
import React, { useEffect, useRef, useState } from 'react'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useStore } from '../state/store'
import { IconLocation, IconClose, IconNode } from './GovIcons'

const TNAGAR_CENTER: [number, number] = [80.24, 13.034]
const TNAGAR_ZOOM = 14.5

/** Elevation below which a junction sits in a recognised low basin. */
const LOW_BASIN_ELEVATION_M = 8.5

/** Depth at which a junction is treated as flooded, in metres. */
const FLOOD_THRESHOLD_M = 0.04

const LOCALITIES = [
  { name: 'Panagal Park', coords: [80.233, 13.0405] as [number, number], zoom: 16 },
  { name: 'Pondy Bazaar', coords: [80.2385, 13.041] as [number, number], zoom: 16 },
  { name: 'Usman Road', coords: [80.2345, 13.0365] as [number, number], zoom: 16.2 },
  { name: 'G.N. Chetty Basin', coords: [80.244, 13.0425] as [number, number], zoom: 16 },
]

/* Sequential depth ramp, shared with the legend in CascadeLayer. */
const DEPTH_RAMP = {
  dry: '#9aa5b1',
  minor: '#f0b429',
  moderate: '#d97706',
  severe: '#a4262c',
} as const

interface NodeRecord {
  osmid: number
  elevation_m: number
  population_served: number
  node_type: string
  flood_depth_m: number
  coordinates: [number, number]
}

export const MapView: React.FC = () => {
  const mapContainerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)

  const graphData = useStore((s) => s.graphData)
  const simulationResult = useStore((s) => s.simulationResult)
  const interventions = useStore((s) => s.interventions)
  const selectedInterventionIds = useStore((s) => s.selectedInterventionIds)
  const focusCoordinates = useStore((s) => s.focusCoordinates)
  const setHoveredNodeId = useStore((s) => s.setHoveredNodeId)
  const setSelectedNodeId = useStore((s) => s.setSelectedNodeId)

  const [nodeRecord, setNodeRecord] = useState<NodeRecord | null>(null)
  /* Basemap tiles arrive over the network well after the app itself is
     interactive. Without this the map area is a blank white panel for several
     seconds, which reads as a broken page. */
  const [baseMapReady, setBaseMapReady] = useState(false)

  // Modelled depth per node, from the most recent simulation.
  const floodState = React.useMemo(() => {
    const depths: Record<number, number> = {}
    simulationResult?.cascade_path.forEach((hop) => {
      depths[hop.node_id] = hop.flood_depth_m
    })
    return depths
  }, [simulationResult])

  // -- Initialise --------------------------------------------------------
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return

    const cartoKey = import.meta.env.VITE_CARTO_API_KEY
    const mapStyle = cartoKey
      ? {
          version: 8 as const,
          sources: {
            'carto-light': {
              type: 'raster' as const,
              tiles: [
                `https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png?api_key=${cartoKey}`,
              ],
              tileSize: 256,
              attribution: '© CARTO © OpenStreetMap contributors',
            },
          },
          layers: [{ id: 'background', type: 'raster' as const, source: 'carto-light' }],
        }
      : 'https://tiles.openfreemap.org/styles/positron'

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: mapStyle,
      center: TNAGAR_CENTER,
      zoom: TNAGAR_ZOOM,
      maxZoom: 19,
      minZoom: 11,
      pitch: 0,
      antialias: true,
    })

    map.addControl(new maplibregl.NavigationControl({ showCompass: true }), 'top-right')
    map.addControl(new maplibregl.ScaleControl({ unit: 'metric' }), 'bottom-right')

    // 'idle' fires once the style has loaded and every visible tile has been
    // rendered — the first moment the map is actually worth looking at.
    map.once('idle', () => setBaseMapReady(true))

    // If tiles never arrive (offline, blocked host), do not strand the user
    // behind a spinner: reveal the map regardless. Our own network overlay
    // renders from local data and is useful even with no basemap underneath.
    const revealTimer = window.setTimeout(() => setBaseMapReady(true), 8000)
    map.on('error', () => setBaseMapReady(true))

    mapRef.current = map
    return () => {
      window.clearTimeout(revealTimer)
      map.remove()
      mapRef.current = null
    }
  }, [])

  // -- Camera ------------------------------------------------------------
  useEffect(() => {
    const map = mapRef.current
    if (!map || !focusCoordinates) return
    map.flyTo({ center: focusCoordinates, zoom: 16.5, essential: true, duration: 1200 })
  }, [focusCoordinates])

  // -- Network layers ----------------------------------------------------
  useEffect(() => {
    const map = mapRef.current
    if (!map || !graphData) return

    const buildLayers = () => {
      // Road links -------------------------------------------------------
      const edgeGeoJSON: GeoJSON.FeatureCollection = {
        type: 'FeatureCollection',
        features: graphData.edges.map((e) => ({
          type: 'Feature',
          properties: {
            ...e.properties,
            computed_depth: Math.max(
              floodState[e.properties.u] ?? 0,
              floodState[e.properties.v] ?? 0
            ),
          },
          geometry: e.geometry,
        })),
      }

      if (map.getSource('edges')) {
        ;(map.getSource('edges') as maplibregl.GeoJSONSource).setData(edgeGeoJSON)
      } else {
        map.addSource('edges', { type: 'geojson', data: edgeGeoJSON })

        map.addLayer({
          id: 'edges-base',
          type: 'line',
          source: 'edges',
          paint: {
            'line-color': [
              'interpolate',
              ['linear'],
              ['get', 'computed_depth'],
              0,
              DEPTH_RAMP.dry,
              0.04,
              DEPTH_RAMP.minor,
              0.2,
              DEPTH_RAMP.moderate,
              0.4,
              DEPTH_RAMP.severe,
            ],
            'line-width': ['interpolate', ['linear'], ['zoom'], 12, 0.8, 16, 2.6],
            'line-opacity': 0.9,
          },
        })

        // Flooded links are widened so they read at low zoom.
        map.addLayer({
          id: 'edges-flooded',
          type: 'line',
          source: 'edges',
          filter: ['>', ['get', 'computed_depth'], FLOOD_THRESHOLD_M],
          paint: {
            'line-color': [
              'interpolate',
              ['linear'],
              ['get', 'computed_depth'],
              0.04,
              DEPTH_RAMP.minor,
              0.2,
              DEPTH_RAMP.moderate,
              0.4,
              DEPTH_RAMP.severe,
            ],
            'line-width': ['interpolate', ['linear'], ['zoom'], 12, 2.2, 16, 5.5],
            'line-opacity': 0.55,
          },
        })
      }

      // Junction nodes ---------------------------------------------------
      const nodeGeoJSON: GeoJSON.FeatureCollection = {
        type: 'FeatureCollection',
        features: graphData.nodes.map((n) => ({
          type: 'Feature',
          id: n.properties.osmid,
          properties: {
            ...n.properties,
            computed_depth: floodState[n.properties.osmid] ?? 0,
          },
          geometry: n.geometry,
        })),
      }

      if (map.getSource('nodes')) {
        ;(map.getSource('nodes') as maplibregl.GeoJSONSource).setData(nodeGeoJSON)
      } else {
        map.addSource('nodes', { type: 'geojson', data: nodeGeoJSON })

        map.addLayer({
          id: 'nodes-circles',
          type: 'circle',
          source: 'nodes',
          paint: {
            'circle-radius': ['interpolate', ['linear'], ['zoom'], 12, 1.6, 16, 4],
            'circle-color': [
              'interpolate',
              ['linear'],
              ['get', 'computed_depth'],
              0,
              '#1a5fa8',
              0.04,
              DEPTH_RAMP.minor,
              0.2,
              DEPTH_RAMP.moderate,
              0.4,
              DEPTH_RAMP.severe,
            ],
            'circle-opacity': 0.95,
            'circle-stroke-width': 0.75,
            'circle-stroke-color': '#ffffff',
          },
        })

        map.on('mouseenter', 'nodes-circles', () => {
          map.getCanvas().style.cursor = 'pointer'
        })
        map.on('mouseleave', 'nodes-circles', () => {
          map.getCanvas().style.cursor = ''
          setHoveredNodeId(null)
        })
        map.on('mousemove', 'nodes-circles', (e) => {
          if (e.features?.[0]) setHoveredNodeId(Number(e.features[0].id))
        })

        map.on('click', 'nodes-circles', (e) => {
          const feature = e.features?.[0]
          if (!feature) return
          const props = feature.properties as Record<string, unknown>
          setSelectedNodeId(Number(feature.id))
          setNodeRecord({
            osmid: Number(props.osmid),
            elevation_m: Number(props.elevation_m),
            population_served: Number(props.population_served),
            node_type: String(props.node_type),
            flood_depth_m: Number(props.computed_depth ?? 0),
            coordinates: (feature.geometry as GeoJSON.Point).coordinates as [number, number],
          })
        })
      }
    }

    if (map.isStyleLoaded()) buildLayers()
    else map.on('load', buildLayers)
  }, [graphData, floodState, setHoveredNodeId, setSelectedNodeId])

  // -- Works markers -----------------------------------------------------
  useEffect(() => {
    const map = mapRef.current
    if (!map || !map.isStyleLoaded()) return

    const selectedWorks = interventions.filter((i) => selectedInterventionIds.has(i.id))
    const markerGeoJSON: GeoJSON.FeatureCollection = {
      type: 'FeatureCollection',
      features: selectedWorks.map((i) => ({
        type: 'Feature',
        properties: { name: i.name, type: i.intervention_type },
        geometry: { type: 'Point', coordinates: [i.node_lon, i.node_lat] },
      })),
    }

    if (map.getSource('intervention-rings')) {
      ;(map.getSource('intervention-rings') as maplibregl.GeoJSONSource).setData(markerGeoJSON)
    } else {
      map.addSource('intervention-rings', { type: 'geojson', data: markerGeoJSON })

      map.addLayer({
        id: 'intervention-rings-outer',
        type: 'circle',
        source: 'intervention-rings',
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['zoom'], 12, 11, 16, 22],
          'circle-color': 'rgba(11, 37, 69, 0.06)',
          'circle-stroke-width': 2,
          'circle-stroke-color': '#0b2545',
        },
      })

      map.addLayer({
        id: 'intervention-rings-inner',
        type: 'circle',
        source: 'intervention-rings',
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['zoom'], 12, 4, 16, 7],
          'circle-color': '#0b2545',
          'circle-stroke-width': 1.5,
          'circle-stroke-color': '#ffffff',
        },
      })
    }
  }, [interventions, selectedInterventionIds])

  const flyTo = (coords: [number, number], zoom: number) => {
    mapRef.current?.flyTo({ center: coords, zoom, duration: 1200, essential: true })
  }

  const isFlooded = nodeRecord ? nodeRecord.flood_depth_m > FLOOD_THRESHOLD_M : false

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      <div
        ref={mapContainerRef}
        style={{ width: '100%', height: '100%' }}
        aria-label="Map of the T. Nagar infrastructure network"
        role="application"
      />

      {/* ── Basemap loading ──────────────────────────────────────────── */}
      {!baseMapReady && (
        <div
          role="status"
          aria-live="polite"
          style={{
            position: 'absolute',
            inset: 0,
            zIndex: 12,
            background: 'var(--gov-grey-050)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 'var(--space-2)',
          }}
        >
          <span className="spinner" style={{ width: '22px', height: '22px' }} />
          <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--clr-text-secondary)' }}>
            Loading base map…
          </p>
        </div>
      )}

      {/* ── Locality navigation ──────────────────────────────────────── */}
      <div
        className="hud-box"
        style={{
          position: 'absolute',
          top: 'var(--space-3)',
          left: 'var(--space-3)',
          zIndex: 10,
          padding: 'var(--space-2)',
        }}
      >
        <div
          id="locality-nav-label"
          style={{
            fontSize: '10px',
            fontWeight: 700,
            letterSpacing: '0.05em',
            textTransform: 'uppercase',
            color: 'var(--gov-navy-900)',
            marginBottom: '5px',
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
          }}
        >
          <IconLocation size={12} />
          Locality navigation
        </div>
        <div role="group" aria-labelledby="locality-nav-label" style={{ display: 'flex', gap: '4px' }}>
          {LOCALITIES.map((locality) => (
            <button
              key={locality.name}
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => flyTo(locality.coords, locality.zoom)}
            >
              {locality.name}
            </button>
          ))}
        </div>
      </div>

      {/* ── Junction record ──────────────────────────────────────────── */}
      {nodeRecord && (
        <div
          className="hud-box fade-in"
          role="region"
          aria-label="Selected junction record"
          style={{
            position: 'absolute',
            bottom: 'var(--space-5)',
            left: 'var(--space-3)',
            zIndex: 15,
            width: '272px',
          }}
        >
          <div className="gov-panel__header">
            <h3 className="gov-panel__title">
              <IconNode size={13} />
              Junction record
            </h3>
            <button
              type="button"
              onClick={() => setNodeRecord(null)}
              className="btn btn-ghost btn-sm"
              aria-label="Close junction record"
              style={{ padding: '2px 4px' }}
            >
              <IconClose size={12} />
            </button>
          </div>

          <div style={{ padding: 'var(--space-2) var(--space-3)' }}>
            <dl className="gov-dl">
              <dt>Reference</dt>
              <dd>{nodeRecord.osmid}</dd>

              <dt>Elevation</dt>
              <dd
                style={{
                  color:
                    nodeRecord.elevation_m < LOW_BASIN_ELEVATION_M
                      ? 'var(--gov-red-700)'
                      : 'var(--gov-green-700)',
                }}
              >
                {nodeRecord.elevation_m.toFixed(1)} m
                {nodeRecord.elevation_m < LOW_BASIN_ELEVATION_M ? ' · low basin' : ''}
              </dd>

              <dt>Population served</dt>
              <dd>{Math.round(nodeRecord.population_served).toLocaleString('en-IN')}</dd>

              <dt>Modelled depth</dt>
              <dd style={{ color: isFlooded ? 'var(--gov-red-700)' : 'var(--gov-green-700)' }}>
                {nodeRecord.flood_depth_m > 0
                  ? `${(nodeRecord.flood_depth_m * 100).toFixed(0)} cm`
                  : 'Dry'}
              </dd>

              <dt>Coordinates</dt>
              <dd>
                {nodeRecord.coordinates[1].toFixed(4)}, {nodeRecord.coordinates[0].toFixed(4)}
              </dd>
            </dl>
          </div>
        </div>
      )}
    </div>
  )
}
