import { useEffect, useState } from 'react'
import { Save, ShieldCheck, ShieldOff } from 'lucide-react'
import { auth, campus } from '../api/endpoints'
import { useAuth } from '../auth/AuthContext'
import { usePortal } from '../auth/PortalContext'
import { PageHeader } from '../components/PortalShell'
import { Field, StatusPill, Toast } from '../components/ui'

export default function Settings() {
  const { user, patchUser } = useAuth()
  const portal = usePortal()
  const [gates, setGates] = useState([])
  const [profile, setProfile] = useState({
    first_name: user?.first_name || '',
    last_name: user?.last_name || '',
    email: user?.email || '',
    phone: user?.phone || '',
    default_gate: user?.default_gate || '',
  })
  const [passwords, setPasswords] = useState({ current_password: '', new_password: '' })
  const [errors, setErrors] = useState({})
  const [toast, setToast] = useState(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    campus.gates().then(setGates).catch(() => {})
  }, [])

  const saveProfile = async (event) => {
    event.preventDefault()
    setBusy(true)
    setErrors({})
    try {
      const updated = await auth.updateMe({
        ...profile,
        default_gate: profile.default_gate || null,
      })
      patchUser(updated)
      setToast({ tone: 'success', message: 'Your details were saved.' })
    } catch (error) {
      setErrors(error.fieldErrors || { detail: error.readable })
    } finally {
      setBusy(false)
    }
  }

  const changePassword = async (event) => {
    event.preventDefault()
    setBusy(true)
    setErrors({})
    try {
      await auth.changePassword(passwords)
      setPasswords({ current_password: '', new_password: '' })
      setToast({ tone: 'success', message: 'Password changed.' })
    } catch (error) {
      setErrors(error.fieldErrors || { detail: error.readable })
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <PageHeader
        title="My Account"
        subtitle={`${user?.role_display} · ${portal.name} portal`}
      />

      <div className="content">
        <div className="two-col">
          <form className="card" onSubmit={saveProfile}>
            <div className="card-header">
              <h3>Your details</h3>
            </div>
            {errors.detail && <div className="note note-error">{errors.detail}</div>}
            <div className="form-grid">
              <Field label="First name" error={errors.first_name}>
                <input
                  value={profile.first_name}
                  onChange={(e) => setProfile({ ...profile, first_name: e.target.value })}
                />
              </Field>
              <Field label="Last name" error={errors.last_name}>
                <input
                  value={profile.last_name}
                  onChange={(e) => setProfile({ ...profile, last_name: e.target.value })}
                />
              </Field>
              <Field label="Email" error={errors.email}>
                <input
                  type="email"
                  value={profile.email}
                  onChange={(e) => setProfile({ ...profile, email: e.target.value })}
                />
              </Field>
              <Field label="Phone" error={errors.phone}>
                <input
                  value={profile.phone}
                  onChange={(e) => setProfile({ ...profile, phone: e.target.value })}
                />
              </Field>
            </div>
            <Field
              label="Gate you normally work at"
              error={errors.default_gate}
              hint="Pre-selected every time you open the console."
            >
              <select
                value={profile.default_gate}
                onChange={(e) => setProfile({ ...profile, default_gate: e.target.value })}
              >
                <option value="">No default gate</option>
                {gates.map((gate) => (
                  <option key={gate.id} value={gate.id}>
                    {gate.name}
                  </option>
                ))}
              </select>
            </Field>
            <div className="form-actions">
              <button type="submit" className="btn btn-primary" disabled={busy}>
                <Save size={16} aria-hidden="true" />
                {busy ? 'Saving…' : 'Save changes'}
              </button>
            </div>
          </form>

          <form className="card" onSubmit={changePassword}>
            <div className="card-header">
              <h3>Change password</h3>
            </div>
            <Field label="Current password" required error={errors.current_password}>
              <input
                type="password"
                value={passwords.current_password}
                onChange={(e) =>
                  setPasswords({ ...passwords, current_password: e.target.value })
                }
                required
                autoComplete="current-password"
              />
            </Field>
            <Field
              label="New password"
              required
              error={errors.new_password}
              hint="At least 8 characters."
            >
              <input
                type="password"
                value={passwords.new_password}
                onChange={(e) => setPasswords({ ...passwords, new_password: e.target.value })}
                required
                autoComplete="new-password"
              />
            </Field>
            <div className="form-actions">
              <button type="submit" className="btn btn-primary" disabled={busy}>
                Change password
              </button>
            </div>
          </form>
        </div>

        <TwoFactorPanel onToast={setToast} />
      </div>

      <Toast toast={toast} onDismiss={() => setToast(null)} />
    </>
  )
}

