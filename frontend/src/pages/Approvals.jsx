import { useCallback, useEffect, useState } from 'react'
import { Check, ExternalLink, X } from 'lucide-react'
import { Link } from 'react-router-dom'
import { devices } from '../api/endpoints'
import { useAuth } from '../auth/AuthContext'
import { usePortal } from '../auth/PortalContext'
import { DataState } from '../components/DataState'
import { PageHeader } from '../components/PortalShell'
import { Field, Modal, Pagination, Toast, formatDateTime } from '../components/ui'

const COLUMNS = ['Submitted', 'Computer', 'Owner', 'Details', ' ']

export default function Approvals() {
  const { canManageRecords } = useAuth()
  const portal = usePortal()
  const [data, setData] = useState(null)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [dialog, setDialog] = useState(null)
  const [toast, setToast] = useState(null)

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    devices
      .pending({ page })
      .then(setData)
      .catch(setError)
      .finally(() => setLoading(false))
  }, [page])

  useEffect(load, [load])

  const done = (message) => {
    setDialog(null)
    setToast({ tone: 'success', message })
    load()
  }

  return (
    <>
      <PageHeader
        title="Pending Approvals"
        subtitle="Computers students submitted through the public registration form"
      />

      <div className="content">
        <div className="note note-info">
          <span>
            Every submission here is <strong>blocked at the gate</strong> until you approve it.
            Check the serial against the machine in front of you before approving.
          </span>
        </div>

        <DataState
          loading={loading}
          error={error}
          onRetry={load}
          rows={data?.results ?? null}
          columns={COLUMNS}
          skeletonRows={5}
          emptyTitle="Nothing waiting for approval"
          emptyBody="Submissions from the public registration form land here."
        >
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Submitted</th>
                  <th>Computer</th>
                  <th className="hide-sm">Owner</th>
                  <th className="hide-md">Details</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {data?.results.map((device) => (
                  <tr key={device.id}>
                    <td>{formatDateTime(device.registered_at)}</td>
                    <td>
                      <strong>{device.label}</strong>
                      <div className="mono muted">{device.serial_number}</div>
                    </td>
                    <td className="hide-sm">
                      {device.owner_detail?.full_name}
                      <div className="muted mono">{device.owner_detail?.reg_number}</div>
                    </td>
                    <td className="hide-md muted">
                      {device.device_type_display}
                      {device.colour ? ` · ${device.colour}` : ''}
                      {device.distinguishing_marks ? ` · ${device.distinguishing_marks}` : ''}
                    </td>
                    <td>
                      <div className="row-actions">
                        <Link
                          className="btn btn-ghost btn-sm"
                          to={`${portal.base}/devices/${device.id}`}
                        >
                          <ExternalLink size={14} aria-hidden="true" />
                        </Link>
                        {canManageRecords && (
                          <>
                            <button
                              type="button"
                              className="btn btn-pass btn-sm"
                              onClick={() => setDialog({ kind: 'APPROVE', device })}
                            >
                              <Check size={14} aria-hidden="true" />
                              Approve
                            </button>
                            <button
                              type="button"
                              className="btn btn-outline btn-sm"
                              onClick={() => setDialog({ kind: 'REJECT', device })}
                            >
                              <X size={14} aria-hidden="true" />
                              <span className="hide-sm">Reject</span>
                            </button>
                          </>
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

      {dialog?.kind === 'APPROVE' && (
        <ApproveDialog device={dialog.device} onClose={() => setDialog(null)} onDone={done} />
      )}
      {dialog?.kind === 'REJECT' && (
        <RejectDialog device={dialog.device} onClose={() => setDialog(null)} onDone={done} />
      )}

      <Toast toast={toast} onDismiss={() => setToast(null)} />
    </>
  )
}

function ApproveDialog({ device, onClose, onDone }) {
  const [assetTag, setAssetTag] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const outcome = await devices.approve(device.id, assetTag)
      onDone(
        outcome.owner_notified
          ? `${device.serial_number} approved. The owner has been notified.`
          : `${device.serial_number} approved. No contact details on file, so tell them in person.`,
      )
    } catch (err) {
      setError(err.fieldErrors?.asset_tag || err.readable)
      setBusy(false)
    }
  }

  return (
    <Modal title={`Approve ${device.serial_number}`} onClose={onClose}>
      <form onSubmit={submit}>
        <p className="muted" style={{ marginTop: 0 }}>
          {device.label} submitted by {device.owner_detail?.full_name} (
          {device.owner_detail?.reg_number}). Approving puts it on the register and lets it
          through the gates.
        </p>
        <Field
          label="Asset tag"
          error={error}
          hint="The university sticker you are applying now. Leave blank to add it later."
        >
          <input
            value={assetTag}
            onChange={(e) => setAssetTag(e.target.value)}
            placeholder="UNI-02401"
            autoFocus
          />
        </Field>
        <div className="form-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-pass" disabled={busy}>
            {busy ? 'Approving…' : 'Approve'}
          </button>
        </div>
      </form>
    </Modal>
  )
}

function RejectDialog({ device, onClose, onDone }) {
  const [reason, setReason] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (event) => {
    event.preventDefault()
    if (!reason.trim()) return
    setBusy(true)
    setError('')
    try {
      const outcome = await devices.reject(device.id, reason)
      onDone(
        outcome.owner_notified
          ? `${device.serial_number} rejected. The owner has been told why.`
          : `${device.serial_number} rejected. No contact details on file, so tell them in person.`,
      )
    } catch (err) {
      setError(err.fieldErrors?.reason || err.readable)
      setBusy(false)
    }
  }

  return (
    <Modal title={`Reject ${device.serial_number}`} onClose={onClose}>
      <form onSubmit={submit}>
        <div className="note note-warn">
          The submission stays on file with your reason, so the serial cannot simply be
          re-submitted in a loop.
        </div>
        <Field
          label="Why is this being turned down?"
          required
          error={error}
          hint="The student will be told this at the registration office."
        >
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            required
            autoFocus
            placeholder="Serial does not match the sticker on the machine."
          />
        </Field>
        <div className="form-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-hold" disabled={busy}>
            {busy ? 'Rejecting…' : 'Reject'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
