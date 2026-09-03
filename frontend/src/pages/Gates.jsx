import { useCallback, useEffect, useState } from 'react'
import { Pencil, Plus } from 'lucide-react'
import { campus } from '../api/endpoints'
import { DataState } from '../components/DataState'
import { PageHeader } from '../components/PortalShell'
import { Field, Modal, StatusPill } from '../components/ui'
import { useToast } from '../components/Toasts'

const GATE_COLUMNS = ['Gate', 'Code', 'Location', 'Scans today', 'State', ' ']

export default function Gates() {
  const [gates, setGates] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [editing, setEditing] = useState(null)
  const toast = useToast()

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    campus
      .gates()
      .then(setGates)
      .catch(setError)
      .finally(() => setLoading(false))
  }, [])

  useEffect(load, [load])

  return (
    <>
      <PageHeader title="Gates" subtitle="Entry points where computers are checked">
        <button type="button" className="btn btn-primary" onClick={() => setEditing({})}>
          <Plus size={16} aria-hidden="true" />
          Add gate
        </button>
      </PageHeader>

      <div className="content">
        <DataState
          loading={loading}
          error={error}
          onRetry={load}
          rows={gates ?? null}
          columns={GATE_COLUMNS}
          skeletonRows={4}
          emptyTitle="No gates yet"
          emptyBody="Add each manned entrance so scans can be attributed to a location."
        >
          <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Gate</th>
                    <th>Code</th>
                    <th className="hide-sm">Location</th>
                    <th>Scans today</th>
                    <th>State</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {gates?.map((gate) => (
                    <tr key={gate.id}>
                      <td>
                        <strong>{gate.name}</strong>
                        {gate.notes && <div className="muted">{gate.notes}</div>}
                      </td>
                      <td className="mono">{gate.code}</td>
                      <td className="hide-sm">{gate.location || ' - '}</td>
                      <td>{gate.scans_today}</td>
                      <td>
                        <StatusPill status={gate.is_active ? 'ACTIVE' : 'RETIRED'}>
                          {gate.is_active ? 'OPEN' : 'CLOSED'}
                        </StatusPill>
                      </td>
                      <td>
                        <button
                          type="button"
                          className="btn btn-ghost btn-sm"
                          onClick={() => setEditing(gate)}
                          aria-label={`Edit ${gate.name}`}
                        >
                          <Pencil size={14} aria-hidden="true" />
                          <span className="hide-sm">Edit</span>
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
          </div>
        </DataState>
      </div>

      {editing && (
        <GateForm
          gate={editing}
          onClose={() => setEditing(null)}
          onDone={(message) => {
            setEditing(null)
            toast.show({ tone: 'success', message })
            load()
          }}
        />
      )}

    </>
  )
}

function GateForm({ gate, onClose, onDone }) {
  const isNew = !gate.id
  const [form, setForm] = useState({
    name: gate.name || '',
    code: gate.code || '',
    location: gate.location || '',
    notes: gate.notes || '',
    is_active: gate.is_active ?? true,
  })
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(false)

  const set = (key) => (event) => setForm({ ...form, [key]: event.target.value })

  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    setErrors({})
    try {
      if (isNew) await campus.createGate(form)
      else await campus.updateGate(gate.id, form)
      onDone(isNew ? 'Gate added.' : 'Gate updated.')
    } catch (error) {
      setErrors(error.fieldErrors || { detail: error.readable })
      setBusy(false)
    }
  }

  return (
    <Modal title={isNew ? 'Add a gate' : `Edit ${gate.name}`} onClose={onClose}>
      <form onSubmit={submit}>
        {errors.detail && <div className="note note-error">{errors.detail}</div>}
        <Field label="Name" required error={errors.name}>
          <input
            value={form.name}
            onChange={set('name')}
            required
            autoFocus
            placeholder="Main Gate"
          />
        </Field>
        <Field label="Code" required error={errors.code} hint="Short label shown on reports.">
          <input value={form.code} onChange={set('code')} required placeholder="MAIN" />
        </Field>
        <Field label="Location" error={errors.location}>
          <input value={form.location} onChange={set('location')} />
        </Field>
        <Field label="Notes" error={errors.notes}>
          <textarea value={form.notes} onChange={set('notes')} />
        </Field>
        <label className="check-inline" style={{ marginBottom: 8 }}>
          <input
            type="checkbox"
            checked={form.is_active}
            onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
          />
          Gate is open and manned
        </label>
        <div className="form-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={busy}>
            {busy ? 'Saving…' : isNew ? 'Add gate' : 'Save changes'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
