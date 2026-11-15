import { useState } from 'react'
import { LogIn } from 'lucide-react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { reasonText, takeSignedOutReason } from '../auth/session'
import { Wordmark } from '../components/Brand'
import { ErrorNote, Field } from '../components/ui'
import { useSiteSettings } from '../hooks/useSiteSettings'
import { PORTAL_LIST, canEnter, homePortalFor } from '../portals'

// Listed without saying which portal each one opens. Finding that out is the
// point of signing in.
const DEMO_ACCOUNTS = ['admin', 'registrar', 'guard1', 'guard2']

/**
 * One front door for every member of staff.
 *
 * There used to be three login screens, one per portal, each announcing whose
 * door it was. That told an unauthenticated visitor how the organisation is
 * shaped, which roles exist and which address to try, before proving anything
 * at all. It also asked staff to know which door was theirs, which is the
 * system's job, not theirs.
 *
 * So: one page, no portal named, and the credentials decide where the person
 * lands. Someone who does not know their role still gets to the right place,
 * and someone who should not be here learns nothing from the page.
 */
export default function StaffLogin() {
  const { login, user, isAuthenticated, loading } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const { settings } = useSiteSettings()
  // Where they were heading before being asked to sign in.
  const intended = location.state?.from?.pathname
  // Read once on mount, so it does not reappear after a later failed attempt.
  const [signedOutReason] = useState(() => takeSignedOutReason())
  const [form, setForm] = useState({ username: '', password: '', otp_token: '' })
  const [error, setError] = useState(null)
  const [needsCode, setNeedsCode] = useState(false)
  const [busy, setBusy] = useState(false)

  const systemName = settings['branding.system_name']
  const university = settings['branding.university_name']

  if (loading) return <div className="page-loading">Checking your session…</div>

  // Already signed in: no reason to show a form.
  if (isAuthenticated) return <Navigate to={destinationFor(user, intended)} replace />

  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const profile = await login(form.username.trim(), form.password, form.otp_token.trim())
      navigate(destinationFor(profile, intended), { replace: true })
    } catch (err) {
      // The password was right but a second factor is needed: reveal the code
      // field rather than showing a bare failure.
      if (err.fieldErrors?.otp_required) {
        setNeedsCode(true)
        setError({ readable: err.fieldErrors.detail || 'Enter your authenticator code.' })
      } else {
        setError(
          err.status === 401 ? { readable: 'Wrong username or password. Try again.' } : err,
        )
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login-page">
      <aside className="login-side">
        {/* The one screen with room for the full lockup, and the one screen
            where it is the page title rather than chrome. */}
        <h1 className="login-wordmark">
          <Wordmark height={64} />
        </h1>
        <p className="login-system">
          {systemName}, {university}
        </p>
        <p>Staff sign in. Your account decides which workspace opens.</p>
        <span className="login-stripe" aria-hidden="true" />
      </aside>

      <div className="login-main">
        <form className="login-card" onSubmit={submit}>
          <h2 className="login-title">Sign in</h2>

          {signedOutReason && reasonText(signedOutReason) && !error && (
            <div className="note note-info" role="status">
              <span>{reasonText(signedOutReason)}</span>
            </div>
          )}

          {intended && !error && (
            <div className="note note-info" role="status">
              <span>Sign in to continue to the page you asked for.</span>
            </div>
          )}

          <ErrorNote error={error} />

          <Field label="Username" required>
            <input
              value={form.username}
              onChange={(e) => setForm({ ...form, username: e.target.value })}
              autoComplete="username"
              autoFocus
              required
            />
          </Field>

          <Field label="Password" required>
            <input
              type="password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              autoComplete="current-password"
              required
            />
          </Field>

          {needsCode && (
            <Field
              label="Authenticator code"
              required
              hint="The 6-digit code from your authenticator app."
            >
              <input
                value={form.otp_token}
                onChange={(e) => setForm({ ...form, otp_token: e.target.value })}
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={8}
                placeholder="000000"
                autoFocus
                required
              />
            </Field>
          )}

          <button type="submit" className="btn btn-primary btn-lg btn-block" disabled={busy}>
            <LogIn size={17} aria-hidden="true" />
            {busy ? 'Signing in…' : 'Sign in'}
          </button>

          <div className="demo-hint">
            <strong>Demo accounts</strong> (password <code>passw0rd!</code>)
            <br />
            {DEMO_ACCOUNTS.join(', ')}
          </div>
        </form>

        <p className="login-aside">
          Registering your own computer as a student?{' '}
          <Link to="/register">Use the student form</Link>. No account needed.
        </p>
      </div>
    </div>
  )
}

/**
 * Where this person goes next.
 *
 * Back to the page they asked for, but only if their account may open it:
 * honouring a stored path without that check would hand a guard a registry
 * URL and then bounce them, which reads as a fault rather than a boundary.
 */
function destinationFor(profile, intended) {
  if (intended) {
    const owner = PORTAL_LIST.find((portal) => intended.startsWith(`${portal.base}/`))
    if (owner && canEnter(profile, owner)) return intended
  }
  return homePortalFor(profile).home
}
