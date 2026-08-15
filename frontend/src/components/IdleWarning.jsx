import { Clock } from 'lucide-react'
import { useAuth } from '../auth/AuthContext'

/**
 * Shown a minute before an idle session ends.
 *
 * A guard mid-queue should never simply find themselves logged out. Any real
 * interaction dismisses this on its own, so in normal use it is never seen.
 */
export function IdleWarning() {
  const { idleWarning, staySignedIn, logout } = useAuth()
  if (idleWarning === null || idleWarning === undefined) return null

  return (
    <div className="idle-warning" role="alertdialog" aria-live="assertive">
      <Clock size={18} aria-hidden="true" />
      <span>
        Signing you out in <strong>{Math.max(0, idleWarning)}s</strong> because this terminal has
        been idle.
      </span>
      <div className="row-actions">
        <button type="button" className="btn btn-primary btn-sm" onClick={staySignedIn}>
          Stay signed in
        </button>
        <button type="button" className="btn btn-ghost btn-sm" onClick={logout}>
          Sign out now
        </button>
      </div>
    </div>
  )
}
