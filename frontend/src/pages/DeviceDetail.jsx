import { useCallback, useEffect, useState } from 'react'
import { ArrowLeft, Ban, Pencil, Printer, TriangleAlert, UserRoundPlus } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { devices } from '../api/endpoints'
import { useAuth } from '../auth/AuthContext'
import { usePortal } from '../auth/PortalContext'
import { PageHeader } from '../components/PortalShell'
import { ErrorNote, Field, Modal, SkeletonBar, SkeletonCard, StatusPill, formatDateTime } from '../components/ui'
import { useToast } from '../components/Toasts'
import { DeviceForm } from './Devices'

export default function DeviceDetail() {
  const { id } = useParams()
  const { canManageRecords } = useAuth()
  const portal = usePortal()
  const [device, setDevice] = useState(null)
  const [history, setHistory] = useState(null)
  const [qrUrl, setQrUrl] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [dialog, setDialog] = useState(null)
  const toast = useToast()

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    Promise.all([devices.get(id), devices.history(id)])
      .then(([deviceData, historyData]) => {
        setDevice(deviceData)
        setHistory(historyData)
      })
      .catch(setError)
      .finally(() => setLoading(false))
  }, [id])

  useEffect(load, [load])

  useEffect(() => {
    // The QR endpoint needs the auth header, so it is fetched as a blob
    // rather than dropped straight into an <img src>.
    let objectUrl = null
    devices
      .qrBlob(id)
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob)
        setQrUrl(objectUrl)
      })
      .catch(() => {})
    return () => objectUrl && URL.revokeObjectURL(objectUrl)
  }, [id])

  if (loading) {
    return (
      <>
        <PageHeader title="Loading the record…" />
        <div className="content">
          <div className="two-col">
            <SkeletonCard lines={8} />
            <SkeletonCard lines={3} />
          </div>
          <SkeletonCard lines={3} />
        </div>
      </>
    )
  }

  if (error) {
    return (
      <>
        <PageHeader title="Computer" />
        <div className="content">
          <ErrorNote error={error} onRetry={load} />
          <Link to={`${portal.base}/devices`} className="btn btn-outline">
            <ArrowLeft size={16} aria-hidden="true" />
            Back to all computers
          </Link>
        </div>
      </>
    )
  }

  if (!device) return null

  const done = (message) => {
    setDialog(null)
    toast.show({ tone: 'success', message })
    load()
  }

  return (
    <>
      <PageHeader title={device.label} subtitle={`Serial ${device.serial_number}`}>
        <Link to={`${portal.base}/devices`} className="btn btn-ghost btn-sm">
          <ArrowLeft size={15} aria-hidden="true" />
          <span className="hide-sm">All computers</span>
        </Link>
        {canManageRecords && (
          <>
            <button
              type="button"
              className="btn btn-outline btn-sm"
              onClick={() => setDialog({ kind: 'EDIT' })}
            >
              <Pencil size={15} aria-hidden="true" />
              Edit
            </button>
            <button
              type="button"
              className="btn btn-outline btn-sm"
              onClick={() => setDialog({ kind: 'TRANSFER' })}
            >
              <UserRoundPlus size={15} aria-hidden="true" />
              <span className="hide-sm">Transfer owner</span>
            </button>
            {device.status !== 'STOLEN' && (
              <button
                type="button"
                className="btn btn-hold btn-sm"
                onClick={() => setDialog({ kind: 'STOLEN' })}
              >
                <Ban size={15} aria-hidden="true" />
                <span className="hide-sm">Report stolen</span>
              </button>
            )}
          </>
        )}
      </PageHeader>

      <div className="content">
        {device.is_blocked && (
          <div className="note note-error">
            <div>
              <strong>
                <TriangleAlert size={16} aria-hidden="true" style={{ verticalAlign: '-3px' }} />{' '}
                This computer is blocked at every gate.
              </strong>
              <ul style={{ margin: '6px 0 0', paddingLeft: 20 }}>
                {device.blocking_reasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            </div>
          </div>
        )}

        <div className="two-col">
          <div className="card">
            <div className="card-header">
              <h3>Details</h3>
              <StatusPill status={device.status}>{device.status_display}</StatusPill>
            </div>
            <dl className="detail-list">
              <Row label="Owner">
                <Link to={`${portal.base}/devices?owner=${device.owner}`}>
                  {device.owner_detail?.full_name}
                </Link>
                <div className="muted mono">{device.owner_detail?.reg_number}</div>
              </Row>
              <Row label="Type">{device.device_type_display}</Row>
              <Row label="Serial">
                <span className="mono">{device.serial_number}</span>
              </Row>
              <Row label="Asset tag">
                <span className="mono">{device.asset_tag || ' - '}</span>
              </Row>
              <Row label="Colour">{device.colour || ' - '}</Row>
              <Row label="Marks">{device.distinguishing_marks || ' - '}</Row>
              <Row label="Registered">
                {formatDateTime(device.registered_at)}
                {device.registered_by_name ? ` by ${device.registered_by_name}` : ''}
              </Row>
              <Row label="Last movement">
                {device.last_movement
                  ? `${device.last_movement.direction === 'IN' ? 'Entered' : 'Left'} via ${
                      device.last_movement.gate || 'unknown gate'
                    } - ${formatDateTime(device.last_movement.created_at)}`
                  : 'Never seen at a gate'}
              </Row>
              <Row label="Notes">{device.notes || ' - '}</Row>
            </dl>
          </div>

          <div className="card">
            <div className="card-header">
              <h3>QR sticker</h3>
              <button
                type="button"
                className="btn btn-outline btn-sm no-print"
                onClick={() => window.print()}
              >
                <Printer size={15} aria-hidden="true" />
                Print
              </button>
            </div>
            <div className="qr-sticker">
              {qrUrl ? (
                <img src={qrUrl} alt={`QR code for ${device.serial_number}`} />
              ) : (
                <div style={{ display: 'grid', placeItems: 'center' }}>
                  <SkeletonBar width={140} height={140} />
                </div>
              )}
              <span className="mono">{device.serial_number}</span>
              <span className="muted" style={{ fontSize: 12 }}>
                {device.owner_detail?.reg_number} · {device.brand}
              </span>
            </div>
            <p className="muted" style={{ fontSize: 12.5 }}>
              Stick this on the chassis. Scanning it at the gate pulls up this record instantly.
            </p>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h3>Holds and theft reports</h3>
          </div>
          {history?.flags?.length ? (
            <HistoryTable
              rows={history.flags}
              columns={['Raised', 'Reason', 'Details', 'State']}
              render={(flag) => [
                formatDateTime(flag.created_at),
                flag.reason_display,
                flag.details || ' - ',
                flag.is_active ? (
                  <StatusPill status="HOLD">ACTIVE</StatusPill>
                ) : (
                  <StatusPill status="ACTIVE">RESOLVED</StatusPill>
                ),
              ]}
            />
          ) : (
            <p className="muted" style={{ margin: 0 }}>
              No holds have ever been raised.
            </p>
          )}
        </div>

        <div className="card">
          <div className="card-header">
            <h3>Ownership history</h3>
          </div>
          {history?.transfers?.length ? (
            <HistoryTable
              rows={history.transfers}
              columns={['When', 'From', 'To', 'Reason', 'By']}
              render={(transfer) => [
                formatDateTime(transfer.created_at),
                transfer.from_student_detail?.reg_number || ' - ',
                transfer.to_student_detail?.reg_number || ' - ',
                transfer.reason || ' - ',
                transfer.transferred_by_name || ' - ',
              ]}
            />
          ) : (
            <p className="muted" style={{ margin: 0 }}>
              Still with the student it was first registered to.
            </p>
          )}
        </div>

        <div className="card">
          <div className="card-header">
            <h3>Permits issued</h3>
          </div>
          {history?.permits?.length ? (
            <HistoryTable
              rows={history.permits}
              columns={['Bearer', 'From', 'Until', 'State']}
              render={(permit) => [
                permit.bearer_name,
                formatDateTime(permit.valid_from),
                formatDateTime(permit.valid_to),
                permit.is_revoked ? (
                  <StatusPill status="DENIED">REVOKED</StatusPill>
                ) : permit.is_valid_now ? (
                  <StatusPill status="ACTIVE">LIVE</StatusPill>
                ) : (
                  <StatusPill status="RETIRED">EXPIRED</StatusPill>
                ),
              ]}
            />
          ) : (
            <p className="muted" style={{ margin: 0 }}>
              Nobody else has been permitted to carry it.
            </p>
          )}
        </div>
      </div>

      {dialog?.kind === 'EDIT' && (
        <DeviceForm
          device={device}
          onClose={() => setDialog(null)}
          onSaved={() => done('Computer record updated.')}
        />
      )}
      {dialog?.kind === 'TRANSFER' && (
        <TransferDialog device={device} onClose={() => setDialog(null)} onDone={done} />
      )}
      {dialog?.kind === 'STOLEN' && (
        <StolenDialog device={device} onClose={() => setDialog(null)} onDone={done} />
      )}

    </>
  )
}

