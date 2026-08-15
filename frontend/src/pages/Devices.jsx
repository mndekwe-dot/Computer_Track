import { useCallback, useEffect, useState } from 'react'
import { ExternalLink, Pencil, Plus } from 'lucide-react'
import { Link, useSearchParams } from 'react-router-dom'
import { mediaUrl } from '../api/client'
import { devices, students } from '../api/endpoints'
import { useAuth } from '../auth/AuthContext'
import { usePortal } from '../auth/PortalContext'
import { DataState } from '../components/DataState'
import { PhotoInput } from '../components/PhotoInput'
import { PageHeader } from '../components/PortalShell'
import { Field, Modal, Pagination, StatusPill, Toast } from '../components/ui'
import { useDebouncedValue } from '../hooks/useLiveSearch'

const TYPES = ['LAPTOP', 'TABLET', 'DESKTOP', 'MONITOR', 'PROJECTOR', 'OTHER']
const STATUSES = ['ACTIVE', 'PENDING', 'LOST', 'STOLEN', 'RETIRED']
const DEVICE_COLUMNS = ['Serial', 'Computer', 'Owner', 'Asset tag', 'Status', ' ']

export default function Devices() {
  const { canManageRecords } = useAuth()
  const portal = usePortal()
  const [params, setParams] = useSearchParams()
  const [data, setData] = useState(null)
  const [filters, setFilters] = useState({
    search: '',
    status: '',
    device_type: '',
    owner: params.get('owner') || '',
    flagged: params.get('flagged') || '',
  })
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [editing, setEditing] = useState(null)
  const [toast, setToast] = useState(null)

  const search = useDebouncedValue(filters.search)

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    devices
      .list({ ...filters, search, page })
      .then(setData)
      .catch(setError)
      .finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.status, filters.device_type, filters.owner, filters.flagged, search, page])

  useEffect(load, [load])

  const updateFilter = (key, value) => {
    setPage(1)
    setFilters((current) => ({ ...current, [key]: value }))
    if (key === 'owner' || key === 'flagged') {
      const next = new URLSearchParams(params)
      if (value) next.set(key, value)
      else next.delete(key)
      setParams(next, { replace: true })
    }
  }

  return (
    <>
      <PageHeader title="Computers" subtitle="Everything registered to a student">
        {canManageRecords && (
          <button type="button" className="btn btn-primary" onClick={() => setEditing({})}>
            <Plus size={16} aria-hidden="true" />
            Register computer
          </button>
        )}
      </PageHeader>

      <div className="content">
        <div className="toolbar">
          <input
            className="grow"
            placeholder="Search serial, brand, owner name or reg number…"
            value={filters.search}
            onChange={(e) => updateFilter('search', e.target.value)}
          />
          <select value={filters.status} onChange={(e) => updateFilter('status', e.target.value)}>
            <option value="">All statuses</option>
            {STATUSES.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>
          <select
            value={filters.device_type}
            onChange={(e) => updateFilter('device_type', e.target.value)}
          >
            <option value="">All types</option>
            {TYPES.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
          <label className="check-inline">
            <input
              type="checkbox"
              checked={filters.flagged === '1'}
              onChange={(e) => updateFilter('flagged', e.target.checked ? '1' : '')}
            />
            Blocked only
          </label>
        </div>

        <DataState
          loading={loading}
          error={error}
          onRetry={load}
          rows={data?.results ?? null}
          columns={DEVICE_COLUMNS}
          emptyTitle="No computers match"
          emptyBody="Adjust the filters above."
        >
          <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Serial</th>
                    <th>Computer</th>
                    <th className="hide-sm">Owner</th>
                    <th className="hide-md">Asset tag</th>
                    <th>Status</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {data?.results.map((device) => (
                    <tr key={device.id}>
                      <td className="mono">{device.serial_number}</td>
                      <td>
                        <strong>{device.label}</strong>
                        <div className="muted">
                          {device.device_type_display}
                          {device.colour ? ` · ${device.colour}` : ''}
                        </div>
                      </td>
                      <td className="hide-sm">
                        {device.owner_detail?.full_name}
                        <div className="muted mono">{device.owner_detail?.reg_number}</div>
                      </td>
                      <td className="hide-md mono">{device.asset_tag || ' - '}</td>
                      <td>
                        <StatusPill status={device.status}>{device.status_display}</StatusPill>
                        {device.is_blocked && device.status === 'ACTIVE' && (
                          <div style={{ marginTop: 4 }}>
                            <StatusPill status="HOLD">BLOCKED</StatusPill>
                          </div>
                        )}
                      </td>
                      <td>
                        <div className="row-actions">
                          <Link
                            className="btn btn-ghost btn-sm"
                            to={`${portal.base}/devices/${device.id}`}
                          >
                            <ExternalLink size={14} aria-hidden="true" />
                            <span className="hide-sm">Open</span>
                          </Link>
                          {canManageRecords && (
                            <button
                              type="button"
                              className="btn btn-ghost btn-sm"
                              onClick={() => setEditing(device)}
                              aria-label={`Edit ${device.serial_number}`}
                            >
                              <Pencil size={14} aria-hidden="true" />
                            </button>
                          )}
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
        <DeviceForm
          device={editing}
          onClose={() => setEditing(null)}
          onSaved={(message) => {
            setEditing(null)
            setToast({ tone: 'success', message })
            load()
          }}
        />
      )}

      <Toast toast={toast} onDismiss={() => setToast(null)} />
    </>
  )
}

export function DeviceForm({ device, onClose, onSaved }) {
  const isNew = !device.id
  const [form, setForm] = useState({
    serial_number: device.serial_number || '',
    asset_tag: device.asset_tag || '',
    device_type: device.device_type || 'LAPTOP',
    brand: device.brand || '',
    model_name: device.model_name || '',
    colour: device.colour || '',
    distinguishing_marks: device.distinguishing_marks || '',
    owner: device.owner || '',
    status: device.status || 'ACTIVE',
    notes: device.notes || '',
    photo: null,
  })
  const [ownerQuery, setOwnerQuery] = useState(
    device.owner_detail
      ? `${device.owner_detail.reg_number} - ${device.owner_detail.full_name}`
      : '',
  )
  const [matches, setMatches] = useState([])
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(false)

  const set = (key) => (event) => setForm({ ...form, [key]: event.target.value })

  useEffect(() => {
    if (!ownerQuery || form.owner) {
      setMatches([])
      return undefined
    }
    // Debounced so typing a reg number does not fire a request per keystroke.
    const timer = setTimeout(() => {
      students
        .list({ search: ownerQuery, page_size: 6 })
        .then((data) => setMatches(data.results || []))
        .catch(() => setMatches([]))
    }, 250)
    return () => clearTimeout(timer)
  }, [ownerQuery, form.owner])

  const submit = async (event) => {
    event.preventDefault()
    if (!form.owner) {
      setErrors({ owner: 'Pick the student this computer belongs to.' })
      return
    }
    setBusy(true)
    setErrors({})
    const payload = { ...form, asset_tag: form.asset_tag || null }
    try {
      if (isNew) await devices.create(payload)
      else await devices.update(device.id, payload)
      onSaved(isNew ? 'Computer registered.' : 'Computer record updated.')
    } catch (error) {
      setErrors(error.fieldErrors || { detail: error.readable })
      setBusy(false)
    }
  }

  return (
    <Modal
      title={isNew ? 'Register a computer' : `Edit ${device.serial_number}`}
      onClose={onClose}
      wide
    >
      <form onSubmit={submit}>
        {errors.detail && <div className="note note-error">{errors.detail}</div>}

        <Field
          label="Owner"
          required
          error={errors.owner}
          hint="Type a registration number or name, then choose from the list."
        >
          <input
            value={ownerQuery}
            onChange={(e) => {
              setOwnerQuery(e.target.value)
              setForm({ ...form, owner: '' })
            }}
            placeholder="218001234 or Aline Uwase"
            autoFocus={isNew}
          />
        </Field>
        {matches.length > 0 && (
          <div className="row-actions" style={{ marginTop: -6, marginBottom: 14 }}>
            {matches.map((student) => (
              <button
                key={student.id}
                type="button"
                className="btn btn-outline btn-sm"
                onClick={() => {
                  setForm({ ...form, owner: student.id })
                  setOwnerQuery(`${student.reg_number} - ${student.full_name}`)
                  setMatches([])
                }}
              >
                {student.reg_number} - {student.full_name}
              </button>
            ))}
          </div>
        )}

        <div className="form-grid">
          <Field label="Serial number" required error={errors.serial_number}>
            <input value={form.serial_number} onChange={set('serial_number')} required />
          </Field>
          <Field
            label="Asset tag"
            error={errors.asset_tag}
            hint="University sticker code, if one is applied."
          >
            <input value={form.asset_tag} onChange={set('asset_tag')} />
          </Field>
          <Field label="Type" error={errors.device_type}>
            <select value={form.device_type} onChange={set('device_type')}>
              {TYPES.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Status" error={errors.status}>
            <select value={form.status} onChange={set('status')}>
              {STATUSES.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Brand" required error={errors.brand}>
            <input value={form.brand} onChange={set('brand')} required placeholder="HP" />
          </Field>
          <Field label="Model" error={errors.model_name}>
            <input
              value={form.model_name}
              onChange={set('model_name')}
              placeholder="EliteBook 840"
            />
          </Field>
          <Field label="Colour" error={errors.colour}>
            <input value={form.colour} onChange={set('colour')} placeholder="Silver" />
          </Field>
        </div>

        <Field
          label="Distinguishing marks"
          error={errors.distinguishing_marks}
          hint="What a guard can check at a glance - stickers, cracks, engravings."
        >
          <input value={form.distinguishing_marks} onChange={set('distinguishing_marks')} />
        </Field>

        <PhotoInput
          label="Photo of the computer"
          hint="What the guard compares against at the gate."
          value={form.photo}
          onChange={(photo) => setForm({ ...form, photo })}
          existingUrl={mediaUrl(device.photo)}
          error={errors.photo}
        />

        <Field label="Notes" error={errors.notes}>
          <textarea value={form.notes} onChange={set('notes')} />
        </Field>

        <div className="form-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={busy}>
            {busy ? 'Saving…' : isNew ? 'Register computer' : 'Save changes'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
