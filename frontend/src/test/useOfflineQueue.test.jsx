import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useOfflineQueue } from '../hooks/useOfflineQueue'
import { setOnline } from './setup'

vi.mock('../api/endpoints', () => ({
  checkpoint: {
    recordScan: vi.fn(),
    bulkScans: vi.fn(),
  },
}))

const { checkpoint } = await import('../api/endpoints')

const QUEUE_KEY = 'ct.scanQueue'

function networkError() {
  const error = new Error('Failed to fetch')
  error.isNetwork = true
  return error
}

function serverError(status) {
  const error = new Error('Bad request')
  error.status = status
  error.isNetwork = false
  return error
}

const SCAN = { device: 1, gate: 2, direction: 'OUT', verdict: 'ALLOWED' }

function queued() {
  return JSON.parse(localStorage.getItem(QUEUE_KEY) || '[]')
}

describe('useOfflineQueue', () => {
  beforeEach(() => {
    localStorage.clear()
    setOnline(true)
    checkpoint.recordScan.mockReset()
    checkpoint.bulkScans.mockReset()
    checkpoint.bulkScans.mockResolvedValue({ synced: 0, scans: [] })
  })

  it('sends straight through when the network is up', async () => {
    checkpoint.recordScan.mockResolvedValue({ id: 10 })
    const { result } = renderHook(() => useOfflineQueue())

    let outcome
    await act(async () => {
      outcome = await result.current.submitScan(SCAN)
    })

    expect(outcome.queued).toBe(false)
    expect(outcome.saved.id).toBe(10)
    expect(queued()).toHaveLength(0)
  })

  it('stamps every scan with an idempotency key and a real timestamp', async () => {
    checkpoint.recordScan.mockResolvedValue({ id: 10 })
    const { result } = renderHook(() => useOfflineQueue())

    await act(async () => {
      await result.current.submitScan(SCAN)
    })

    const sent = checkpoint.recordScan.mock.calls[0][0]
    expect(sent.client_reference).toBeTruthy()
    expect(Date.parse(sent.client_timestamp)).not.toBeNaN()
  })

  it('keeps the decision locally when the network drops', async () => {
    checkpoint.recordScan.mockRejectedValue(networkError())
    const { result } = renderHook(() => useOfflineQueue())

    let outcome
    await act(async () => {
      outcome = await result.current.submitScan(SCAN)
    })

    // The guard already made this decision; losing it is not an option.
    expect(outcome.queued).toBe(true)
    expect(queued()).toHaveLength(1)
    expect(result.current.queued).toBe(1)
  })

  it('surfaces a server rejection instead of silently queueing it', async () => {
    // A 400 means the server will never accept this scan. Queueing it would
    // hide a real problem from the guard and block the queue forever.
    checkpoint.recordScan.mockRejectedValue(serverError(400))
    const { result } = renderHook(() => useOfflineQueue())

    await expect(result.current.submitScan(SCAN)).rejects.toMatchObject({ status: 400 })
    expect(queued()).toHaveLength(0)
  })

  it('flushes the queue and empties it', async () => {
    localStorage.setItem(QUEUE_KEY, JSON.stringify([SCAN, SCAN]))
    checkpoint.bulkScans.mockResolvedValue({ synced: 2, scans: [] })

    const { result } = renderHook(() => useOfflineQueue())
    await act(async () => {
      await result.current.flush()
    })

    expect(checkpoint.bulkScans).toHaveBeenCalledWith([SCAN, SCAN])
    expect(queued()).toHaveLength(0)
    expect(result.current.queued).toBe(0)
  })

  it('flushes automatically when the network comes back', async () => {
    localStorage.setItem(QUEUE_KEY, JSON.stringify([SCAN]))
    setOnline(false)
    const { result } = renderHook(() => useOfflineQueue())
    expect(result.current.online).toBe(false)

    await act(async () => {
      setOnline(true)
    })

    await waitFor(() => expect(checkpoint.bulkScans).toHaveBeenCalled())
    expect(result.current.online).toBe(true)
  })

  it('keeps the queue when a flush fails for network reasons', async () => {
    localStorage.setItem(QUEUE_KEY, JSON.stringify([SCAN]))
    checkpoint.bulkScans.mockRejectedValue(networkError())

    const { result } = renderHook(() => useOfflineQueue())
    await act(async () => {
      await result.current.flush().catch(() => {})
    })

    // Still offline-ish: worth retrying, so nothing is thrown away.
    expect(queued()).toHaveLength(1)
  })

  it('drops a queue the server will never accept, so it cannot block forever', async () => {
    localStorage.setItem(QUEUE_KEY, JSON.stringify([SCAN]))
    checkpoint.bulkScans.mockRejectedValue(serverError(400))

    const { result } = renderHook(() => useOfflineQueue())
    await act(async () => {
      await result.current.flush().catch(() => {})
    })

    expect(queued()).toHaveLength(0)
  })

  it('does not attempt a flush while offline', async () => {
    localStorage.setItem(QUEUE_KEY, JSON.stringify([SCAN]))
    setOnline(false)

    const { result } = renderHook(() => useOfflineQueue())
    await act(async () => {
      await result.current.flush()
    })

    expect(checkpoint.bulkScans).not.toHaveBeenCalled()
    expect(queued()).toHaveLength(1)
  })
})
