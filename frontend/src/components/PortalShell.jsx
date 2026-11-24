import { useEffect, useRef, useState } from 'react'
import { CornerUpLeft, Menu, LogOut, UserCog, X } from 'lucide-react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { PortalProvider } from '../auth/PortalContext'
import { homePortalFor } from '../portals'
import { Brand } from './Brand'
import { ErrorBoundary } from './ErrorBoundary'

export function PortalShell({ portal }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [navOpen, setNavOpen] = useState(false)
  const toggleRef = useRef(null)

  // An administrator may open any portal, so they can stand at a gate and
  // reproduce what a guard sees. Until now there was no marked way back:
  // the sidebar showed the Security Gate's two links and the name of a
  // portal that was not theirs, and the only exit was typing a URL.
  const ownPortal = homePortalFor(user)
  const visiting = ownPortal.key !== portal.key

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
    navigate('/login', { replace: true })
  }

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

          {/* Links are grouped by the job they belong to. A group heading is
              printed once, above its first link; ungrouped links sit at the
              top. Each group is a list of its own so a screen reader announces
              how many links it holds. */}
          <nav className="nav" aria-label={`${portal.name} sections`}>
            {groupNav(portal.nav).map(({ group, links }) => (
              <div className="nav-section" key={group || 'top'}>
                {group && (
                  <div className="nav-group" id={`nav-${portal.key}-${group}`}>
                    {group}
                  </div>
                )}
                <ul aria-labelledby={group ? `nav-${portal.key}-${group}` : undefined}>
                  {links.map((link) => {
                    const Icon = link.icon
                    // Pages reached from inside another (Import from the
                    // Students page) keep their parent highlighted.
                    const alsoActive = link.also?.some((path) =>
                      location.pathname.startsWith(path),
                    )
                    return (
                      <li key={link.to}>
                        <NavLink
                          to={link.to}
                          end={link.end}
                          className={({ isActive }) => (isActive || alsoActive ? 'active' : undefined)}
                          aria-current={alsoActive ? 'page' : undefined}
                        >
                          <Icon size={17} className="nav-icon" aria-hidden="true" />
                          <span>{link.label}</span>
                        </NavLink>
                      </li>
                    )
                  })}
                </ul>
              </div>
            ))}
          </nav>

          <div className="sidebar-footer">
            {visiting && (
              <NavLink to={ownPortal.home} className="portal-return">
                <CornerUpLeft size={15} aria-hidden="true" />
                <span>
                  Back to {ownPortal.name}
                  <span>You are visiting {portal.name}</span>
                </span>
              </NavLink>
            )}

            {/* Your own account lives with your name rather than in the list
                of work: it is about you, not about the register. */}
            <NavLink to={`${portal.base}/account`} className="sidebar-user">
              <UserCog size={17} className="nav-icon" aria-hidden="true" />
              <span>
                <strong>{user?.full_name}</strong>
                <span>
                  {user?.role_display}
                  {user?.default_gate_name ? `, ${user.default_gate_name}` : ''}
                </span>
                <span className="sidebar-user-link">My account</span>
              </span>
            </NavLink>
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

function groupNav(links) {
  const sections = []
  for (const link of links) {
    const group = link.group || null
    const last = sections[sections.length - 1]
    if (last && last.group === group) last.links.push(link)
    else sections.push({ group, links: [link] })
  }
  return sections
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
