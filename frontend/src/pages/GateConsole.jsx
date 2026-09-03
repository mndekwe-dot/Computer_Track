import { useCallback, useEffect, useRef, useState } from 'react'
import {
  ArrowDownToLine,
  ArrowUpFromLine,
  Ban,
  Building2,
  Check,
  CircleCheck,
  CloudOff,
  CircleHelp,
  GraduationCap,
  LaptopMinimal,
  OctagonAlert,
  QrCode,
  RefreshCw,
  Search,
  Ticket,
  TriangleAlert,
  Wifi,
  WifiOff,
  X,
} from 'lucide-react'
import { mediaUrl } from '../api/client'
import { auth, campus, checkpoint } from '../api/endpoints'
import { useAuth } from '../auth/AuthContext'
import { PageHeader } from '../components/PortalShell'
import { QrScanner } from '../components/QrScanner'
import { EmptyState, ErrorNote, Field, Modal, SkeletonCard, SkeletonStudentCard, StatusPill, formatTime } from '../components/ui'
import { useToast } from '../components/Toasts'
import { useLiveSearch } from '../hooks/useLiveSearch'
import { useOfflineQueue } from '../hooks/useOfflineQueue'
import { recall, remember } from '../hooks/useLookupCache'

export default function GateConsole() {
  const { user, patchUser } = useAuth()
  const { submitScan, flush, queued, online, syncing } = useOfflineQueue()

  const [gates, setGates] = useState([])
  const [gatesError, setGatesError] = useState(null)
  const [gateId, setGateId] = useState(user?.default_gate || '')
  const [direction, setDirection] = useState('OUT')

  const [query, setQuery] = useState('')
  const [result, setResult] = useState(null)
  const [searching, setSearching] = useState(false)
  const [error, setError] = useState(null)

  const [recent, setRecent] = useState([])
  const toast = useToast()
  const [scanning, setScanning] = useState(false)
  const [dialog, setDialog] = useState(null)

  // Live typeahead while the guard types, kept separate from the committed
  // lookup that Enter performs.
  const { results: live, searching: liveSearching, reset: resetLive } = useLiveSearch(query)
  const [highlight, setHighlight] = useState(-1)
  const [suggestOpen, setSuggestOpen] = useState(false)

  const inputRef = useRef(null)

  const loadGates = useCallback(() => {
    setGatesError(null)
    campus.gates().then(setGates).catch(setGatesError)
  }, [])

  useEffect(() => {
    loadGates()
    // The recent list is a convenience; failing to load it must not get in the
    // way of the queue, so this one stays quiet.
    checkpoint
      .scans({ guard: user?.id, page_size: 8 })
      .then((data) => setRecent(data.results || []))
      .catch(() => {})
  }, [user?.id, loadGates])

  const focusSearch = useCallback(() => {
    // Throughput at a busy gate depends on the caret already being in the box.
    requestAnimationFrame(() => inputRef.current?.focus())
  }, [])

  // University property is held on the way out and clear on the way in, so a
  // result fetched under one direction is wrong under the other. Showing a
  // stale PASS after the guard flips the toggle is the dangerous half of that,
  // so the lookup is re-run rather than left alone.
  const lookedUpQuery = useRef(null)

  const runLookup = useCallback(
    async (raw) => {
      const value = (raw ?? '').trim()
      if (!value) return
      setSuggestOpen(false)
      setHighlight(-1)
      setSearching(true)
      setError(null)
      try {
        const payload = await checkpoint.lookup(value, direction)
        setResult(payload)
        // Kept so the same person coming back through the gate can still be
        // checked if the network has gone. Only what has been looked up, and
        // only for a few minutes - see hooks/useLookupCache.js for why this
        // is deliberately not a copy of the register.
        remember(value, direction, payload)
        lookedUpQuery.current = value
      } catch (err) {
        // A network failure is the one case worth falling back for. A 404 or
        // a 403 is an answer, and showing a stale one instead would be worse
        // than showing the error.
        const cached = err.isNetwork ? recall(value, direction) : null
        if (cached) {
          setResult(cached)
          setError(null)
          lookedUpQuery.current = value
        } else {
          setError(err)
          setResult(null)
        }
      } finally {
        setSearching(false)
      }
    },
    // The verdict for university property depends on which way it is going,
    // so a lookup made under "Leaving" must not be reused under "Entering".
    [direction],
  )

  // Re-run whatever is on screen when the direction changes, so the verdict
  // always matches the toggle the guard is looking at.
  useEffect(() => {
    if (lookedUpQuery.current) runLookup(lookedUpQuery.current)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [direction])

  // One flat list so the arrow keys can walk students and computers together.
  const suggestions = [
    ...live.students.map((s) => ({
      key: `s${s.id}`,
      kind: 'student',
      primary: s.reg_number,
      secondary: s.full_name,
      meta: s.device_count === 1 ? '1 computer' : `${s.device_count} computers`,
      value: s.reg_number,
      status: s.status,
    })),
    ...live.devices.map((d) => ({
      key: `d${d.id}`,
      kind: 'device',
      primary: d.serial_number,
      secondary: d.label,
      meta: d.owner_reg_number,
      value: d.serial_number,
      status: d.status,
    })),
  ]

  const onKeyDown = (event) => {
    if (!suggestOpen || suggestions.length === 0) return
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setHighlight((index) => (index + 1) % suggestions.length)
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      setHighlight((index) => (index <= 0 ? suggestions.length - 1 : index - 1))
    } else if (event.key === 'Escape') {
      setSuggestOpen(false)
      setHighlight(-1)
    }
  }

  const onSubmit = (event) => {
    event.preventDefault()
    // Enter takes the highlighted suggestion if the guard arrowed to one,
    // otherwise whatever they typed.
    const chosen = highlight >= 0 ? suggestions[highlight] : null
    const value = chosen ? chosen.value : query
    if (chosen) setQuery(chosen.value)
    runLookup(value)
  }

  const clearAll = () => {
    setQuery('')
    setResult(null)
    setError(null)
    setSuggestOpen(false)
    setHighlight(-1)
    resetLive()
    focusSearch()
  }

  const record = async ({ device, verdict, overrideReason = '', notes = '', permit = null }) => {
    if (!gateId) {
      toast.show({ tone: 'error', message: 'Choose which gate you are working at first.' })
      return
    }
    try {
      const payload = {
        device: device?.id ?? null,
        gate: Number(gateId),
        direction,
        verdict,
        method: result?.method || 'MANUAL',
        override_reason: overrideReason,
        notes,
        permit,
        claimed_serial: device?.serial_number || result?.query || '',
        claimed_reg_number: result?.student?.reg_number || '',
      }
      const { saved, queued: wasQueued } = await submitScan(payload)

      const label = device ? `${device.brand} ${device.serial_number}` : 'Unregistered device'
      setRecent((prev) =>
        [
          {
            id: saved.id || `local-${saved.client_reference}`,
            device_label: label,
            student_name: result?.student?.full_name || '',
            verdict,
            direction,
            happened_at: saved.client_timestamp || new Date().toISOString(),
            pending: wasQueued,
          },
          ...prev,
        ].slice(0, 12),
      )

      toast.show({
        tone: verdict === 'ALLOWED' ? 'success' : 'warn',
        message: wasQueued
          ? `Saved on this device - ${label} will sync when the network returns.`
          : `${verdictWord(verdict, direction)} · ${label}`,
      })
      setDialog(null)
      clearAll()
    } catch (err) {
      toast.show({ tone: 'error', message: err.readable || 'Could not record that decision.' })
    }
  }

  const changeGate = async (value) => {
    setGateId(value)
    const gate = value ? Number(value) : null
    try {
      await auth.updateMe({ default_gate: gate })
      patchUser({ default_gate: gate })
    } catch {
      /* Not worth interrupting the queue over. */
    }
  }

  return (
    <>
      <PageHeader
        title="Gate Console"
        subtitle="Ask for the registration number, then match the computer in front of you."
      >
        <span className="connection-badge" data-online={online}>
          {online ? <Wifi size={14} aria-hidden="true" /> : <WifiOff size={14} aria-hidden="true" />}
          <span>{online ? 'Online' : 'Offline'}</span>
          <span className="hide-sm">{online ? '' : ' - saving locally'}</span>
        </span>
        {queued > 0 && (
          <button
            type="button"
            className="btn btn-outline btn-sm"
            onClick={() => flush().catch(() => {})}
            disabled={syncing || !online}
          >
            <RefreshCw size={14} aria-hidden="true" />
            {syncing ? 'Syncing…' : `Sync ${queued}`}
          </button>
        )}
      </PageHeader>

      <div className="content">
        {gatesError && (
          <div className="note note-error" role="alert">
            <span>
              The gate list could not be loaded, so decisions cannot be attributed yet.{' '}
              {gatesError.readable}
            </span>
            <button type="button" className="btn btn-ghost btn-sm" onClick={loadGates}>
              Try again
            </button>
          </div>
        )}

        <div className="console-controls">
          <div className="control-group">
            <div className="field-label">Gate</div>
            <select value={gateId} onChange={(e) => changeGate(e.target.value)}>
              <option value="">Select a gate…</option>
              {gates.map((gate) => (
                <option key={gate.id} value={gate.id}>
                  {gate.name}
                </option>
              ))}
            </select>
          </div>

          <div className="control-group">
            <div className="field-label">Direction</div>
            <div className="direction-toggle" role="group" aria-label="Direction of travel">
              <button
                type="button"
                aria-pressed={direction === 'IN'}
                onClick={() => setDirection('IN')}
              >
                <ArrowDownToLine size={16} aria-hidden="true" />
                Entering
              </button>
              <button
                type="button"
                aria-pressed={direction === 'OUT'}
                onClick={() => setDirection('OUT')}
              >
                <ArrowUpFromLine size={16} aria-hidden="true" />
                Leaving
              </button>
            </div>
          </div>
        </div>

        <form onSubmit={onSubmit} className="search-row">
          <div className="search-field">
            <input
              ref={inputRef}
              className="search-input"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value)
                setSuggestOpen(true)
                setHighlight(-1)
              }}
              onKeyDown={onKeyDown}
              onFocus={() => setSuggestOpen(true)}
              // A blur that lands on a suggestion must not close the list
              // before the click registers.
              onBlur={() => setTimeout(() => setSuggestOpen(false), 120)}
              placeholder="Registration number, serial, or asset tag…"
              autoFocus
              autoComplete="off"
              spellCheck="false"
              role="combobox"
              aria-expanded={suggestOpen && suggestions.length > 0}
              aria-controls="gate-suggestions"
              aria-autocomplete="list"
              aria-label="Search by registration number, serial or asset tag"
            />

            {suggestOpen && (suggestions.length > 0 || liveSearching) && (
              <ul className="suggest-list" id="gate-suggestions" role="listbox">
                {suggestions.length === 0 && liveSearching && (
                  <li className="suggest-empty">Searching…</li>
                )}
                {suggestions.map((item, index) => (
                  <li key={item.key}>
                    <button
                      type="button"
                      role="option"
                      aria-selected={index === highlight}
                      className="suggest-item"
                      data-active={index === highlight}
                      onMouseEnter={() => setHighlight(index)}
                      onMouseDown={(e) => e.preventDefault()}
                      onClick={() => {
                        setQuery(item.value)
                        runLookup(item.value)
                      }}
                    >
                      <span className="suggest-icon" aria-hidden="true">
                        {item.kind === 'student' ? (
                          <GraduationCap size={15} />
                        ) : (
                          <LaptopMinimal size={15} />
                        )}
                      </span>
                      <span className="suggest-text">
                        <strong className="mono">{item.primary}</strong>
                        <span className="muted">{item.secondary}</span>
                      </span>
                      <span className="suggest-meta muted">{item.meta}</span>
                    </button>
                  </li>
                ))}
                {live.truncated && (
                  <li className="suggest-empty">Keep typing to narrow this down…</li>
                )}
              </ul>
            )}
          </div>

          <div className="search-actions">
            <button type="submit" className="btn btn-primary btn-lg" disabled={searching}>
              <Search size={18} aria-hidden="true" />
              {searching ? 'Checking…' : 'Check'}
            </button>
            <button
              type="button"
              className="btn btn-outline btn-lg"
              onClick={() => setScanning(true)}
              aria-label="Scan a QR sticker"
            >
              <QrCode size={18} aria-hidden="true" />
            </button>
            {(result || error) && (
              <button
                type="button"
                className="btn btn-ghost btn-lg"
                onClick={clearAll}
                aria-label="Clear"
              >
                <X size={18} aria-hidden="true" />
              </button>
            )}
          </div>
        </form>

        <div className="console">
          <div>
            <ErrorNote error={error} onRetry={() => runLookup(query)} />
            {searching && (
              <>
                <SkeletonStudentCard />
                <SkeletonCard lines={3} />
              </>
            )}

            {!searching && !result && !error && (
              <EmptyState title="Ready">
                Ask the student for their registration number and type it above. You can also
                scan the QR sticker or type the serial printed on the computer.
              </EmptyState>
            )}

            {result && result.resolved_as === 'NOT_FOUND' && (
              <NotFoundPanel
                result={result}
                onPick={(value) => {
                  setQuery(value)
                  runLookup(value)
                }}
                onLogUnregistered={() => setDialog({ kind: 'UNREGISTERED', device: null })}
              />
            )}

            {result?.from_cache && (
              /*
                A guard has to know they are looking at a copy. A computer
                reported stolen in the last few minutes would still read as
                clear here, and that is the one situation where the console
                being confidently wrong matters most.
              */
              <div className="note note-warn" role="status">
                <CloudOff size={16} aria-hidden="true" />
                <span>
                  Offline. This is what the register said at{' '}
                  <strong>{formatTime(result.cached_at)}</strong>, not what it says now. A hold
                  placed since then will not show. Check again once the network returns.
                </span>
              </div>
            )}

            {result && result.resolved_as !== 'NOT_FOUND' && (
              <>
                {result.student && (
                  <StudentCard student={result.student} warnings={result.warnings} />
                )}
                {result.devices.length === 0 && (
                  <EmptyState title="No computer registered to this student">
                    Nothing may be taken out under this name until it is registered at the
                    registration office.
                  </EmptyState>
                )}
                {result.devices.map((device) => (
                  <DeviceDecisionCard
                    key={device.id}
                    device={device}
                    direction={direction}
                    highlighted={device.id === result.matched_device_id}
                    onAllow={() => record({ device, verdict: 'ALLOWED' })}
                    onDeny={() => setDialog({ kind: 'DENY', device })}
                    onOverride={() => setDialog({ kind: 'OVERRIDE', device })}
                  />
                ))}
              </>
            )}
          </div>

          <aside className="side-panel">
            <div className="card">
              <div className="card-header">
                <h3>Recent decisions</h3>
              </div>
              {recent.length === 0 ? (
                <p className="muted" style={{ fontSize: 13, margin: 0 }}>
                  Nothing recorded yet on this shift.
                </p>
              ) : (
                <div className="recent-list">
                  {recent.map((scan) => (
                    <div className="recent-item" key={scan.id}>
                      {/* Flat children on purpose: the card is a grid, so the
                          verdict can hold the top-right corner while the name
                          and the time each get the card's full width instead
                          of wrapping around the pill. */}
                      <strong>{scan.device_label || scan.claimed_serial || ' - '}</strong>
                      <StatusPill status={scan.verdict} />
                      <span className="muted">
                        {scan.student_name || 'Unknown'} · {formatTime(scan.happened_at)}
                        {scan.pending && ' · not yet synced'}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </aside>
        </div>
      </div>

      {scanning && (
        <QrScanner
          onClose={() => setScanning(false)}
          onDetected={(value) => {
            setScanning(false)
            setQuery(value)
            runLookup(value)
          }}
        />
      )}

      {dialog && (
        <DecisionDialog
          dialog={dialog}
          direction={direction}
          onClose={() => setDialog(null)}
          onConfirm={record}
        />
      )}

    </>
  )
}

function verdictWord(verdict, direction) {
  const move = direction === 'IN' ? 'entry' : 'exit'
  if (verdict === 'ALLOWED') return `Allowed ${move}`
  if (verdict === 'DENIED') return `Denied ${move}`
  if (verdict === 'OVERRIDE') return `Override recorded for ${move}`
  return 'Unregistered device logged'
}

function StudentCard({ student, warnings }) {
  const photo = mediaUrl(student.photo)
  const initials = (student.full_name || '?')
    .split(' ')
    .map((part) => part[0])
    .slice(0, 2)
    .join('')

  return (
    <div className="card">
      <div className="student-card">
        {photo ? (
          <img className="student-photo" src={photo} alt={student.full_name} />
        ) : (
          <div className="student-photo-placeholder" aria-hidden="true">
            {initials}
          </div>
        )}
        <div className="student-meta">
          <h2>{student.full_name}</h2>
          <div className="mono student-reg">{student.reg_number}</div>
          <div className="meta-list">
            <span>
              <StatusPill status={student.status}>{student.status_display}</StatusPill>
            </span>
            {student.programme && <span>{student.programme}</span>}
            {student.year_of_study && <span>Year {student.year_of_study}</span>}
            {student.phone && <span>{student.phone}</span>}
          </div>
        </div>
      </div>

      {warnings?.map((warning) => (
        <div className="note note-warn" key={warning} style={{ marginTop: 14, marginBottom: 0 }}>
          <span>
            <TriangleAlert size={16} aria-hidden="true" style={{ verticalAlign: '-3px' }} />{' '}
            {warning}
          </span>
        </div>
      ))}
    </div>
  )
}

function DeviceDecisionCard({ device, direction, highlighted, onAllow, onDeny, onOverride }) {
  const { action, reasons } = device.recommendation
  const hold = action === 'HOLD'

  return (
    <div className="device-card" data-action={action}>
      <div className="device-card-head">
        {device.photo && (
          <a
            className="device-photo"
            href={mediaUrl(device.photo)}
            target="_blank"
            rel="noreferrer"
            title="Open the registered photo full size"
          >
            <img src={mediaUrl(device.photo)} alt={`Registered photo of ${device.label}`} />
          </a>
        )}
        <div style={{ minWidth: 0, flex: 1 }}>
          <div className="device-title">
            {device.brand} {device.model_name}
            {highlighted && (
              <span className="pill pill-IN" style={{ marginLeft: 8 }}>
                Scanned
              </span>
            )}
          </div>
          <div className="mono device-serial">
            {device.serial_number}
            {device.asset_tag ? ` · ${device.asset_tag}` : ''}
          </div>
          <div className="device-specs">
            <span>{device.device_type_display}</span>
            {device.colour && <span>{device.colour}</span>}
            {device.distinguishing_marks && <span>&ldquo;{device.distinguishing_marks}&rdquo;</span>}
          </div>
          {/* University property has no student card above it, so the guard
              would otherwise be told to hold something with no indication of
              whose it is or who to call about it. */}
          {device.ownership === 'UNIVERSITY' && (
            <div className="device-custody">
              <Building2 size={14} aria-hidden="true" />
              <span>
                University property
                {device.department_name ? ` · ${device.department_name}` : ''}
                {device.custodian_name ? ` · ${device.custodian_name}` : ''}
              </span>
            </div>
          )}
        </div>
        <StatusPill status={device.status}>{device.status_display}</StatusPill>
      </div>

      <div className="verdict-banner" data-action={action}>
        <span className="verdict-headline">
          {hold ? (
            <OctagonAlert size={18} aria-hidden="true" />
          ) : (
            <CircleCheck size={18} aria-hidden="true" />
          )}
          {hold ? 'HOLD - do not let this through' : 'CLEAR - details match the register'}
        </span>
        {hold && (
          <ul>
            {reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        )}
      </div>

      {device.valid_permits?.map((permit) => (
        <div className="permit-note" key={permit.id}>
          <Ticket size={16} aria-hidden="true" style={{ verticalAlign: '-3px' }} />{' '}
          <strong>{permit.bearer_name}</strong> is permitted to carry this computer
          {permit.bearer_id_number ? ` (ID ${permit.bearer_id_number})` : ''} until{' '}
          {new Date(permit.valid_to).toLocaleString()}. Check their ID against this name.
        </div>
      ))}

      <div className="decision-row">
        {hold ? (
          <>
            <button type="button" className="btn btn-hold btn-lg" onClick={onDeny}>
              <Ban size={18} aria-hidden="true" />
              Deny and hold
            </button>
            <button type="button" className="btn btn-warn btn-lg" onClick={onOverride}>
              <TriangleAlert size={18} aria-hidden="true" />
              Override with reason…
            </button>
          </>
        ) : (
          <>
            <button type="button" className="btn btn-pass btn-lg" onClick={onAllow}>
              <Check size={18} aria-hidden="true" />
              Allow {direction === 'IN' ? 'entry' : 'exit'}
            </button>
            <button type="button" className="btn btn-outline btn-lg" onClick={onDeny}>
              <Ban size={18} aria-hidden="true" />
              Deny
            </button>
          </>
        )}
      </div>
    </div>
  )
}

function NotFoundPanel({ result, onPick, onLogUnregistered }) {
  const suggestions = result.suggestions || { students: [], devices: [] }
  const hasSuggestions = suggestions.students?.length || suggestions.devices?.length

  return (
    <div className="card">
      <div className="note note-warn" style={{ marginBottom: hasSuggestions ? 14 : 0 }}>
        <span>
          <TriangleAlert size={16} aria-hidden="true" style={{ verticalAlign: '-3px' }} />{' '}
          {result.message}
        </span>
      </div>

      {hasSuggestions ? (
        <>
          <h3 style={{ fontSize: 14, marginBottom: 10 }}>Did you mean…</h3>
          <div className="row-actions">
            {suggestions.students.map((student) => (
              <button
                key={`s${student.id}`}
                type="button"
                className="btn btn-outline btn-sm"
                onClick={() => onPick(student.reg_number)}
              >
                {student.reg_number} - {student.full_name}
              </button>
            ))}
            {suggestions.devices.map((device) => (
              <button
                key={`d${device.id}`}
                type="button"
                className="btn btn-outline btn-sm"
                onClick={() => onPick(device.serial_number)}
              >
                {device.serial_number} - {device.label}
              </button>
            ))}
          </div>
        </>
      ) : null}

      <div className="decision-row">
        <button type="button" className="btn btn-warn btn-lg" onClick={onLogUnregistered}>
          <CircleHelp size={18} aria-hidden="true" />
          Log as unregistered device
        </button>
      </div>
    </div>
  )
}

function DecisionDialog({ dialog, direction, onClose, onConfirm }) {
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)

  const config = {
    DENY: {
      title: 'Record a denial',
      hint: 'What did you tell the student? This is kept on the permanent gate log.',
      required: false,
      button: 'Record denial',
      className: 'btn-hold',
    },
    OVERRIDE: {
      title: 'Override a blocked computer',
      hint: 'Say who authorised this and why. Overrides are reviewed by the security office.',
      required: true,
      button: 'Record override',
      className: 'btn-warn',
    },
    UNREGISTERED: {
      title: 'Log an unregistered device',
      hint: 'Describe the computer and what you did - send the student to the registration office.',
      required: false,
      button: 'Log it',
      className: 'btn-warn',
    },
  }[dialog.kind]

  const submit = async (event) => {
    event.preventDefault()
    if (config.required && !reason.trim()) return
    setBusy(true)
    await onConfirm({
      device: dialog.device,
      verdict:
        dialog.kind === 'DENY'
          ? 'DENIED'
          : dialog.kind === 'OVERRIDE'
            ? 'OVERRIDE'
            : 'UNREGISTERED',
      overrideReason: dialog.kind === 'OVERRIDE' ? reason : '',
      notes: dialog.kind === 'OVERRIDE' ? '' : reason,
    })
    setBusy(false)
  }

  return (
    <Modal title={config.title} onClose={onClose}>
      <form onSubmit={submit}>
        {dialog.device && (
          <p className="muted" style={{ marginTop: 0 }}>
            {dialog.device.brand} {dialog.device.model_name} · {dialog.device.serial_number} ·{' '}
            {direction === 'IN' ? 'entering' : 'leaving'} campus
          </p>
        )}
        <Field
          label={config.required ? 'Reason' : 'Note'}
          required={config.required}
          hint={config.hint}
        >
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            required={config.required}
            autoFocus
          />
        </Field>
        <div className="form-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className={`btn ${config.className}`} disabled={busy}>
            {busy ? 'Saving…' : config.button}
          </button>
        </div>
      </form>
    </Modal>
  )
}
