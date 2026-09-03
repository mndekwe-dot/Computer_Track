import { useCallback, useEffect, useState } from 'react'
import { Pencil, Plus } from 'lucide-react'
import { campus } from '../api/endpoints'
import { DataState } from '../components/DataState'
import { PageHeader } from '../components/PortalShell'
import { Field, Modal, StatusPill } from '../components/ui'
import { useToast } from '../components/Toasts'

/**
 * What kinds of equipment the register recognises.
 *
 * This was a fixed list in the code, so a university that checks lab
 * equipment or musical instruments at the gate had to file a bug and wait for
 * a release.
 */

const COLUMNS = ['Order', 'Type', 'Code', 'On the student form', 'Registered', 'State', ' ']

export default function EquipmentTypes() {
  const [rows, setRows] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [editing, setEditing] = useState(null)
  const toast = useToast()

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    campus
      .equipmentTypes()
      .then(setRows)
      .catch(setError)
      .finally(() => setLoading(false))
  }, [])

  useEffect(load, [load])

  const retire = async (row) => {
    try {
      const result = await campus.retireEquipmentType(row.id)
      toast.success(result.detail)
      load()
    } catch (err) {
      toast.error(err.readable)
    }
  }

  return (
    <>
      <PageHeader
        title="Equipment types"
        subtitle="What the register recognises, and what students may choose from"
      >
        <button type="button" className="btn btn-primary" onClick={() => setEditing({})}>
          <Plus size={16} aria-hidden="true" />
          Add type
        </button>
      </PageHeader>

      <div className="content">
        <DataState
          loading={loading}
          error={error}
          onRetry={load}
          rows={rows ?? null}
          columns={COLUMNS}
          skeletonRows={5}
          emptyTitle="No equipment types"
          emptyBody="Add at least one, or nothing can be registered."
        >
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th className="hide-sm">Order</th>
                  <th>Type</th>
                  <th className="hide-sm">Code</th>
                  <th>On the student form</th>
                  <th>Registered</th>
                  <th>State</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {rows?.map((row) => (
                  <tr key={row.id}>
                    <td className="hide-sm">{row.sort_order}</td>
                    <td>
                      <strong>{row.label}</strong>
                      {row.description && <div className="muted">{row.description}</div>}
                    </td>
                    <td className="hide-sm mono">{row.code}</td>
                    <td>{row.offered_to_students ? 'Yes' : 'No'}</td>
                    <td>{row.device_count}</td>
                    <td>
                      <StatusPill status={row.is_active ? 'ACTIVE' : 'RETIRED'}>
                        {row.is_active ? 'IN USE' : 'RETIRED'}
                      </StatusPill>
                    </td>
                    <td className="row-actions">
                      <button
                        type="button"
                        className="btn btn-ghost btn-sm"
                        onClick={() => setEditing(row)}
                        aria-label={`Edit ${row.label}`}
                      >
                        <Pencil size={14} aria-hidden="true" />
                        <span className="hide-sm">Edit</span>
                      </button>
                      {row.is_active && (
                        <button
                          type="button"
                          className="btn btn-ghost btn-sm"
                          onClick={() => retire(row)}
                          aria-label={`Retire ${row.label}`}
                        >
                          Retire
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </DataState>
      </div>

      {editing && (
        <TypeForm
          row={editing}
          onClose={() => setEditing(null)}
          onDone={(message) => {
            setEditing(null)
            toast.success(message)
            load()
          }}
        />
      )}
    </>
  )
}

function TypeForm({ row, onClose, onDone }) {
  const isNew = !row.id
  const inUse = (row.device_count || 0) > 0
  const [form, setForm] = useState({
    code: row.code || '',
    label: row.label || '',
    description: row.description || '',
    offered_to_students: row.offered_to_students ?? true,
    is_active: row.is_active ?? true,
    sort_order: row.sort_order ?? 100,
  })
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(false)

  const set = (key) => (event) => setForm({ ...form, [key]: event.target.value })

  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    setErrors({})
    try {
      if (isNew) await campus.createEquipmentType(form)
      else await campus.updateEquipmentType(row.id, form)
      onDone(isNew ? `${form.label} added.` : `${form.label} updated.`)
    } catch (error) {
      setErrors(error.fieldErrors || { detail: error.readable })
      setBusy(false)
    }
  }

  return (
    <Modal title={isNew ? 'Add an equipment type' : `Edit ${row.label}`} onClose={onClose}>
      <form onSubmit={submit}>
        {errors.detail && <div className="note note-error">{errors.detail}</div>}

        <Field
          label="Name"
          required
          error={errors.label}
          hint="What a student and a guard see. Safe to reword at any time."
        >
          <input value={form.label} onChange={set('label')} required autoFocus placeholder="Laptop" />
        </Field>

        <Field
          label="Code"
          required
          error={errors.code}
          hint={
            inUse
              ? `Fixed: ${row.device_count} computers are already registered under this code, and it appears in exports already taken.`
              : 'Stored on each record and used in exports. Letters, digits and underscores.'
          }
        >
          <input
            value={form.code}
            onChange={set('code')}
            required
            readOnly={inUse}
            placeholder="LAPTOP"
            className="mono"
          />
        </Field>

        <Field label="Description" error={errors.description}>
          <input value={form.description} onChange={set('description')} />
        </Field>

        <Field
          label="Position in the list"
          error={errors.sort_order}
          hint="Lower numbers come first. The types students choose most should be near the top."
        >
          <input type="number" value={form.sort_order} onChange={set('sort_order')} min={0} />
        </Field>

        <label className="check-inline">
          <input
            type="checkbox"
            checked={form.offered_to_students}
            onChange={(e) => setForm({ ...form, offered_to_students: e.target.checked })}
          />
          Offer this on the public student form
        </label>

        <label className="check-inline" style={{ marginBottom: 8 }}>
          <input
            type="checkbox"
            checked={form.is_active}
            onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
          />
          In use
        </label>

        <div className="form-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={busy}>
            {busy ? 'Saving…' : isNew ? 'Add type' : 'Save changes'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
