/**
 * GovShell — the portal chrome around the working area.
 *
 * Structure follows Indian government web conventions (GIGW):
 *   utility strip → masthead → primary navigation → breadcrumb
 *   → [ working area ] → footer
 *
 * The shell also owns the two site-wide accessibility controls required of a
 * public-facing government service: text resizing and high contrast. Both are
 * persisted, and both are re-applied before first paint by the inline script
 * in index.html so the page never flashes at the default setting.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react'
import {
  SealMark,
  IconChevronRight,
  IconContrast,
  IconTextSize,
  IconInfo,
} from './GovIcons'

/* -------------------------------------------------------------------------
   Accessibility preferences
   ------------------------------------------------------------------------- */

const STORAGE_SCALE = 'ufrdss.textScale'
const STORAGE_CONTRAST = 'ufrdss.contrast'

const SCALE_STEPS = [0.9, 1, 1.15] as const
type ScaleStep = (typeof SCALE_STEPS)[number]

/** Storage can throw outright in private modes — never let it break the page. */
function readStored(key: string): string | null {
  try {
    return window.localStorage.getItem(key)
  } catch {
    return null
  }
}

function writeStored(key: string, value: string): void {
  try {
    window.localStorage.setItem(key, value)
  } catch {
    /* preference simply will not persist */
  }
}

function initialScale(): ScaleStep {
  const stored = Number(readStored(STORAGE_SCALE))
  return (SCALE_STEPS as readonly number[]).includes(stored) ? (stored as ScaleStep) : 1
}

function initialContrast(): boolean {
  return readStored(STORAGE_CONTRAST) === 'high'
}

/* -------------------------------------------------------------------------
   Types
   ------------------------------------------------------------------------- */

export interface ShellSection {
  id: string
  label: string
  /** Short description announced to assistive technology. */
  description: string
  icon: React.ReactNode
  /** Renders a marker when the section holds new output. */
  flagged?: boolean
  disabled?: boolean
}

interface GovShellProps {
  sections: ShellSection[]
  activeSection: string
  onSectionChange: (id: string) => void
  /** Rendered at the right of the masthead — system status, dataset counts. */
  mastheadAside?: React.ReactNode
  /** Trailing breadcrumb segment describing the current view. */
  breadcrumbLeaf: string
  children: React.ReactNode
}

/* -------------------------------------------------------------------------
   Accessibility toolbar
   ------------------------------------------------------------------------- */

const AccessibilityControls: React.FC = () => {
  const [scale, setScale] = useState<ScaleStep>(initialScale)
  const [highContrast, setHighContrast] = useState<boolean>(initialContrast)

  useEffect(() => {
    document.documentElement.style.setProperty('--ui-scale', String(scale))
    writeStored(STORAGE_SCALE, String(scale))
  }, [scale])

  useEffect(() => {
    if (highContrast) {
      document.documentElement.setAttribute('data-contrast', 'high')
    } else {
      document.documentElement.removeAttribute('data-contrast')
    }
    writeStored(STORAGE_CONTRAST, highContrast ? 'high' : 'normal')
  }, [highContrast])

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
      {/* Text size */}
      <div
        role="group"
        aria-label="Text size"
        style={{ display: 'flex', alignItems: 'center', gap: '4px' }}
      >
        <IconTextSize size={14} />
        <span className="sr-only">Text size</span>
        {([
          { step: SCALE_STEPS[0], label: 'A-', name: 'Decrease text size' },
          { step: SCALE_STEPS[1], label: 'A', name: 'Default text size' },
          { step: SCALE_STEPS[2], label: 'A+', name: 'Increase text size' },
        ] as const).map((opt) => (
          <button
            key={opt.label}
            type="button"
            className="gov-utility__btn"
            aria-pressed={scale === opt.step}
            onClick={() => setScale(opt.step)}
            title={opt.name}
            style={{ minWidth: '26px' }}
          >
            <span aria-hidden="true">{opt.label}</span>
            <span className="sr-only">{opt.name}</span>
          </button>
        ))}
      </div>

      {/* High contrast */}
      <button
        type="button"
        className="gov-utility__btn"
        aria-pressed={highContrast}
        onClick={() => setHighContrast((v) => !v)}
        style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}
      >
        <IconContrast size={13} />
        High contrast
      </button>
    </div>
  )
}

/* -------------------------------------------------------------------------
   Primary navigation
   ------------------------------------------------------------------------- */

