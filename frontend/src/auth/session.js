/**
 * Session lifetime for a shared machine.
 *
 * The gate console runs on a terminal several guards use in turn, often left
 * facing an open queue. An unattended signed-in session there is a bigger risk
 * than anywhere else in the system, so the session ends on its own after a
 * period of no activity, with a warning first so nobody loses what they were
 * doing mid-queue.
 *
 * Timings are wall-clock, not timer-based: a laptop that sleeps for an hour
 * must come back expired, and a setTimeout would simply have been suspended.
 */

const LAST_ACTIVITY_KEY = 'ct.lastActivity'
const SIGNED_OUT_REASON_KEY = 'ct.signedOutReason'

const minutes = (value, fallback) => {
  const parsed = Number.parseFloat(value)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback
}

/**
 * How long a session may sit idle, and how much warning it gives first.
 *
 * These were module constants read from the build environment, which meant
 * changing the timeout on a terminal facing an open queue required a rebuild
 * and a redeploy. They are policy, not deployment: the registration office
 * sets them, and `configureSession` applies what the server sends.
 *
 * The build-time value stays as the starting point, so the console behaves
 * sensibly for the moment between first paint and the settings arriving.
 */
let config = {
  idleMinutes: minutes(import.meta.env.VITE_IDLE_MINUTES, 30),
  warnSeconds: minutes(import.meta.env.VITE_IDLE_WARN_SECONDS, 60),
}

export function configureSession(next = {}) {
  config = {
    idleMinutes: minutes(next.idleMinutes, config.idleMinutes),
    warnSeconds: minutes(next.warnSeconds, config.warnSeconds),
  }
}

export const idleMinutes = () => config.idleMinutes
export const warnSeconds = () => config.warnSeconds

export const ACTIVITY_EVENTS = [
  'mousedown',
  'keydown',
  'touchstart',
  'scroll',
  'focus',
]

export function markActivity(at = Date.now()) {
  try {
    localStorage.setItem(LAST_ACTIVITY_KEY, String(at))
  } catch {
    // A full or blocked localStorage should never break the console.
  }
}

export function lastActivity() {
  const raw = Number.parseInt(localStorage.getItem(LAST_ACTIVITY_KEY) || '', 10)
  return Number.isFinite(raw) ? raw : null
}

/** Seconds until the session ends. Negative once it already has. */
export function secondsRemaining(now = Date.now()) {
  const last = lastActivity()
  if (last === null) return idleMinutes() * 60
  return Math.round((last + idleMinutes() * 60 * 1000 - now) / 1000)
}

export function isExpired(now = Date.now()) {
  return secondsRemaining(now) <= 0
}

export function clearActivity() {
  localStorage.removeItem(LAST_ACTIVITY_KEY)
}

/**
 * Why the last sign-out happened, so the login page can say so.
 * Read once and cleared, so the message does not reappear later.
 */
export function setSignedOutReason(reason) {
  if (reason) localStorage.setItem(SIGNED_OUT_REASON_KEY, reason)
  else localStorage.removeItem(SIGNED_OUT_REASON_KEY)
}

export function takeSignedOutReason() {
  const reason = localStorage.getItem(SIGNED_OUT_REASON_KEY)
  localStorage.removeItem(SIGNED_OUT_REASON_KEY)
  return reason
}

export const REASONS = {
  IDLE: 'idle',
  EXPIRED: 'expired',
  MANUAL: 'manual',
}

/**
 * A function rather than a table, because the idle timeout is no longer known
 * at module load. Built as a table, the message quoted whatever the build
 * happened to be configured with, however the university had since set it.
 */
export function reasonText(reason) {
  if (reason === REASONS.IDLE) {
    const count = idleMinutes()
    return `You were signed out after ${count} ${count === 1 ? 'minute' : 'minutes'} without activity.`
  }
  if (reason === REASONS.EXPIRED) return 'Your session expired. Please sign in again.'
  return ''
}
