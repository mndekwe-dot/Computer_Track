/**
 * The etracker brand mark.
 *
 * Two files, both derived from the supplied artwork in
 * `etracker-high-resolution-logo.svg`:
 *
 *   assets/logo-mark.svg   the monitor on its own, near enough square
 *   assets/logo.svg        the full lockup, monitor plus "etracker."
 *
 * The original is a 2000x2000 canvas that is mostly lilac padding, so it
 * cannot be dropped into a 34px sidebar slot: both of these are trimmed to
 * the artwork and have no background, which lets them sit on the sidebar, on
 * white and on the login panel without a coloured square around them.
 *
 * `Brand` pairs the mark with a name, so the mark there is decorative: a
 * screen reader that announced "etracker" and then read the name beside it
 * would say the same thing twice.
 */
import markUrl from '../assets/logo-mark.svg'
import wordmarkUrl from '../assets/logo.svg'

const SIZES = {
  sm: { box: 34, font: 15 },
  md: { box: 44, font: 18 },
  lg: { box: 60, font: 24 },
}

export function Logo({ size = 'sm', alt = '' }) {
  const { box } = SIZES[size] || SIZES.sm

  return (
    <img
      src={markUrl}
      alt={alt}
      aria-hidden={alt ? undefined : 'true'}
      className="logo-img"
      style={{ height: box, width: 'auto' }}
    />
  )
}

/** The full lockup, for the few places with room for it and no name beside it. */
export function Wordmark({ height = 38, alt = 'etracker' }) {
  return <img src={wordmarkUrl} alt={alt} className="wordmark-img" style={{ height }} />
}

/**
 * Logo plus a name, used in sidebars and on login and public pages.
 *
 * `as` exists because this block plays two roles. In a sidebar it is chrome
 * repeated on every screen, so a heading element would be wrong. On the login
 * and public pages it *is* the page title, and rendering it as a <strong>
 * left those pages with no heading at all: nothing to navigate to, and an
 * <h2> further down with no parent.
 */
export function Brand({ title, subtitle, size = 'sm', stacked = false, as: Title = 'strong' }) {
  return (
    <div className={stacked ? 'brand brand-stacked' : 'brand'}>
      <Logo size={size} />
      <span className="brand-text">
        <Title>{title}</Title>
        {subtitle && <span>{subtitle}</span>}
      </span>
    </div>
  )
}
