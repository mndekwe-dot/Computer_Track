import { useState } from 'react'
import { LogIn, TriangleAlert } from 'lucide-react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { reasonText, takeSignedOutReason } from '../auth/session'
import { Brand } from '../components/Brand'
import { ErrorNote, Field } from '../components/ui'
import { canEnter, homePortalFor } from '../portals'

const DEMO_ACCOUNTS = {
  guard: ['guard1', 'guard2'],
  registry: ['registrar'],
  admin: ['admin'],
}

export default function PortalLogin({ portal }) {
  const { login, logout, user, isAuthenticated, loading } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  // Where they were heading before being asked to sign in.
  const intended = location.state?.from?.pathname
  // Read once on mount, so it does not reappear after a later failed attempt.
  const [signedOutReason] = useState(() => takeSignedOutReason())
  const [form, setForm] = useState({ username: '', password: '', otp_token: '' })
  const [error, setError] = useState(null)
  const [wrongPortal, setWrongPortal] = useState(null)
  const [needsCode, setNeedsCode] = useState(false)
  const [busy, setBusy] = useState(false)

  if (loading) return <div className="page-loading">Checking your session…</div>

  // Already signed in: go straight through if this is their portal, otherwise
  // bounce to the one that is.
  if (isAuthenticated && !wrongPortal) {
    if (!canEnter(user, portal)) {
      return <Navigate to={homePortalFor(user).home} replace />
    }
    // Back to whatever they were trying to open, if it belongs to this portal.
    const target =
      intended && intended.startsWith(`${portal.base}/`) ? intended : portal.home
    return <Navigate to={target} replace />
  }

  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    setError(null)
    setWrongPortal(null)
    try {
      const profile = await login(form.username.trim(), form.password, form.otp_token.trim())
      if (!canEnter(profile, portal)) {
        // Their credentials are valid, just not for this door. Say so plainly
        // and hand them the right link instead of a bare "denied".
        const theirs = homePortalFor(profile)
        logout()
        setWrongPortal({ profile, theirs })
        return
      }
      navigate(
        intended && intended.startsWith(`${portal.base}/`) ? intended : portal.home,
        { replace: true },
      )
    } catch (err) {
      // The password was right but a second factor is needed - reveal the
      // code field rather than showing a bare failure.
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
    <div className="login-page" style={{ '--brand': portal.accent, '--brand-dark': portal.accentDark }}>
      {/* The portal's own colour fills one side of the screen, so a guard at a
          shared terminal knows which door they are at before reading a word. */}
      <aside className="login-side">
        <Brand title={portal.loginTitle} subtitle={portal.tagline} size="md" as="h1" />
        <p>{portal.loginBlurb}</p>
        <span className="login-stripe" aria-hidden="true" />
      </aside>

      <div className="login-main">
      <form className="login-card" onSubmit={submit}>
        <h2 className="login-title">Sign in</h2>

        {wrongPortal && (
          <div className="note note-warn" role="alert">
            <div>
              <TriangleAlert size={16} aria-hidden="true" style={{ verticalAlign: '-3px' }} />{' '}
              <strong>This is not your portal.</strong>
              <div style={{ marginTop: 5 }}>
                {wrongPortal.profile.full_name} is a {wrongPortal.profile.role_display}. Sign in
                at the {wrongPortal.theirs.name} portal instead.
              </div>
              <button
                type="button"
                className="btn btn-outline btn-sm"
                style={{ marginTop: 10 }}
                onClick={() => navigate(`${wrongPortal.theirs.base}/login`)}
              >
                Go to {wrongPortal.theirs.name}
              </button>
            </div>
          </div>
        )}

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
          <strong>Demo accounts for this portal</strong> (password <code>passw0rd!</code>)
          <br />
          {DEMO_ACCOUNTS[portal.key].join(', ')}
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
