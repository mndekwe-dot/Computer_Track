/**
 * Lookups the guard has already done this shift, kept so a repeat works
 * offline.
 *
 * The obvious way to make a gate console work offline is to download the
 * register to the device. That is the one thing this must not do. The
 * register is every student's name, photograph, telephone number and
 * equipment; a tablet holding a copy is a tablet that leaks all of it when it
 * is left on a desk or taken. A gate console is the least physically secure
 * device in the system.
 *
 * So only what has actually been looked up is kept, and only briefly. That
 * covers the case that genuinely happens - a student comes back through the
 * same gate, or the guard checks a second time before deciding - without the
 * device ever holding a record of somebody who has not walked past it.
 *
 * Four limits, all deliberate:
 *
 *   sessionStorage, not localStorage. The copy dies when the tab closes.
 *   A short expiry, so a hold placed ten minutes ago is not missed for long.
 *   A small cap on entries, oldest evicted first.
 *   Cleared on sign-out, so the next guard on the terminal starts clean.
 *
 * A cached answer is always marked as cached where it is shown. A guard has
 * to know they are looking at a copy, because a computer reported stolen
 * since the lookup would still read as clear.
 */

const KEY = 'ct.lookupCache'

// Long enough to cover somebody stepping away and coming back, short enough
// that a hold raised in the office reaches the gate quickly.
const TTL_MS = 10 * 60 * 1000

// A shift's worth of repeat visitors, not a register.
const MAX_ENTRIES = 40

function read() {
  try {
    const parsed = JSON.parse(sessionStorage.getItem(KEY) || '{}')
    return parsed && typeof parsed === 'object' ? parsed : {}
  } catch {
    return {}
  }
}

function write(entries) {
  try {
    sessionStorage.setItem(KEY, JSON.stringify(entries))
  } catch {
    // Full or blocked storage costs the offline copy and nothing else.
  }
}

function normalise(query, direction) {
  return `${(query || '').trim().toUpperCase()}|${direction || 'OUT'}`
}

/** Store one lookup result. */
export function remember(query, direction, payload) {
  if (!query || !payload) return
  const entries = read()
  entries[normalise(query, direction)] = { at: Date.now(), payload }

  const keys = Object.keys(entries)
  if (keys.length > MAX_ENTRIES) {
    keys
      .sort((a, b) => entries[a].at - entries[b].at)
      .slice(0, keys.length - MAX_ENTRIES)
      .forEach((key) => delete entries[key])
  }
  write(entries)
}

/**
 * A previous answer for this query, or null.
 *
 * Returns the payload with `from_cache` and `cached_at` attached, so whatever
 * renders it cannot forget to say that it is a copy.
 */
export function recall(query, direction) {
  const entry = read()[normalise(query, direction)]
  if (!entry) return null
  if (Date.now() - entry.at > TTL_MS) return null
  return { ...entry.payload, from_cache: true, cached_at: entry.at }
}

export function clearLookupCache() {
  try {
    sessionStorage.removeItem(KEY)
  } catch {
    // Nothing to do: the entries expire on their own and die with the tab.
  }
}
