import { useCallback, useEffect, useState } from 'react'
import { checkpoint } from '../api/endpoints'

const QUEUE_KEY = 'ct.scanQueue'

function readQueue() {
  try {
    return JSON.parse(localStorage.getItem(QUEUE_KEY) || '[]')
  } catch {
    return []
  }
}

function writeQueue(items) {
  localStorage.setItem(QUEUE_KEY, JSON.stringify(items))
}

function newReference() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID()
  return `ref-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

/**
 * Gates sit at the edge of campus where the network drops. A decision the
 * guard has already made must never be lost, so every scan carries an
 * idempotency key and falls back to a local queue that flushes on reconnect.
 */
export function useOfflineQueue() {
  const [queued, setQueued] = useState(() => readQueue().length)
  const [online, setOnline] = useState(() => navigator.onLine)
  const [syncing, setSyncing] = useState(false)

  const flush = useCallback(async () => {
    const pending = readQueue()
    if (!pending.length || !navigator.onLine) return { synced: 0 }
    setSyncing(true)
    try {
      const result = await checkpoint.bulkScans(pending)
      writeQueue([])
      setQueued(0)
      return result
    } catch (error) {
      // A validation error means the server will never accept these rows;
      // holding them forever would block every later sync. Anything else
      // (offline, server down) is worth retrying.
      if (!error.isNetwork && error.status >= 400 && error.status < 500) {
        writeQueue([])
        setQueued(0)
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

  /** Send a scan, queueing it locally if the network is unavailable. */
  const submitScan = useCallback(async (payload) => {
    const enriched = {
      ...payload,
      client_reference: payload.client_reference || newReference(),
      client_timestamp: payload.client_timestamp || new Date().toISOString(),
    }
    try {
      const saved = await checkpoint.recordScan(enriched)
      return { saved, queued: false }
    } catch (error) {
      if (error.isNetwork) {
        const pending = [...readQueue(), enriched]
        writeQueue(pending)
        setQueued(pending.length)
        return { saved: enriched, queued: true }
      }
      throw error
    }
  }, [])

  return { submitScan, flush, queued, online, syncing }
}
