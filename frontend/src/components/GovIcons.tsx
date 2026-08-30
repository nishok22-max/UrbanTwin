/**
 * GovIcons — line-art icon set for the decision support system.
 *
 * Replaces the emoji previously used as functional iconography. Emoji render
 * inconsistently across platforms, cannot inherit colour, and are announced
 * verbatim by screen readers ("sparkles", "rocket"), which is unacceptable in
 * an official interface.
 *
 * Conventions:
 *  - 24x24 viewBox, 1.75 stroke, currentColor — icons take the colour of text
 *  - aria-hidden by default: every icon is paired with a visible text label
 *  - `title` may be supplied for the rare standalone control, which promotes
 *    the icon to role="img"
 */
import React from 'react'

export interface IconProps {
  size?: number
  className?: string
  /** Accessible name. Omit for decorative icons paired with visible text. */
  title?: string
  style?: React.CSSProperties
}

const Svg: React.FC<IconProps & { children: React.ReactNode; fill?: boolean }> = ({
  size = 16,
  className,
  title,
  style,
  children,
  fill = false,
}) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill={fill ? 'currentColor' : 'none'}
    stroke={fill ? 'none' : 'currentColor'}
    strokeWidth={1.75}
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
    style={{ flexShrink: 0, ...style }}
    role={title ? 'img' : undefined}
    aria-hidden={title ? undefined : true}
    aria-label={title}
    focusable="false"
  >
    {title ? <title>{title}</title> : null}
    {children}
  </svg>
)

/* -------------------------------------------------------------------------
   Identity
   ------------------------------------------------------------------------- */

/**
 * Institutional device for the masthead. A deliberately generic civic mark —
 * a chevron shield over a waterline — chosen so the system is not mistaken
 * for an existing authority's emblem.
 */
export const SealMark: React.FC<{ size?: number }> = ({ size = 40 }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 48 48"
    aria-hidden="true"
    focusable="false"
    style={{ flexShrink: 0 }}
  >
    <circle cx="24" cy="24" r="22.5" fill="var(--gov-navy-900)" />
    <circle cx="24" cy="24" r="19" fill="none" stroke="var(--gov-white)" strokeWidth="1" opacity="0.5" />
    {/* Shield */}
    <path
      d="M24 10 L34 14.5 V25 C34 31.5 29.5 35.8 24 38 C18.5 35.8 14 31.5 14 25 V14.5 Z"
      fill="none"
      stroke="var(--gov-white)"
      strokeWidth="1.75"
      strokeLinejoin="round"
    />
    {/* Skyline within the shield */}
    <path
      d="M18 26.5 V20.5 h3 V26.5 M22.5 26.5 V17 h3.5 V26.5 M27.5 26.5 V22 h3 V26.5"
      fill="none"
      stroke="var(--gov-white)"
      strokeWidth="1.4"
      strokeLinejoin="round"
    />
    {/* Waterline */}
    <path
      d="M15.5 30 q2.2 -1.7 4.3 0 t4.3 0 t4.3 0 t4.3 0"
      fill="none"
      stroke="var(--gov-gold)"
      strokeWidth="1.75"
      strokeLinecap="round"
    />
  </svg>
)

/* -------------------------------------------------------------------------
   Domain
   ------------------------------------------------------------------------- */

/** Rainfall / design storm */
export const IconRainfall: React.FC<IconProps> = (p) => (
  <Svg {...p}>
    <path d="M7 16.5A4.5 4.5 0 0 1 7.2 7.6a5.5 5.5 0 0 1 10.5 1.3A3.8 3.8 0 0 1 17.5 16.5Z" />
    <path d="M8.5 19v2M12 19.5v2.5M15.5 19v2" />
  </Svg>
)

/** Flood / inundation depth */
export const IconWater: React.FC<IconProps> = (p) => (
  <Svg {...p}>
    <path d="M2 15.5q2.5-2 5-0.2t5 0t5-0.2t5 0.4" />
    <path d="M2 19.5q2.5-2 5-0.2t5 0t5-0.2t5 0.4" />
    <path d="M12 3s4.5 4.7 4.5 7.5a4.5 4.5 0 0 1-9 0C7.5 7.7 12 3 12 3Z" />
  </Svg>
)

/** Capital budget / cost */
export const IconBudget: React.FC<IconProps> = (p) => (
  <Svg {...p}>
    <rect x="2.5" y="5.5" width="19" height="13" rx="1.5" />
    <circle cx="12" cy="12" r="3" />
    <path d="M5.5 9v6M18.5 9v6" />
  </Svg>
)

/** Schedule of works / infrastructure interventions */
export const IconWorks: React.FC<IconProps> = (p) => (
  <Svg {...p}>
    <path d="M14.7 6.3a3.9 3.9 0 0 0 5.1 5.1L21 12.6l-8.4 8.4a2 2 0 0 1-2.8-2.8l8.4-8.4Z" />
    <path d="M9.5 9.5 4.8 4.8" />
    <path d="M3 8.5 8.5 3l2.5 2.5L5.5 11Z" />
  </Svg>
)

/** Population / residents protected */
export const IconPopulation: React.FC<IconProps> = (p) => (
  <Svg {...p}>
    <circle cx="9" cy="8" r="3.2" />
    <path d="M2.8 19.5a6.2 6.2 0 0 1 12.4 0" />
    <path d="M16.5 5.2a3.2 3.2 0 0 1 0 5.9" />
    <path d="M18 14.4a6.2 6.2 0 0 1 3.2 5.1" />
  </Svg>
)

