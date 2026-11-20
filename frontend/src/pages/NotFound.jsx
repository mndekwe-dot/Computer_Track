import { Link, useLocation } from 'react-router-dom'
import { ArrowLeft, Compass, LifeBuoy } from 'lucide-react'
import { useAuth } from '../auth/AuthContext'
import { Brand } from '../components/Brand'
import { useSiteSettings } from '../hooks/useSiteSettings'
import { PageMeta } from '../components/PageMeta'
import { PORTALS, homePortalFor } from '../portals'

/**
 * A wrong address used to redirect silently to the landing page.
 *
 * That reads as the application losing your place. A guard who mistypes a
 * bookmark, or follows a link to a page that has been renamed, ends up
 * somewhere else with no explanation and no idea whether they are signed in.
 * Worse, it hides the mistake: nobody ever reports a broken link that quietly
 * takes them somewhere plausible.
 *
 * So the page says what happened, shows the address that failed, and offers
 * the two ways out that are actually useful: back to where they came from,
 * and forward to the part of the system they belong in.
 */
export default function NotFound() {
  const { user, isAuthenticated, loading } = useAuth()
  const { settings } = useSiteSettings()
  const location = useLocation()

  if (loading) {
    return <div className="page-loading">Checking your session…</div>
  }

  const portal = isAuthenticated ? homePortalFor(user) : null
  const systemName = settings['branding.system_name'] || 'etracker'

  return (
    <div className="notfound-page">
      <PageMeta
        title="Page not found"
        description="That address does not exist on the campus computer register."
        noindex
      />

      <main className="notfound-card" id="main">
        <Brand title={systemName} subtitle="Campus computer register" size="md" as="p" />

        <p className="notfound-code" aria-hidden="true">
          404
        </p>
        <h1>That page does not exist</h1>
        <p className="notfound-body">
          Nothing is served at this address. It may have been renamed, or the link that brought
          you here may be out of date.
        </p>

        {/* The address is shown because it is the one piece of information
            that makes the problem reportable. Broken out of the sentence and
            wrapped, since a long portal URL has no spaces to break at. */}
        <p className="notfound-path">
          <span className="visually-hidden">Address requested: </span>
          <code>{location.pathname}</code>
        </p>

        <div className="notfound-actions">
          {portal ? (
            <Link className="btn btn-primary" to={portal.home}>
              <Compass size={16} aria-hidden="true" />
              Go to {portal.name}
            </Link>
          ) : (
            <Link className="btn btn-primary" to="/">
              <Compass size={16} aria-hidden="true" />
              Go to the home page
            </Link>
          )}
          <button type="button" className="btn btn-ghost" onClick={() => window.history.back()}>
            <ArrowLeft size={16} aria-hidden="true" />
            Back
          </button>
        </div>

        {!isAuthenticated && (
          <nav className="notfound-links" aria-label="Other places to go">
            <h2>Looking for something else?</h2>
            <ul>
              <li>
                <Link to="/register">Register a computer, or check one you have registered</Link>
              </li>
              <li>
                <Link to="/login">Sign in as a member of staff</Link>
              </li>
            </ul>
          </nav>
        )}

        {settings['branding.support_email'] && (
          <p className="notfound-support">
            <LifeBuoy size={15} aria-hidden="true" />
            Still stuck? Email{' '}
            <a href={`mailto:${settings['branding.support_email']}`}>
              {settings['branding.support_email']}
            </a>
            .
          </p>
        )}
      </main>
    </div>
  )
}