function Row({ label, children }) {
  return (
    <>
      <dt className="muted">{label}</dt>
      <dd>{children}</dd>
    </>
  )
}

function HistoryTable({ rows, columns, render }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id}>
              {render(row).map((cell, index) => (
                // eslint-disable-next-line react/no-array-index-key
                <td key={index}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function TransferDialog({ device, onClose, onDone }) {
  const [regNumber, setRegNumber] = useState('')
  const [reason, setReason] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      await devices.transfer(device.id, { to_student_reg_number: regNumber, reason })
      onDone(`Ownership moved to ${regNumber}.`)
    } catch (err) {
      setError(err.fieldErrors?.to_student_reg_number || err.readable)
      setBusy(false)
    }
  }

  return (
    <Modal title="Transfer ownership" onClose={onClose}>
      <form onSubmit={submit}>
        <p className="muted" style={{ marginTop: 0 }}>
          Currently registered to {device.owner_detail?.full_name} (
          {device.owner_detail?.reg_number}). The old owner stays in the history.
        </p>
        <Field label="New owner's registration number" required error={error}>
          <input
            value={regNumber}
            onChange={(e) => setRegNumber(e.target.value)}
            required
            autoFocus
          />
        </Field>
        <Field label="Reason">
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Sold to a classmate, replaced under warranty…"
          />
        </Field>
        <div className="form-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={busy}>
            {busy ? 'Transferring…' : 'Transfer'}
          </button>
        </div>
      </form>
    </Modal>
  )
}

function StolenDialog({ device, onClose, onDone }) {
  const [details, setDetails] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    try {
      await devices.reportStolen(device.id, details)
      onDone('Reported stolen. Every gate will now block this computer.')
    } catch (err) {
      setError(err.readable)
      setBusy(false)
    }
  }

  return (
    <Modal title="Report this computer stolen" onClose={onClose}>
      <form onSubmit={submit}>
        <div className="note note-warn">
          Every gate will immediately refuse this computer, and the guard will be told to hold it
          and call security control.
        </div>
        {error && <div className="note note-error">{error}</div>}
        <Field label="What happened?" hint="When and where it was taken, and who reported it.">
          <textarea value={details} onChange={(e) => setDetails(e.target.value)} autoFocus />
        </Field>
        <div className="form-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-hold" disabled={busy}>
            {busy ? 'Reporting…' : 'Report stolen'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
