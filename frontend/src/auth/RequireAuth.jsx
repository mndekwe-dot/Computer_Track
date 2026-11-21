import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from './AuthContext'
import { canEnter, homePortalFor } from '../portals'

/**
 * Gate for a whole portal.
 *
 * An unauthenticated visitor goes to the single staff sign-in page. Somebody
 * signed in who has typed an address belonging to another portal is sent to
 * their own, silently: there is no decision for them to make, and a screen
 * announcing which portal they are not allowed into would describe the
 * organisation to anyone who guessed a URL.
 */
export function RequirePortal({ portal, children }) {
  const { user, isAuthenticated, loading } = useAuth()
  const location = useLocation()

  if (loading) return <div className="page-loading">Checking your session…</div>

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  if (!canEnter(user, portal)) return <Navigate to={homePortalFor(user).home} replace />

  return children
}
