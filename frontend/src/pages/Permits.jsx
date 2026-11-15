import { useCallback, useEffect, useState } from 'react'
import { Plus, X } from 'lucide-react'
import { Link } from 'react-router-dom'
import { devices } from '../api/endpoints'
import { useAuth } from '../auth/AuthContext'
import { usePortal } from '../auth/PortalContext'
import { DataState } from '../components/DataState'
import { PageHeader } from '../components/PortalShell'
import { Field, Modal, Pagination, StatusPill, formatDateTime } from '../components/ui'
import { useToast } from '../components/Toasts'

const PERMIT_COLUMNS = ['Carrier', 'Computer', 'Owner', 'Valid from', 'Valid until', 'State', ' ']

/** Datetime-local inputs want "YYYY-MM-DDTHH:mm" in the viewer's own timezone. */
function toLocalInput(date) {
  const offset = date.getTimezoneOffset() * 60000
  return new Date(date.getTime() - offset).toISOString().slice(0, 16)
}

export default function Permits() {
  const { canManageRecords } = useAuth()
  const portal = usePortal()
  const [data, setData] = useState(null)
  const [onlyLive, setOnlyLive] = useState(true)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [creating, setCreating] = useState(false)
  const toast = useToast()

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    devices
      .permits({ valid: onlyLive ? '1' : '', page })
      .then(setData)
      .catch(setError)
      .finally(() => setLoading(false))
  }, [onlyLive, page])

  useEffect(load, [load])

  const revoke = async (permit) => {
    try {
      await devices.revokePermit(permit.id)
      toast.show({ tone: 'success', message: `Permit for ${permit.bearer_name} revoked.` })
      load()
    } catch (err) {
      toast.show({ tone: 'error', message: err.readable })
    }
  }

  return (
    <>
      <PageHeader
        title="Permits"
        subtitle="Written permission for somebody other than the owner to carry a computer"
      >
        {canManageRecords && (
          <button type="button" className="btn btn-primary" onClick={() => setCreating(true)}>
            <Plus size={16} aria-hidden="true" />
            Issue permit
          </button>
        )}
      </PageHeader>

      <div className="content">
        <div className="toolbar">
          <label className="check-inline">
            <input
              type="checkbox"
              checked={onlyLive}
              onChange={(e) => {
                setPage(1)
                setOnlyLive(e.target.checked)
              }}
            />
            Only permits valid right now
          </label>
        </div>

        <DataState
          loading={loading}
          error={error}
          onRetry={load}
          rows={data?.results ?? null}
          columns={PERMIT_COLUMNS}
          skeletonRows={5}
          emptyTitle="No permits"
          emptyBody="When a student lends their laptop to somebody else, issue a permit here so the gate lets the carrier through."
        >
          <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Carrier</th>
                    <th>Computer</th>
                    <th className="hide-md">Owner</th>
                    <th className="hide-sm">Valid from</th>
                    <th>Valid until</th>
                    <th>State</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {data?.results.map((permit) => (
                    <tr key={permit.id}>
                      <td>
                        <strong>{permit.bearer_name}</strong>
                        {permit.bearer_id_number && (
                          <div className="muted mono">{permit.bearer_id_number}</div>
                        )}
                        {permit.relationship && (
                          <div className="muted">{permit.relationship}</div>
                        )}
                      </td>
                      <td className="mono">
                        <Link to={`${portal.base}/devices/${permit.device}`}>
                          {permit.device_serial}
                        </Link>
                      </td>
                      <td className="hide-md">{permit.owner_name}</td>
                      <td className="hide-sm">{formatDateTime(permit.valid_from)}</td>
                      <td className="nowrap">{formatDateTime(permit.valid_to)}</td>
                      <td>
                        {permit.is_revoked ? (
                          <StatusPill status="DENIED">REVOKED</StatusPill>
                        ) : permit.is_valid_now ? (
                          <StatusPill status="ACTIVE">LIVE</StatusPill>
                        ) : (
                          <StatusPill status="RETIRED">NOT ACTIVE</StatusPill>
                        )}
                      </td>
                      <td>
                        {!permit.is_revoked && canManageRecords && (
                          <button
                            type="button"
                            className="btn btn-ghost btn-sm"
                            onClick={() => revoke(permit)}
                          >
                            <X size={14} aria-hidden="true" />
                            <span className="hide-sm">Revoke</span>
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          <Pagination count={data?.count ?? 0} page={page} onChange={setPage} />
        </DataState>
      </div>

      {creating && (
        <PermitForm
          onClose={() => setCreating(false)}
          onDone={(message) => {
            setCreating(false)
            toast.show({ tone: 'success', message })
            load()
          }}
        />
      )}

    </>
  )
}

function PermitForm({ onClose, onDone }) {
  const now = new Date()
  const inAWeek = new Date(now.getTime() + 7 * 24 * 3600 * 1000)

  const [deviceQuery, setDeviceQuery] = useState('')
  const [matches, setMatches] = useState([])
  const [form, setForm] = useState({
    device: '',
    bearer_name: '',
    bearer_id_number: '',
    relationship: '',
    reason: '',
    valid_from: toLocalInput(now),
    valid_to: toLocalInput(inAWeek),
  })
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(false)

  const set = (key) => (event) => setForm({ ...form, [key]: event.target.value })

  useEffect(() => {
    if (!deviceQuery || form.device) {
      setMatches([])
      return undefined
    }
    const timer = setTimeout(() => {
      devices
        .list({ search: deviceQuery, page_size: 6 })
        .then((data) => setMatches(data.results || []))
        .catch(() => setMatches([]))
    }, 250)
    return () => clearTimeout(timer)
  }, [deviceQuery, form.device])

  const submit = async (event) => {
    event.preventDefault()
    if (!form.device) {
      setErrors({ device: 'Choose the computer this permit covers.' })
      return
    }
    setBusy(true)
    setErrors({})
    try {
      await devices.createPermit({
        ...form,
        valid_from: new Date(form.valid_from).toISOString(),
        valid_to: new Date(form.valid_to).toISOString(),
      })
      onDone(`Permit issued to ${form.bearer_name}.`)
    } catch (error) {
      setErrors(error.fieldErrors || { detail: error.readable })
      setBusy(false)
    }
  }

  return (
    <Modal title="Issue a permit" onClose={onClose} wide>
      <form onSubmit={submit}>
        {errors.detail && <div className="note note-error">{errors.detail}</div>}

        <Field label="Computer" required error={errors.device} hint="Search by serial or owner.">
          <input
            value={deviceQuery}
            onChange={(e) => {
              setDeviceQuery(e.target.value)
              setForm({ ...form, device: '' })
            }}
            placeholder="HP12345678 or 218001234"
            autoFocus
          />
        </Field>
        {matches.length > 0 && (
          <div className="row-actions" style={{ marginTop: -6, marginBottom: 14 }}>
            {matches.map((device) => (
              <button
                key={device.id}
                type="button"
                className="btn btn-outline btn-sm"
                onClick={() => {
                  setForm({ ...form, device: device.id })
                  setDeviceQuery(`${device.serial_number} - ${device.owner_detail?.full_name}`)
                  setMatches([])
                }}
              >
                {device.serial_number} - {device.owner_detail?.reg_number}
              </button>
            ))}
          </div>
        )}

        <div className="form-grid">
          <Field label="Carrier's full name" required error={errors.bearer_name}>
            <input value={form.bearer_name} onChange={set('bearer_name')} required />
          </Field>
          <Field
            label="Carrier's ID or reg number"
            error={errors.bearer_id_number}
            hint="The guard checks this against the ID presented."
          >
            <input value={form.bearer_id_number} onChange={set('bearer_id_number')} />
          </Field>
          <Field label="Relationship to owner" error={errors.relationship}>
            <input
              value={form.relationship}
              onChange={set('relationship')}
              placeholder="Classmate"
            />
          </Field>
          <Field label="Valid from" required error={errors.valid_from}>
            <input
              type="datetime-local"
              value={form.valid_from}
              onChange={set('valid_from')}
              required
            />
          </Field>
          <Field label="Valid until" required error={errors.valid_to}>
            <input
              type="datetime-local"
              value={form.valid_to}
              onChange={set('valid_to')}
              required
            />
          </Field>
        </div>

        <Field label="Reason" error={errors.reason}>
          <textarea
            value={form.reason}
            onChange={set('reason')}
            placeholder="Group project, repair collection, owner away on teaching practice…"
          />
        </Field>

        <div className="form-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={busy}>
            {busy ? 'Issuing…' : 'Issue permit'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
