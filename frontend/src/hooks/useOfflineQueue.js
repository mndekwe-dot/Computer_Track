import { useCallback, useEffect, useState } from 'react'
import { checkpoint } from '../api/endpoints'

const QUEUE_KEY = 'ct.scanQueue'
const REJECTED_KEY = 'ct.scanQueue.rejected'

function readList(key) {
  try {
    const parsed = JSON.parse(localStorage.getItem(key) || '[]')
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function writeList(key, items) {
  try {
    localStorage.setItem(key, JSON.stringify(items))
  } catch {
    // Storage full or blocked. Nothing useful to do here, and throwing would
    // lose the decision the guard has already made.
  }
}

function newReference() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID()
  return `ref-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

/**
 * Gates sit at the edge of campus where the network drops. A decision the
 * guard has already made must never be lost, so every scan carries an
 * idempotency key and falls back to a local queue that flushes on reconnect.
 *
 * The key is what makes retrying safe: the server answers a replayed
 * reference with the original scan rather than writing a second one, so a
 * flush that half-succeeded and then lost the network can simply be repeated.
 */
export function useOfflineQueue() {
  const [queue, setQueue] = useState(() => readList(QUEUE_KEY))
  const [rejected, setRejected] = useState(() => readList(REJECTED_KEY))
  const [online, setOnline] = useState(() => navigator.onLine)
  const [syncing, setSyncing] = useState(false)
  const [lastSync, setLastSync] = useState(null)

  const flush = useCallback(async () => {
    const pending = readList(QUEUE_KEY)
    if (!pending.length || !navigator.onLine) return { synced: 0 }
    setSyncing(true)
    try {
      const result = await checkpoint.bulkScans(pending)
      writeList(QUEUE_KEY, [])
      setQueue([])
      setLastSync(new Date().toISOString())
      return result
    } catch (error) {
      // A validation error means the server will never accept these rows, so
      // leaving them in the queue would block every later sync behind scans
      // that can never go through.
      //
      // They are moved aside rather than deleted. Discarding them silently
      // destroyed a record of decisions a guard actually made - which is
      // exactly the thing this queue exists to protect - and left nobody with
      // any way to find out that it had happened.
      if (!error.isNetwork && error.status >= 400 && error.status < 500) {
        const failures = pending.map((scan) => ({
          scan,
          rejected_at: new Date().toISOString(),
          reason: error.readable || 'The server would not accept this scan.',
        }))
        const kept = [...readList(REJECTED_KEY), ...failures]
        writeList(REJECTED_KEY, kept)
        writeList(QUEUE_KEY, [])
        setRejected(kept)
        setQueue([])
      }
      throw error
    } finally {
      setSyncing(false)
    }
  }, [])

  useEffect(() => {
    const goOnline = () => {
      setOnline(true)
      flush().catch(() => {})
    }
    const goOffline = () => setOnline(false)
    window.addEventListener('online', goOnline)
    window.addEventListener('offline', goOffline)
    if (navigator.onLine) flush().catch(() => {})
    return () => {
      window.removeEventListener('online', goOnline)
      window.removeEventListener('offline', goOffline)
    }
  }, [flush])

  useEffect(() => {
    // `navigator.onLine` only reports whether there is a network interface,
    // not whether anything is reachable through it - campus wifi that has
    // dropped its uplink still reads as online. A queue that never drains is
    // the symptom, so a periodic attempt covers the case no event fires for.
    if (!queue.length) return undefined
    const timer = setInterval(() => {
      if (navigator.onLine) flush().catch(() => {})
    }, 30000)
    return () => clearInterval(timer)
  }, [queue.length, flush])

  /** Send a scan, queueing it locally if the network is unavailable. */
  const submitScan = useCallback(async (payload) => {
    const enriched = {
      ...payload,
      client_reference: payload.client_reference || newReference(),
      // The time the guard actually decided, which is what the log has to
      // show - not the time the network came back, which may be hours later.
      client_timestamp: payload.client_timestamp || new Date().toISOString(),
    }
    try {
      const saved = await checkpoint.recordScan(enriched)
      return { saved, queued: false }
    } catch (error) {
      if (error.isNetwork) {
        const pending = [...readList(QUEUE_KEY), enriched]
        writeList(QUEUE_KEY, pending)
        setQueue(pending)
        return { saved: enriched, queued: true }
      }
      throw error
    }
  }, [])

  /** Discard the scans the server refused, once somebody has looked at them. */
  const clearRejected = useCallback(() => {
    writeList(REJECTED_KEY, [])
    setRejected([])
  }, [])

  return {
    submitScan,
    flush,
    clearRejected,
    queue,
    queued: queue.length,
    rejected,
    online,
    syncing,
    lastSync,
  }
}
