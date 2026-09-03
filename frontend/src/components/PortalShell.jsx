import { useEffect, useRef, useState } from 'react'
import { Menu, LogOut, X } from 'lucide-react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { PortalProvider } from '../auth/PortalContext'
import { PORTAL_LIST, canEnter } from '../portals'
import { Brand } from './Brand'
import { ErrorBoundary } from './ErrorBoundary'

export function PortalShell({ portal }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [navOpen, setNavOpen] = useState(false)
  const toggleRef = useRef(null)

  // On a phone the nav is a drawer; it must close on navigation, otherwise it
  // covers the page the guard just asked for.
  useEffect(() => setNavOpen(false), [location.pathname])

  useEffect(() => {
    const onKey = (event) => {
      if (event.key !== 'Escape' || !navOpen) return
      setNavOpen(false)
      // Escape that leaves focus on a now-hidden drawer strands the keyboard
      // user at the top of the document. Hand it back to the control they
      // opened it with.
      toggleRef.current?.focus()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [navOpen])

  const signOut = () => {
    logout()
    navigate(`${portal.base}/login`, { replace: true })
  }

  // Admins can drop into another portal to see exactly what its users see.
  const otherPortals = PORTAL_LIST.filter(
    (candidate) => candidate.key !== portal.key && canEnter(user, candidate),
  )

  return (
    <PortalProvider portal={portal}>
      <div
        className="app"
        data-portal={portal.key}
        style={{ '--brand': portal.accent, '--brand-dark': portal.accentDark }}
      >
        <a className="skip-link" href="#main-content">
          Skip to content
        </a>

        <button
          ref={toggleRef}
          type="button"
          className="nav-toggle"
          onClick={() => setNavOpen((open) => !open)}
          aria-expanded={navOpen}
          aria-controls="portal-nav"
        >
          {navOpen ? <X size={20} /> : <Menu size={20} />}
          <span>{portal.name}</span>
        </button>

        {navOpen && (
          <div className="nav-scrim" onClick={() => setNavOpen(false)} aria-hidden="true" />
        )}

        <aside className="sidebar" id="portal-nav" data-open={navOpen}>
          <Brand title={portal.name} subtitle={portal.tagline} />

          <nav className="nav" aria-label={`${portal.name} sections`}>
            {portal.nav.map((link) => {
              const Icon = link.icon
              return (
                <NavLink key={link.to} to={link.to} end={link.end}>
                  <Icon size={17} className="nav-icon" aria-hidden="true" />
                  <span>{link.label}</span>
                </NavLink>
              )
            })}
          </nav>

          <div className="sidebar-footer">
            {otherPortals.length > 0 && (
              <div className="portal-switch">
                <div className="nav-group">Switch portal</div>
                {otherPortals.map((other) => (
                  <button
                    key={other.key}
                    type="button"
                    className="portal-switch-btn"
                    onClick={() => navigate(other.home)}
                  >
                    <span className="portal-dot" style={{ background: other.accent }} />
                    {other.name}
                  </button>
                ))}
              </div>
            )}

            <div className="sidebar-user">
              <strong>{user?.full_name}</strong>
              <span>
                {user?.role_display}
                {user?.default_gate_name ? ` · ${user.default_gate_name}` : ''}
              </span>
            </div>
            <button type="button" className="btn btn-ghost btn-sm btn-block" onClick={signOut}>
              <LogOut size={15} aria-hidden="true" />
              Sign out
            </button>
          </div>
        </aside>

        <main className="main" id="main-content" tabIndex={-1}>
          <ErrorBoundary key={location.pathname}>
            <Outlet />
          </ErrorBoundary>
        </main>
      </div>
    </PortalProvider>
  )
}

export function PageHeader({ title, subtitle, children }) {
  return (
    <header className="topbar">
      <div className="topbar-title">
        <h1>{title}</h1>
        {subtitle && <div className="topbar-sub">{subtitle}</div>}
      </div>
      {children && <div className="topbar-actions">{children}</div>}
    </header>
  )
}
