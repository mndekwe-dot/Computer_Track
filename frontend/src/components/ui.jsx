import { cloneElement, isValidElement, useEffect, useId, useRef } from 'react'
import { ChevronLeft, ChevronRight, X } from 'lucide-react'

export function StatusPill({ status, children }) {
  const tone = String(status || '').toUpperCase()
  // The API sends codes like DENIED or IN_USE; people read "Denied".
  const label = tone.replace(/_/g, ' ').toLowerCase().replace(/^./, (c) => c.toUpperCase())
  return <span className={`pill pill-${tone}`}>{children || label}</span>
}

export function ErrorNote({ error, onRetry }) {
  if (!error) return null
  return (
    <div className="note note-error" role="alert">
      <span>{error.readable || String(error)}</span>
      {onRetry && (
        <button type="button" className="btn btn-ghost btn-sm" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  )
}

/**
 * Skeletons mirror the shape of the content that is coming, so the page does
 * not jump when data lands. They are used for the first load of a view; a
 * refetch dims the existing table instead, because blanking out rows the guard
 * is already reading is worse than a moment of stale data.
 */
export function SkeletonBar({ width = '100%', height = 12 }) {
  return <span className="skeleton-bar" style={{ width, height }} aria-hidden="true" />
}

export function SkeletonTable({ columns = [], rows = 6 }) {
  return (
    <div className="table-wrap" aria-busy="true" aria-label="Loading records">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: rows }, (_, rowIndex) => (
            <tr key={rowIndex}>
              {columns.map((column, colIndex) => (
                <td key={column}>
                  <SkeletonBar width={colIndex === 1 ? '75%' : colIndex === 0 ? '60%' : '45%'} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function SkeletonStats({ count = 8 }) {
  return (
    <div className="stat-grid" aria-busy="true" aria-label="Loading figures">
      {Array.from({ length: count }, (_, index) => (
        <div className="stat" key={index}>
          <SkeletonBar width="65%" height={10} />
          <div style={{ marginTop: 12 }}>
            <SkeletonBar width="40%" height={26} />
          </div>
        </div>
      ))}
    </div>
  )
}

export function SkeletonCard({ lines = 4 }) {
  return (
    <div className="card" aria-busy="true" aria-label="Loading">
      <SkeletonBar width="35%" height={15} />
      <div style={{ marginTop: 16, display: 'grid', gap: 10 }}>
        {Array.from({ length: lines }, (_, index) => (
          <SkeletonBar key={index} width={`${90 - index * 12}%`} />
        ))}
      </div>
    </div>
  )
}

export function SkeletonStudentCard() {
  return (
    <div className="card" aria-busy="true" aria-label="Looking up the register">
      <div className="student-card">
        <div className="skeleton-bar student-photo-placeholder" aria-hidden="true" />
        <div className="student-meta" style={{ flex: 1, display: 'grid', gap: 10 }}>
          <SkeletonBar width="45%" height={20} />
          <SkeletonBar width="30%" height={14} />
          <SkeletonBar width="60%" height={12} />
        </div>
      </div>
    </div>
  )
}

/** Wrap a list that is being refetched so it dims rather than disappears. */
export function Refreshing({ active, children }) {
  return (
    <div className="refreshable" data-refreshing={active ? 'true' : 'false'}>
      {children}
    </div>
  )
}

/**
 * An empty state that only describes the exit ("clear a filter") makes the
 * reader go and find the control. `action` puts the control here, which is
 * where they already are.
 */
export function EmptyState({ title, children, action }) {
  return (
    <div className="empty-state">
      <h3>{title}</h3>
      {children && <p>{children}</p>}
      {action && <div className="empty-state-action">{action}</div>}
    </div>
  )
}

/**
 * The hint and the error used to sit inside the `<label>`, which made them
 * part of the control's accessible name: a screen reader announced the label,
 * the hint and the error as one long run of words every time focus landed.
 * They now sit outside it and are attached with `aria-describedby`, which is
 * the mechanism meant for exactly this, and the control is marked invalid so
 * the state is announced rather than only coloured.
 */
export function Field({ label, error, hint, children, required }) {
  const id = useId()
  const hintId = `${id}-hint`
  const errorId = `${id}-error`
  const describedBy = error ? errorId : hint ? hintId : undefined

  const control =
    isValidElement(children) && describedBy
      ? cloneElement(children, {
          'aria-describedby':
            [children.props['aria-describedby'], describedBy].filter(Boolean).join(' '),
          'aria-invalid': error ? 'true' : children.props['aria-invalid'],
        })
      : children

  return (
    <div className="field">
      <label className="field-control">
        <span className="field-label">
          {label}
          {required && <em aria-hidden="true"> *</em>}
          {/* The asterisk is decorative, so without this the requirement is
              carried by a glyph assistive technology never sees. */}
          {required && <span className="visually-hidden"> (required)</span>}
        </span>
        {control}
      </label>
      {hint && !error && (
        <span className="field-hint" id={hintId}>
          {hint}
        </span>
      )}
      {error && (
        <span className="field-error" id={errorId}>
          {error}
        </span>
      )}
    </div>
  )
}

const FOCUSABLE =
  'a[href], button:not(:disabled), input:not(:disabled), select:not(:disabled), ' +
  'textarea:not(:disabled), [tabindex]:not([tabindex="-1"])'

/**
 * `aria-modal` tells assistive technology the rest of the page is inert, but
 * it does nothing for the Tab key: without a trap, focus walked straight out
 * of the dialog and into the page behind it, where the user could operate
 * controls they could no longer see. This keeps Tab and Shift+Tab inside the
 * dialog and returns focus to whatever opened it on close.
 */
export function Modal({ title, onClose, children, wide = false }) {
  const bodyRef = useRef(null)
  const dialogRef = useRef(null)

  useEffect(() => {
    const opener = document.activeElement
    bodyRef.current?.focus()

    const onKey = (event) => {
      if (event.key === 'Escape') {
        onClose()
        return
      }
      if (event.key !== 'Tab' || !dialogRef.current) return

      // Deliberately not an `offsetParent` visibility test: that is null for
      // anything inside a fixed-position ancestor and null throughout jsdom,
      // so it would quietly switch the trap off in the two places it matters
      // most. `hidden` is the attribute that actually means "not here", and a
      // visually-hidden control (the file input behind a styled button) is
      // meant to stay reachable.
      const items = [...dialogRef.current.querySelectorAll(FOCUSABLE)].filter(
        (node) => !node.closest('[hidden]'),
      )
      if (items.length === 0) return
      const first = items[0]
      const last = items[items.length - 1]
      const active = document.activeElement

      if (event.shiftKey && (active === first || active === bodyRef.current)) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && active === last) {
        event.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('keydown', onKey)
      // Returning focus is what makes a dialog feel like it closed rather
      // than like the page reloaded underneath you.
      if (opener instanceof HTMLElement) opener.focus()
    }
  }, [onClose])

  return (
    <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div
        ref={dialogRef}
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        data-wide={wide}
      >
        <header className="modal-header">
          <h2>{title}</h2>
          <button type="button" className="btn btn-ghost" onClick={onClose} aria-label="Close">
            <X size={16} aria-hidden="true" />
          </button>
        </header>
        <div className="modal-body" ref={bodyRef} tabIndex={-1}>
          {children}
        </div>
      </div>
    </div>
  )
}

export function Pagination({ count, page, pageSize = 25, onChange }) {
  const pages = Math.max(1, Math.ceil((count || 0) / pageSize))
  if (pages <= 1) return null
  return (
    <nav className="pagination" aria-label="Pagination">
      <button
        type="button"
        className="btn btn-ghost btn-sm"
        disabled={page <= 1}
        onClick={() => onChange(page - 1)}
      >
        <ChevronLeft size={15} aria-hidden="true" />
        Previous
      </button>
      <span>
        Page {page} of {pages} · {count} records
      </span>
      <button
        type="button"
        className="btn btn-ghost btn-sm"
        disabled={page >= pages}
        onClick={() => onChange(page + 1)}
      >
        Next
        <ChevronRight size={15} aria-hidden="true" />
      </button>
    </nav>
  )
}

export function formatDateTime(value) {
  if (!value) return ' - '
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ' - '
  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function formatTime(value) {
  if (!value) return ' - '
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ' - '
  return date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
}