const PrimaryNav: React.FC<{
  sections: ShellSection[]
  activeSection: string
  onSectionChange: (id: string) => void
}> = ({ sections, activeSection, onSectionChange }) => {
  const refs = useRef<Record<string, HTMLButtonElement | null>>({})

  /* Arrow keys move between sections; only the active tab stays in the tab
     order, which is the expected behaviour for a tablist. */
  const onKeyDown = useCallback(
    (event: React.KeyboardEvent, index: number) => {
      const selectable = sections.filter((s) => !s.disabled)
      if (selectable.length === 0) return

      const positionInSelectable = selectable.findIndex((s) => s.id === sections[index].id)
      let nextIndex = -1

      if (event.key === 'ArrowRight') nextIndex = (positionInSelectable + 1) % selectable.length
      else if (event.key === 'ArrowLeft')
        nextIndex = (positionInSelectable - 1 + selectable.length) % selectable.length
      else if (event.key === 'Home') nextIndex = 0
      else if (event.key === 'End') nextIndex = selectable.length - 1
      else return

      event.preventDefault()
      const target = selectable[nextIndex]
      onSectionChange(target.id)
      refs.current[target.id]?.focus()
    },
    [sections, onSectionChange]
  )

  return (
    <nav className="gov-nav" aria-label="Sections">
      <div role="tablist" aria-label="Sections" style={{ display: 'flex', alignItems: 'stretch' }}>
        {sections.map((section, index) => {
          const isActive = section.id === activeSection
          return (
            <button
              key={section.id}
              ref={(el) => {
                refs.current[section.id] = el
              }}
              id={`nav-${section.id}`}
              role="tab"
              type="button"
              className="gov-nav__item"
              aria-selected={isActive}
              aria-controls={`panel-${section.id}`}
              aria-describedby={`nav-desc-${section.id}`}
              tabIndex={isActive ? 0 : -1}
              disabled={section.disabled}
              onClick={() => onSectionChange(section.id)}
              onKeyDown={(e) => onKeyDown(e, index)}
            >
              {section.icon}
              <span>{section.label}</span>
              {section.flagged && (
                <span className="gov-nav__count" aria-hidden="true">
                  •
                </span>
              )}
              <span id={`nav-desc-${section.id}`} className="sr-only">
                {section.description}
                {section.flagged ? '. New results available' : ''}
              </span>
            </button>
          )
        })}
      </div>
    </nav>
  )
}

/* -------------------------------------------------------------------------
   Shell
   ------------------------------------------------------------------------- */

export const GovShell: React.FC<GovShellProps> = ({
  sections,
  activeSection,
  onSectionChange,
  mastheadAside,
  breadcrumbLeaf,
  children,
}) => {
  const today = new Date().toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>

      {/* ── Utility strip ─────────────────────────────────────────────── */}
      <div className="gov-utility">
        <span className="gov-utility__notice">
          <IconInfo size={13} />
          Demonstration prototype — not an official government service
        </span>
        <span style={{ flex: 1 }} />
        <span className="tabular" style={{ opacity: 0.85 }}>
          {today}
        </span>
        <AccessibilityControls />
      </div>

      {/* ── Masthead ──────────────────────────────────────────────────── */}
      <header className="gov-masthead">
        <SealMark size={40} />
        <div style={{ minWidth: 0 }}>
          <h1 className="gov-masthead__title">
            Urban Flood Resilience Decision Support System
          </h1>
          <p className="gov-masthead__sub">
            Consequence simulation and budget-constrained investment appraisal
            &nbsp;·&nbsp; T. Nagar, Chennai
          </p>
        </div>
        <div style={{ flex: 1 }} />
        {mastheadAside}
      </header>

      {/* ── Primary navigation ────────────────────────────────────────── */}
      <PrimaryNav
        sections={sections}
        activeSection={activeSection}
        onSectionChange={onSectionChange}
      />

      {/* ── Breadcrumb ────────────────────────────────────────────────── */}
      <div className="gov-breadcrumb">
        <nav aria-label="Breadcrumb">
          <ol>
            <li>Home</li>
            <li aria-hidden="true">
              <IconChevronRight size={11} />
            </li>
            <li>Flood Resilience Planning</li>
            <li aria-hidden="true">
              <IconChevronRight size={11} />
            </li>
            <li>T. Nagar</li>
            <li aria-hidden="true">
              <IconChevronRight size={11} />
            </li>
            <li aria-current="page">{breadcrumbLeaf}</li>
          </ol>
        </nav>
      </div>

      {/* ── Working area ──────────────────────────────────────────────── */}
      {children}

      {/* ── Footer ────────────────────────────────────────────────────── */}
      <footer className="gov-footer">
        <span>
          Model outputs are indicative and intended to support — not replace —
          engineering appraisal.
        </span>
        <span style={{ flex: 1 }} />
        <span>Base data: OpenStreetMap</span>
        <span aria-hidden="true">·</span>
        <span>Method: Monte-Carlo cascade with 0-1 knapsack allocation</span>
        <span aria-hidden="true">·</span>
        <span className="tabular">Last updated {today}</span>
      </footer>
    </div>
  )
}