/** Mobility / road network */
export const IconMobility: React.FC<IconProps> = (p) => (
  <Svg {...p}>
    <path d="M4 21 8.5 3M19.5 21 15 3" />
    <path d="M12 4.5v3M12 10.5v3M12 16.5v3" />
  </Svg>
)

/** Service availability / essential facilities */
export const IconService: React.FC<IconProps> = (p) => (
  <Svg {...p}>
    <path d="M3.5 20.5V9.8L12 3.5l8.5 6.3v10.7Z" />
    <path d="M12 10v6M9 13h6" />
  </Svg>
)

/** Locality / map position */
export const IconLocation: React.FC<IconProps> = (p) => (
  <Svg {...p}>
    <path d="M19 10.2c0 5.2-7 11.3-7 11.3s-7-6.1-7-11.3a7 7 0 0 1 14 0Z" />
    <circle cx="12" cy="10" r="2.6" />
  </Svg>
)

/** Network node / graph asset */
export const IconNode: React.FC<IconProps> = (p) => (
  <Svg {...p}>
    <circle cx="12" cy="12" r="2.6" />
    <circle cx="4.5" cy="5" r="2" />
    <circle cx="19.5" cy="5" r="2" />
    <circle cx="4.5" cy="19" r="2" />
    <circle cx="19.5" cy="19" r="2" />
    <path d="M6 6.4 10 10.2M18 6.4 14 10.2M6 17.6 10 13.8M18 17.6 14 13.8" />
  </Svg>
)

/* -------------------------------------------------------------------------
   Analysis
   ------------------------------------------------------------------------- */

/** Assessment / results */
export const IconChart: React.FC<IconProps> = (p) => (
  <Svg {...p}>
    <path d="M3.5 3.5v17h17" />
    <path d="M7 16.5v-4M11.3 16.5V8M15.6 16.5v-6M20 16.5V6" />
  </Svg>
)

/** Comparison table / options analysis */
export const IconTable: React.FC<IconProps> = (p) => (
  <Svg {...p}>
    <rect x="3" y="4" width="18" height="16" rx="1.5" />
    <path d="M3 9h18M3 14.5h18M9.5 9v11" />
  </Svg>
)

/** Optimisation / appraisal run */
export const IconAppraisal: React.FC<IconProps> = (p) => (
  <Svg {...p}>
    <circle cx="11" cy="11" r="7" />
    <path d="M16.2 16.2 21 21" />
    <path d="M8.2 11.4l2 2 4-4.4" />
  </Svg>
)

/** Adjustable parameters / weightings */
export const IconSettings: React.FC<IconProps> = (p) => (
  <Svg {...p}>
    <path d="M5 6h14M5 12h14M5 18h14" />
    <circle cx="9" cy="6" r="2" />
    <circle cx="15" cy="12" r="2" />
    <circle cx="8" cy="18" r="2" />
  </Svg>
)

/** Document / report */
export const IconDocument: React.FC<IconProps> = (p) => (
  <Svg {...p}>
    <path d="M14 3H6.5A1.5 1.5 0 0 0 5 4.5v15A1.5 1.5 0 0 0 6.5 21h11a1.5 1.5 0 0 0 1.5-1.5V8Z" />
    <path d="M14 3v5h5" />
    <path d="M8.5 12.5h7M8.5 16h5" />
  </Svg>
)

/* -------------------------------------------------------------------------
   Status
   ------------------------------------------------------------------------- */

export const IconCheck: React.FC<IconProps> = (p) => (
  <Svg {...p}>
    <path d="M4.5 12.5 9.5 17.5 19.5 6.5" />
  </Svg>
)

export const IconAlert: React.FC<IconProps> = (p) => (
  <Svg {...p}>
    <path d="M10.6 3.9 2.5 18a1.6 1.6 0 0 0 1.4 2.4h16.2A1.6 1.6 0 0 0 21.5 18L13.4 3.9a1.6 1.6 0 0 0-2.8 0Z" />
    <path d="M12 9.5v4.2M12 17.2h.01" />
  </Svg>
)

export const IconInfo: React.FC<IconProps> = (p) => (
  <Svg {...p}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 11v5.5M12 7.8h.01" />
  </Svg>
)

export const IconClose: React.FC<IconProps> = (p) => (
  <Svg {...p}>
    <path d="M6 6l12 12M18 6 6 18" />
  </Svg>
)

export const IconChevronRight: React.FC<IconProps> = (p) => (
  <Svg {...p}>
    <path d="M9 5.5 15.5 12 9 18.5" />
  </Svg>
)

export const IconChevronDown: React.FC<IconProps> = (p) => (
  <Svg {...p}>
    <path d="M5.5 9 12 15.5 18.5 9" />
  </Svg>
)

/* -------------------------------------------------------------------------
   Accessibility controls
   ------------------------------------------------------------------------- */

/** High-contrast toggle */
export const IconContrast: React.FC<IconProps> = (p) => (
  <Svg {...p}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 3v18a9 9 0 0 0 0-18Z" fill="currentColor" stroke="none" />
  </Svg>
)

/** Text size control */
export const IconTextSize: React.FC<IconProps> = (p) => (
  <Svg {...p}>
    <path d="M3 19 8.5 5.5 14 19" />
    <path d="M5.2 14.5h6.6" />
    <path d="M15.5 19 19 10l3.5 9" />
    <path d="M16.9 16h4.2" />
  </Svg>
)
