import { useCallback, useEffect, useState } from 'react'
import { CircleCheck } from 'lucide-react'
import { Link } from 'react-router-dom'
import { devices } from '../api/endpoints'
import { useAuth } from '../auth/AuthContext'
import { usePortal } from '../auth/PortalContext'
import { DataState } from '../components/DataState'
import { PageHeader } from '../components/PortalShell'
import { Field, Modal, Pagination, StatusPill, Toast, formatDateTime } from '../components/ui'

const FLAG_COLUMNS = ['Raised', 'Computer', 'Owner', 'Reason', 'Details', 'State', ' ']

export default function Flags() {
  const { canManageRecords } = useAuth()
  const portal = usePortal()
  const [data, setData] = useState(null)
  const [showResolved, setShowResolved] = useState(false)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [resolving, setResolving] = useState(null)
  const [toast, setToast] = useState(null)

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    devices
      .flags({ is_active: showResolved ? '' : 'true', page })
      .then(setData)
      .catch(setError)
      .finally(() => setLoading(false))
  }, [showResolved, page])

  useEffect(load, [load])

  return (
    <>
      <PageHeader
        title="Holds & Theft Reports"
        subtitle="An active hold blocks the computer at every gate on campus"
      />

      <div className="content">
        <div className="toolbar">
          <label className="check-inline">
            <input
              type="checkbox"
              checked={showResolved}
              onChange={(e) => {
                setPage(1)
                setShowResolved(e.target.checked)
              }}
            />
            Include resolved holds
          </label>
        </div>

        <DataState
          loading={loading}
          error={error}
          onRetry={load}
          rows={data?.results ?? null}
          columns={FLAG_COLUMNS}
          skeletonRows={5}
          emptyTitle="No holds in place"
          emptyBody="Nothing is currently blocked. Report a theft from a computer's page."
        >
          <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Raised</th>
                    <th>Computer</th>
                    <th className="hide-sm">Owner</th>
                    <th>Reason</th>
                    <th className="hide-md">Details</th>
                    <th>State</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {data?.results.map((flag) => (
                    <tr key={flag.id}>
                      <td>
                        {formatDateTime(flag.created_at)}
                        {flag.raised_by_name && (
                          <div className="muted">by {flag.raised_by_name}</div>
                        )}
                      </td>
                      <td className="mono">
                        <Link to={`${portal.base}/devices/${flag.device}`}>
                          {flag.device_serial}
                        </Link>
                      </td>
                      <td className="hide-sm">
                        {flag.owner_name}
                        <div className="muted mono">{flag.owner_reg_number}</div>
                      </td>
                      <td>{flag.reason_display}</td>
                      <td className="hide-md muted">{flag.details || ' - '}</td>
                      <td>
                        {flag.is_active ? (
                          <StatusPill status="HOLD">ACTIVE</StatusPill>
                        ) : (
                          <StatusPill status="ACTIVE">RESOLVED</StatusPill>
                        )}
                      </td>
                      <td>
                        {flag.is_active && canManageRecords && (
                          <button
                            type="button"
                            className="btn btn-outline btn-sm"
                            onClick={() => setResolving(flag)}
                          >
                            <CircleCheck size={14} aria-hidden="true" />
                            <span className="hide-sm">Resolve</span>
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

      {resolving && (
        <ResolveDialog
          flag={resolving}
          onClose={() => setResolving(null)}
          onDone={(message) => {
            setResolving(null)
            setToast({ tone: 'success', message })
            load()
          }}
        />
      )}

      <Toast toast={toast} onDismiss={() => setToast(null)} />
    </>
  )
}

function ResolveDialog({ flag, onClose, onDone }) {
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    try {
      await devices.resolveFlag(flag.id, note)
      onDone(`Hold lifted on ${flag.device_serial}.`)
    } catch (err) {
      setError(err.readable)
      setBusy(false)
    }
  }

  return (
    <Modal title={`Resolve the hold on ${flag.device_serial}`} onClose={onClose}>
      <form onSubmit={submit}>
        <div className="note note-info">
          Once resolved, this computer passes the gates again. Theft and loss reports also return
          the computer to active status.
        </div>
        {error && <div className="note note-error">{error}</div>}
        <Field label="How was it resolved?" hint="Kept on the record for audit.">
          <textarea value={note} onChange={(e) => setNote(e.target.value)} autoFocus />
        </Field>
        <div className="form-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={busy}>
            {busy ? 'Resolving…' : 'Lift the hold'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
