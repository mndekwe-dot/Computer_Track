import { useCallback, useEffect, useState } from 'react'
import { KeyRound, Pencil, Plus } from 'lucide-react'
import { auth, campus } from '../api/endpoints'
import { DataState } from '../components/DataState'
import { PageHeader } from '../components/PortalShell'
import { Field, Modal, Pagination, StatusPill, Toast, formatDateTime } from '../components/ui'
import { useDebouncedValue } from '../hooks/useLiveSearch'

const ROLES = [
  ['GUARD', 'Security guard - Security Gate portal'],
  ['REGISTRAR', 'Registration officer - Registration Office portal'],
  ['ADMIN', 'Administrator - every portal, plus staff accounts'],
]
const STAFF_COLUMNS = ['Name', 'Username', 'Role', 'Gate', 'Last signed in', 'State', ' ']

export default function Staff() {
  const [data, setData] = useState(null)
  const [gates, setGates] = useState([])
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [editing, setEditing] = useState(null)
  const [resetting, setResetting] = useState(null)
  const [toast, setToast] = useState(null)

  const debouncedSearch = useDebouncedValue(search)

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    auth
      .users({ search: debouncedSearch, page })
      .then(setData)
      .catch(setError)
      .finally(() => setLoading(false))
  }, [debouncedSearch, page])

  useEffect(load, [load])
  useEffect(() => {
    campus.gates().then(setGates).catch(() => {})
  }, [])

  return (
    <>
      <PageHeader title="Staff Accounts" subtitle="Who can sign in, and which portal they use">
        <button type="button" className="btn btn-primary" onClick={() => setEditing({})}>
          <Plus size={16} aria-hidden="true" />
          Add staff member
        </button>
      </PageHeader>

      <div className="content">
        <div className="toolbar">
          <input
            className="grow"
            placeholder="Search by name, username or staff number…"
            value={search}
            onChange={(e) => {
              setPage(1)
              setSearch(e.target.value)
            }}
          />
        </div>

        <DataState
          loading={loading}
          error={error}
          onRetry={load}
          rows={data?.results ?? null}
          columns={STAFF_COLUMNS}
          skeletonRows={5}
          emptyTitle="No staff match that search"
          emptyBody="Try a different name, username or staff number."
        >
          <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th className="hide-sm">Username</th>
                    <th>Role</th>
                    <th className="hide-md">Gate</th>
                    <th className="hide-md">Last signed in</th>
                    <th>State</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {data?.results.map((person) => (
                    <tr key={person.id}>
                      <td>
                        <strong>{person.full_name}</strong>
                        {person.staff_number && (
                          <div className="muted mono">{person.staff_number}</div>
                        )}
                      </td>
                      <td className="hide-sm mono">{person.username}</td>
                      <td>{person.role_display}</td>
                      <td className="hide-md">{person.default_gate_name || ' - '}</td>
                      <td className="hide-md">{formatDateTime(person.last_login)}</td>
                      <td>
                        <StatusPill status={person.is_active ? 'ACTIVE' : 'RETIRED'}>
                          {person.is_active ? 'ACTIVE' : 'DISABLED'}
                        </StatusPill>
                      </td>
                      <td>
                        <div className="row-actions">
                          <button
                            type="button"
                            className="btn btn-ghost btn-sm"
                            onClick={() => setEditing(person)}
                            aria-label={`Edit ${person.username}`}
                          >
                            <Pencil size={14} aria-hidden="true" />
                          </button>
                          <button
                            type="button"
                            className="btn btn-ghost btn-sm"
                            onClick={() => setResetting(person)}
                            aria-label={`Reset password for ${person.username}`}
                          >
                            <KeyRound size={14} aria-hidden="true" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          <Pagination count={data?.count ?? 0} page={page} onChange={setPage} />
        </DataState>
      </div>

      {editing && (
        <StaffForm
          person={editing}
          gates={gates}
          onClose={() => setEditing(null)}
          onDone={(message) => {
            setEditing(null)
            setToast({ tone: 'success', message })
            load()
          }}
        />
      )}

      {resetting && (
        <ResetDialog
          person={resetting}
          onClose={() => setResetting(null)}
          onDone={(message) => {
            setResetting(null)
            setToast({ tone: 'success', message })
          }}
        />
      )}

      <Toast toast={toast} onDismiss={() => setToast(null)} />
    </>
  )
}

function StaffForm({ person, gates, onClose, onDone }) {
  const isNew = !person.id
  const [form, setForm] = useState({
    username: person.username || '',
    first_name: person.first_name || '',
    last_name: person.last_name || '',
    email: person.email || '',
    phone: person.phone || '',
    staff_number: person.staff_number || '',
    role: person.role || 'GUARD',
    default_gate: person.default_gate || '',
    is_active: person.is_active ?? true,
    password: '',
  })
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(false)

  const set = (key) => (event) => setForm({ ...form, [key]: event.target.value })

  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    setErrors({})
    const payload = {
      ...form,
      default_gate: form.default_gate || null,
      staff_number: form.staff_number || null,
    }
    if (!payload.password) delete payload.password
    try {
      if (isNew) await auth.createUser(payload)
      else await auth.updateUser(person.id, payload)
      onDone(isNew ? 'Staff account created.' : 'Staff account updated.')
    } catch (error) {
      setErrors(error.fieldErrors || { detail: error.readable })
      setBusy(false)
    }
  }

  return (
    <Modal title={isNew ? 'Add a staff member' : `Edit ${person.full_name}`} onClose={onClose} wide>
      <form onSubmit={submit}>
        {errors.detail && <div className="note note-error">{errors.detail}</div>}
        <div className="form-grid">
          <Field label="Username" required error={errors.username}>
            <input value={form.username} onChange={set('username')} required autoFocus />
          </Field>
          <Field
            label={isNew ? 'Password' : 'New password'}
            required={isNew}
            error={errors.password}
            hint={isNew ? 'At least 8 characters.' : 'Leave blank to keep the current password.'}
          >
            <input
              type="password"
              value={form.password}
              onChange={set('password')}
              required={isNew}
              autoComplete="new-password"
            />
          </Field>
          <Field label="First name" error={errors.first_name}>
            <input value={form.first_name} onChange={set('first_name')} />
          </Field>
          <Field label="Last name" error={errors.last_name}>
            <input value={form.last_name} onChange={set('last_name')} />
          </Field>
          <Field label="Staff number" error={errors.staff_number}>
            <input value={form.staff_number} onChange={set('staff_number')} />
          </Field>
          <Field label="Phone" error={errors.phone}>
            <input value={form.phone} onChange={set('phone')} />
          </Field>
          <Field label="Email" error={errors.email}>
            <input type="email" value={form.email} onChange={set('email')} />
          </Field>
          <Field label="Default gate" error={errors.default_gate}>
            <select value={form.default_gate} onChange={set('default_gate')}>
              <option value=""> - </option>
              {gates.map((gate) => (
                <option key={gate.id} value={gate.id}>
                  {gate.name}
                </option>
              ))}
            </select>
          </Field>
        </div>

        <Field
          label="Role"
          required
          error={errors.role}
          hint="This decides which portal they sign in to."
        >
          <select value={form.role} onChange={set('role')}>
            {ROLES.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </Field>

        <label className="check-inline" style={{ marginBottom: 8 }}>
          <input
            type="checkbox"
            checked={form.is_active}
            onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
          />
          Account is active and may sign in
        </label>

        <div className="form-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={busy}>
            {busy ? 'Saving…' : isNew ? 'Create account' : 'Save changes'}
          </button>
        </div>
      </form>
    </Modal>
  )
}

function ResetDialog({ person, onClose, onDone }) {
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      await auth.resetPassword(person.id, password)
      onDone(`Password reset for ${person.username}. Give it to them in person.`)
    } catch (err) {
      setError(err.fieldErrors?.new_password || err.readable)
      setBusy(false)
    }
  }

  return (
    <Modal title={`Reset password for ${person.username}`} onClose={onClose}>
      <form onSubmit={submit}>
        <Field label="New password" required error={error} hint="At least 8 characters.">
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoFocus
            autoComplete="new-password"
          />
        </Field>
        <div className="form-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={busy}>
            {busy ? 'Resetting…' : 'Reset password'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
