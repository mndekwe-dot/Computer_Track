import { useCallback, useEffect, useState } from 'react'
import { Pencil, Plus } from 'lucide-react'
import { Link } from 'react-router-dom'
import { campus, students } from '../api/endpoints'
import { useAuth } from '../auth/AuthContext'
import { usePortal } from '../auth/PortalContext'
import { DataState } from '../components/DataState'
import { PageHeader } from '../components/PortalShell'
import { Field, Modal, Pagination, StatusPill, Toast } from '../components/ui'
import { useDebouncedValue } from '../hooks/useLiveSearch'

const STATUSES = ['ACTIVE', 'SUSPENDED', 'GRADUATED', 'WITHDRAWN']
const STUDENT_COLUMNS = ['Reg number', 'Name', 'Department', 'Year', 'Computers', 'Status', ' ']

export default function Students() {
  const { canManageRecords } = useAuth()
  const portal = usePortal()
  const [data, setData] = useState(null)
  const [departments, setDepartments] = useState([])
  const [filters, setFilters] = useState({ search: '', status: '', department: '' })
  const clearFilters = () => {
    setFilters({ search: '', status: '', department: '' })
    setPage(1)
  }
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [editing, setEditing] = useState(null)
  const [toast, setToast] = useState(null)

  // Search is debounced so typing a reg number is one request, not nine.
  const search = useDebouncedValue(filters.search)

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    students
      .list({ ...filters, search, page })
      .then(setData)
      .catch(setError)
      .finally(() => setLoading(false))
    // `filters.search` is intentionally excluded: the debounced `search`
    // drives the request instead.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.status, filters.department, search, page])

  useEffect(load, [load])
  useEffect(() => {
    campus.departments().then(setDepartments).catch(() => {})
  }, [])

  const updateFilter = (key, value) => {
    setPage(1)
    setFilters((current) => ({ ...current, [key]: value }))
  }

  return (
    <>
      <PageHeader title="Students" subtitle="The people your computers belong to">
        {canManageRecords && (
          <button type="button" className="btn btn-primary" onClick={() => setEditing({})}>
            <Plus size={16} aria-hidden="true" />
            Add student
          </button>
        )}
      </PageHeader>

      <div className="content">
        <div className="toolbar">
          <input
            className="grow"
            placeholder="Search by name, reg number, phone…"
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
            value={filters.department}
            onChange={(e) => updateFilter('department', e.target.value)}
          >
            <option value="">All departments</option>
            {departments.map((dept) => (
              <option key={dept.id} value={dept.id}>
                {dept.name}
              </option>
            ))}
          </select>
        </div>

        <DataState
          loading={loading}
          error={error}
          onRetry={load}
          rows={data?.results ?? null}
          columns={STUDENT_COLUMNS}
          emptyTitle="No students match"
          emptyBody="Try a different search or filter."
          emptyAction={
            <button type="button" className="btn btn-outline" onClick={clearFilters}>
              Clear filters
            </button>
          }
        >
          <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Reg number</th>
                    <th>Name</th>
                    <th className="hide-md">Department</th>
                    <th className="hide-sm">Year</th>
                    <th className="hide-sm">Computers</th>
                    <th>Status</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {data?.results.map((student) => (
                    <tr key={student.id}>
                      <td className="mono">{student.reg_number}</td>
                      <td>
                        <strong>{student.full_name}</strong>
                        {student.phone && <div className="muted">{student.phone}</div>}
                      </td>
                      <td className="hide-md">{student.department_name || ' - '}</td>
                      <td className="hide-sm">{student.year_of_study || ' - '}</td>
                      <td className="hide-sm">
                        <Link to={`${portal.base}/devices?owner=${student.id}`}>
                          {student.device_count} registered
                        </Link>
                      </td>
                      <td>
                        <StatusPill status={student.status}>{student.status_display}</StatusPill>
                      </td>
                      <td>
                        {canManageRecords && (
                          <button
                            type="button"
                            className="btn btn-ghost btn-sm"
                            onClick={() => setEditing(student)}
                            aria-label={`Edit ${student.full_name}`}
                          >
                            <Pencil size={14} aria-hidden="true" />
                            <span className="hide-sm">Edit</span>
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

      {editing && (
        <StudentForm
          student={editing}
          departments={departments}
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

function StudentForm({ student, departments, onClose, onSaved }) {
  const isNew = !student.id
  const [form, setForm] = useState({
    reg_number: student.reg_number || '',
    first_name: student.first_name || '',
    last_name: student.last_name || '',
    email: student.email || '',
    phone: student.phone || '',
    national_id: student.national_id || '',
    department: student.department || '',
    programme: student.programme || '',
    year_of_study: student.year_of_study || '',
    status: student.status || 'ACTIVE',
    notes: student.notes || '',
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
      department: form.department || null,
      year_of_study: form.year_of_study || null,
    }
    try {
      if (isNew) await students.create(payload)
      else await students.update(student.id, payload)
      onSaved(isNew ? 'Student added to the register.' : 'Student record updated.')
    } catch (error) {
      setErrors(error.fieldErrors || { detail: error.readable })
      setBusy(false)
    }
  }

  return (
    <Modal title={isNew ? 'Add a student' : `Edit ${student.full_name}`} onClose={onClose} wide>
      <form onSubmit={submit}>
        {errors.detail && <div className="note note-error">{errors.detail}</div>}
        <div className="form-grid">
          <Field label="Registration number" required error={errors.reg_number}>
            <input value={form.reg_number} onChange={set('reg_number')} required autoFocus />
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
          <Field label="First name" required error={errors.first_name}>
            <input value={form.first_name} onChange={set('first_name')} required />
          </Field>
          <Field label="Last name" required error={errors.last_name}>
            <input value={form.last_name} onChange={set('last_name')} required />
          </Field>
          <Field label="Email" error={errors.email}>
            <input type="email" value={form.email} onChange={set('email')} />
          </Field>
          <Field label="Phone" error={errors.phone}>
            <input value={form.phone} onChange={set('phone')} />
          </Field>
          <Field label="National ID" error={errors.national_id}>
            <input value={form.national_id} onChange={set('national_id')} />
          </Field>
          <Field label="Department" error={errors.department}>
            <select value={form.department} onChange={set('department')}>
              <option value="">No department</option>
              {departments.map((dept) => (
                <option key={dept.id} value={dept.id}>
                  {dept.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Programme" error={errors.programme}>
            <input value={form.programme} onChange={set('programme')} />
          </Field>
          <Field label="Year of study" error={errors.year_of_study}>
            <input
              type="number"
              min="1"
              max="8"
              value={form.year_of_study}
              onChange={set('year_of_study')}
            />
          </Field>
        </div>
        <Field label="Notes" error={errors.notes}>
          <textarea value={form.notes} onChange={set('notes')} />
        </Field>
        <div className="form-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={busy}>
            {busy ? 'Saving…' : isNew ? 'Add student' : 'Save changes'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
