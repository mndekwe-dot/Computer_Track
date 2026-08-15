import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { DoorOpen } from 'lucide-react'
import { useAuth } from './AuthContext'
import { canEnter, homePortalFor } from '../portals'

/**
 * Gate for a whole portal. An unauthenticated visitor is sent to *this*
 * portal's login page, not a shared one - the three front doors stay separate.
 */
export function RequirePortal({ portal, children }) {
  const { user, isAuthenticated, loading } = useAuth()
  const location = useLocation()

  if (loading) return <div className="page-loading">Checking your session…</div>

  if (!isAuthenticated) {
    return <Navigate to={`${portal.base}/login`} state={{ from: location }} replace />
  }

  if (!canEnter(user, portal)) return <WrongPortal user={user} portal={portal} />

  return children
}

function WrongPortal({ user, portal }) {
  const navigate = useNavigate()
  const theirs = homePortalFor(user)

  return (
    <div className="empty-state" style={{ padding: '70px 24px' }}>
      <DoorOpen size={34} aria-hidden="true" style={{ color: 'var(--text-muted)' }} />
      <h2 style={{ marginTop: 12 }}>Wrong portal</h2>
      <p style={{ maxWidth: 440, margin: '10px auto 20px' }}>
        You are signed in as a {user.role_display}, which does not have access to the{' '}
        {portal.name} portal. Your work is in {theirs.name}.
      </p>
      <button type="button" className="btn btn-primary" onClick={() => navigate(theirs.home)}>
        Go to {theirs.name}
      </button>
    </div>
  )
}
