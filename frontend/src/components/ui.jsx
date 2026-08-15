import { useEffect, useRef } from 'react'

export function StatusPill({ status, children }) {
  const tone = String(status || '').toUpperCase()
  return <span className={`pill pill-${tone}`}>{children || tone.replace(/_/g, ' ')}</span>
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

export function SkeletonTable({ columns, rows = 6 }) {
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

export function EmptyState({ title, children }) {
  return (
    <div className="empty-state">
      <h3>{title}</h3>
      {children && <p>{children}</p>}
    </div>
  )
}

export function Field({ label, error, hint, children, required }) {
  return (
    <label className="field">
      <span className="field-label">
        {label}
        {required && <em aria-hidden="true"> *</em>}
      </span>
      {children}
      {hint && !error && <span className="field-hint">{hint}</span>}
      {error && <span className="field-error">{error}</span>}
    </label>
  )
}

export function Modal({ title, onClose, children, wide = false }) {
  const ref = useRef(null)

  useEffect(() => {
    const onKey = (event) => event.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    ref.current?.focus()
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" role="dialog" aria-modal="true" aria-label={title} data-wide={wide}>
        <header className="modal-header">
          <h2>{title}</h2>
          <button type="button" className="btn btn-ghost" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </header>
        <div className="modal-body" ref={ref} tabIndex={-1}>
          {children}
        </div>
      </div>
    </div>
  )
}

export function Toast({ toast, onDismiss }) {
  useEffect(() => {
    if (!toast) return undefined
    const timer = setTimeout(onDismiss, toast.tone === 'error' ? 7000 : 4000)
    return () => clearTimeout(timer)
  }, [toast, onDismiss])

  if (!toast) return null
  return (
    <div className={`toast toast-${toast.tone || 'info'}`} role="status" aria-live="polite">
      {toast.message}
      <button type="button" className="toast-close" onClick={onDismiss} aria-label="Dismiss">
        ✕
      </button>
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
        ← Previous
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
        Next →
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