/**
 * Two-factor enrolment. Offered to everyone, pressed on administrators - they
 * reach every portal and can reset any password, so their account is the one
 * worth the extra step.
 */
function TwoFactorPanel({ onToast }) {
  const { user, patchUser } = useAuth()
  const [status, setStatus] = useState(null)
  const [setup, setSetup] = useState(null)
  const [code, setCode] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const load = () => auth.twoFactorStatus().then(setStatus).catch(() => {})
  useEffect(load, [])

  const begin = async () => {
    setBusy(true)
    setError('')
    try {
      setSetup(await auth.twoFactorBegin())
    } catch (err) {
      setError(err.readable)
    } finally {
      setBusy(false)
    }
  }

  const confirm = async (event) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      await auth.twoFactorConfirm(code.trim())
      setSetup(null)
      setCode('')
      patchUser({ two_factor_enabled: true })
      onToast({ tone: 'success', message: 'Two-factor authentication is on.' })
      load()
    } catch (err) {
      setError(err.fieldErrors?.token || err.readable)
    } finally {
      setBusy(false)
    }
  }

  const disable = async (event) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      await auth.twoFactorDisable(password)
      setPassword('')
      patchUser({ two_factor_enabled: false })
      onToast({ tone: 'warn', message: 'Two-factor authentication turned off.' })
      load()
    } catch (err) {
      setError(err.fieldErrors?.password || err.readable)
    } finally {
      setBusy(false)
    }
  }

  if (!status) return null

  return (
    <div className="card">
      <div className="card-header">
        <h3>Two-factor authentication</h3>
        <StatusPill status={status.enabled ? 'ACTIVE' : 'PENDING'}>
          {status.enabled ? 'ON' : 'OFF'}
        </StatusPill>
      </div>

      {error && <div className="note note-error">{error}</div>}

      {status.enabled ? (
        <>
          <p className="muted" style={{ marginTop: 0, fontSize: 13.5 }}>
            You will be asked for a code from your authenticator app each time you sign in.
          </p>
          <form onSubmit={disable}>
            <Field
              label="Turn it off"
              hint="Confirm with your password. Only you can do this - an administrator cannot turn off somebody else's."
            >
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Your password"
                autoComplete="current-password"
                required
              />
            </Field>
            <div className="form-actions">
              <button type="submit" className="btn btn-outline" disabled={busy}>
                <ShieldOff size={16} aria-hidden="true" />
                Turn off two-factor
              </button>
            </div>
          </form>
        </>
      ) : setup ? (
        <form onSubmit={confirm}>
          <p className="muted" style={{ marginTop: 0, fontSize: 13.5 }}>
            Scan this with Google Authenticator, Authy or any TOTP app, then enter the code it
            shows to finish.
          </p>
          <div style={{ textAlign: 'center', margin: '14px 0' }}>
            <img
              src={setup.qr_png_base64}
              alt="Two-factor QR code"
              style={{ width: 190, height: 190 }}
            />
            <div className="muted" style={{ fontSize: 12, marginTop: 8 }}>
              Cannot scan? Enter this key by hand:
              <br />
              <code className="mono">{setup.secret}</code>
            </div>
          </div>
          <Field label="Code from the app" required>
            <input
              value={code}
              onChange={(e) => setCode(e.target.value)}
              inputMode="numeric"
              maxLength={8}
              placeholder="000000"
              autoFocus
              required
            />
          </Field>
          <div className="form-actions">
            <button type="button" className="btn btn-ghost" onClick={() => setSetup(null)}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={busy}>
              {busy ? 'Checking…' : 'Finish setup'}
            </button>
          </div>
        </form>
      ) : (
        <>
          {status.recommended && (
            <div className="note note-warn">
              <span>
                <ShieldCheck size={16} aria-hidden="true" style={{ verticalAlign: '-3px' }} /> Your
                account reaches every portal and can reset any password. A second factor is
                strongly recommended.
              </span>
            </div>
          )}
          <p className="muted" style={{ marginTop: 0, fontSize: 13.5 }}>
            Adds a 6-digit code from your phone to each sign-in. Nothing changes until you have
            scanned the code and confirmed it works, so you cannot lock yourself out.
          </p>
          <div className="form-actions">
            <button type="button" className="btn btn-primary" onClick={begin} disabled={busy}>
              <ShieldCheck size={16} aria-hidden="true" />
              Set up two-factor
            </button>
          </div>
        </>
      )}
    </div>
  )
}
