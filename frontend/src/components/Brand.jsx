/**
 * Your logo goes here.
 *
 * Drop your file at `src/assets/logo.svg` (or .png) and uncomment the import
 * below - nothing else in the app needs to change. Until then this renders a
 * neutral placeholder box so layouts keep their correct spacing.
 *
 *   import logoUrl from '../assets/logo.svg'
 *
 * Sizes used around the app: 'sm' in portal sidebars, 'lg' on login screens.
 */

// import logoUrl from '../assets/logo.svg'
const logoUrl = null

const SIZES = {
  sm: { box: 34, font: 15 },
  md: { box: 44, font: 18 },
  lg: { box: 60, font: 24 },
}

export function Logo({ size = 'sm', alt = 'University logo' }) {
  const { box, font } = SIZES[size] || SIZES.sm

  if (logoUrl) {
    return (
      <img
        src={logoUrl}
        alt={alt}
        className="logo-img"
        style={{ height: box, width: 'auto', maxWidth: box * 3 }}
      />
    )
  }

  return (
    <span
      className="logo-placeholder"
      style={{ width: box, height: box, fontSize: font * 0.42 }}
      role="img"
      aria-label={alt}
      title="Replace this in src/components/Brand.jsx"
    >
      LOGO
    </span>
  )
}

/** Logo plus the portal's name, used in sidebars and on login screens. */
export function Brand({ title, subtitle, size = 'sm', stacked = false }) {
  return (
    <div className={stacked ? 'brand brand-stacked' : 'brand'}>
      <Logo size={size} />
      <span className="brand-text">
        <strong>{title}</strong>
        {subtitle && <span>{subtitle}</span>}
      </span>
    </div>
  )
}
