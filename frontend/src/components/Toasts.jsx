import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import { AlertTriangle, CheckCircle2, Info, X } from 'lucide-react'

/**
 * Confirmations and failures, in one place.
 *
 * Each page used to hold its own `toast` state and render its own region.
 * That meant a second message replaced the first mid-sentence, and a
 * confirmation raised while navigating away was lost with the component that
 * owned it. One host at the root fixes both.
 *
 * Three rules the rest of this file exists to keep:
 *
 * Errors do not disappear. A message naming what went wrong is no use if it
 * removes itself before it has been read, and a guard mid-decision is exactly
 * the person who looks up too late. Successes time out; failures wait.
 *
 * Pointing at a toast stops its clock. Reading is the one activity a
 * disappearing message punishes.
 *
 * Motion is never the only signal. Every toast carries an icon and a written
 * message, so it says the same thing with the animation switched off.
 */

const ToastContext = createContext(null)

// Long enough to read a sentence twice. Five seconds is the floor for
// anything auto-dismissing; below that a message becomes a flicker.
const DISMISS_AFTER = 5000

// Older messages are dropped rather than stacking indefinitely, because a
// column of them covers the thing the reader is trying to act on.
const MAX_VISIBLE = 3

let nextId = 0

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])

  const dismiss = useCallback((id) => {
    setToasts((current) => current.filter((toast) => toast.id !== id))
  }, [])

  const show = useCallback((input) => {
    // Accepts a bare string or the {tone, message} shape.
    const toast = typeof input === 'string' ? { message: input } : input || {}
    if (!toast.message) return null
    const id = ++nextId
    setToasts((current) => [...current.slice(-(MAX_VISIBLE - 1)), { ...toast, id }])
    return id
  }, [])

  const api = useMemo(
    () => ({
      show,
      dismiss,
      success: (message) => show({ tone: 'success', message }),
      error: (message) => show({ tone: 'error', message }),
      info: (message) => show({ tone: 'info', message }),
      dismissAll: () => setToasts([]),
    }),
    [show, dismiss],
  )

  return (
    <ToastContext.Provider value={api}>
      {children}
      <ToastHost toasts={toasts} onDismiss={dismiss} />
    </ToastContext.Provider>
  )
}

export function useToast() {
  const api = useContext(ToastContext)
  if (!api) {
    // A page rendered outside the provider should not crash on a success
    // message. It loses the toast, which is worse than showing it and better
    // than an error boundary.
    return {
      show: () => null,
      dismiss: () => {},
      dismissAll: () => {},
      success: () => null,
      error: () => null,
      info: () => null,
    }
  }
  return api
}

const ICONS = {
  success: CheckCircle2,
  error: AlertTriangle,
  info: Info,
}

function ToastHost({ toasts, onDismiss }) {
  const errors = toasts.filter((toast) => toast.tone === 'error')
  const rest = toasts.filter((toast) => toast.tone !== 'error')

  return (
    <div className="toast-region">
      {/*
        Two regions, not one. A failure has to interrupt whatever the screen
        reader is currently saying; a confirmation has to wait its turn. One
        region can only have one politeness setting, so either errors arrive
        late or every "Saved." talks over the page.

        Both are always in the DOM. A live region inserted at the same moment
        as its text is announced unreliably, which is why a second identical
        message often went unread.
      */}
      <div className="toast-stack" role="alert" aria-live="assertive">
        {errors.map((toast) => (
          <ToastItem key={toast.id} toast={toast} onDismiss={onDismiss} />
        ))}
      </div>
      <div className="toast-stack" role="status" aria-live="polite">
        {rest.map((toast) => (
          <ToastItem key={toast.id} toast={toast} onDismiss={onDismiss} />
        ))}
      </div>
    </div>
  )
}

function ToastItem({ toast, onDismiss }) {
  const isError = toast.tone === 'error'
  const Icon = ICONS[toast.tone] || Info
  const [paused, setPaused] = useState(false)
  const timer = useRef(null)

  useEffect(() => {
    // Errors stay until dismissed, and a paused toast is one somebody is
    // reading or has tabbed to.
    if (isError || paused) return undefined
    timer.current = setTimeout(() => onDismiss(toast.id), toast.duration || DISMISS_AFTER)
    return () => clearTimeout(timer.current)
  }, [isError, paused, toast.id, toast.duration, onDismiss])

  return (
    <div
      className={`toast toast-${toast.tone || 'info'}`}
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)}
      onBlur={() => setPaused(false)}
    >
      <Icon size={17} className="toast-icon" aria-hidden="true" />
      <span className="toast-message">{toast.message}</span>
      {toast.action && (
        <button
          type="button"
          className="btn btn-ghost btn-sm toast-action"
          onClick={() => {
            toast.action.onClick()
            onDismiss(toast.id)
          }}
        >
          {toast.action.label}
        </button>
      )}
      <button
        type="button"
        className="toast-close"
        onClick={() => onDismiss(toast.id)}
        aria-label={`Dismiss: ${toast.message}`}
      >
        <X size={14} aria-hidden="true" />
      </button>
    </div>
  )
}
