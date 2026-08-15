import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useDebouncedValue, useLiveSearch } from '../hooks/useLiveSearch'

vi.mock('../api/endpoints', () => ({
  search: { suggest: vi.fn() },
}))

const { search } = await import('../api/endpoints')

const RESULT = { students: [{ id: 1, reg_number: '218001234' }], devices: [], truncated: false }

describe('useDebouncedValue', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  it('holds the value until typing stops', () => {
    const { result, rerender } = renderHook(({ value }) => useDebouncedValue(value, 200), {
      initialProps: { value: 'a' },
    })
    expect(result.current).toBe('a')

    rerender({ value: 'ab' })
    rerender({ value: 'abc' })
    expect(result.current).toBe('a')

    act(() => vi.advanceTimersByTime(200))
    expect(result.current).toBe('abc')
  })

  it('restarts the clock on every keystroke', () => {
    const { result, rerender } = renderHook(({ value }) => useDebouncedValue(value, 200), {
      initialProps: { value: 'a' },
    })

    rerender({ value: 'ab' })
    act(() => vi.advanceTimersByTime(150))
    rerender({ value: 'abc' })
    act(() => vi.advanceTimersByTime(150))
    // 300ms total, but only 150ms since the last keystroke.
    expect(result.current).toBe('a')

    act(() => vi.advanceTimersByTime(50))
    expect(result.current).toBe('abc')
  })
})

describe('useLiveSearch', () => {
  beforeEach(() => {
    search.suggest.mockReset()
    search.suggest.mockResolvedValue(RESULT)
  })

  it('ignores anything shorter than the minimum', async () => {
    const { result } = renderHook(() => useLiveSearch('a'))
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 250))
    })
    expect(search.suggest).not.toHaveBeenCalled()
    expect(result.current.results.students).toEqual([])
  })

  it('searches once the query is long enough', async () => {
    const { result } = renderHook(() => useLiveSearch('uwa'))
    await waitFor(() => expect(result.current.results.students).toHaveLength(1))
    expect(search.suggest).toHaveBeenCalledTimes(1)
  })

  it('collapses a burst of keystrokes into one request', async () => {
    const { rerender } = renderHook(({ q }) => useLiveSearch(q), { initialProps: { q: 'u' } })
    rerender({ q: 'uw' })
    rerender({ q: 'uwa' })
    rerender({ q: 'uwas' })
    rerender({ q: 'uwase' })

    await waitFor(() => expect(search.suggest).toHaveBeenCalled())
    // Only the settled value is ever requested.
    expect(search.suggest).toHaveBeenCalledTimes(1)
    expect(search.suggest.mock.calls[0][0]).toBe('uwase')
  })

  it('passes an abort signal so a superseded request can be cancelled', async () => {
    const { result } = renderHook(() => useLiveSearch('uwa'))
    await waitFor(() => expect(search.suggest).toHaveBeenCalled())

    const signal = search.suggest.mock.calls[0][2]
    expect(signal).toBeInstanceOf(AbortSignal)
    expect(signal.aborted).toBe(false)
    expect(result.current.results.students).toHaveLength(1)
  })

  it('aborts the in-flight request when the query changes', async () => {
    const { rerender } = renderHook(({ q }) => useLiveSearch(q), { initialProps: { q: 'uwa' } })
    await waitFor(() => expect(search.suggest).toHaveBeenCalledTimes(1))
    const firstSignal = search.suggest.mock.calls[0][2]

    rerender({ q: 'mugisha' })
    await waitFor(() => expect(search.suggest).toHaveBeenCalledTimes(2))

    // Without this, a slow first response could land after the second and
    // show the guard results for a query they have already moved on from.
    expect(firstSignal.aborted).toBe(true)
  })

  it('a late aborted response does not overwrite newer results', async () => {
    const slow = { students: [{ id: 99, reg_number: 'STALE' }], devices: [], truncated: false }
    search.suggest
      .mockImplementationOnce(
        () => new Promise((resolve) => setTimeout(() => resolve(slow), 120)),
      )
      .mockResolvedValueOnce(RESULT)

    const { result, rerender } = renderHook(({ q }) => useLiveSearch(q), {
      initialProps: { q: 'sta' },
    })
    await waitFor(() => expect(search.suggest).toHaveBeenCalledTimes(1))
    rerender({ q: 'uwa' })

    await waitFor(() => expect(result.current.results.students[0]?.reg_number).toBe('218001234'))
    await new Promise((resolve) => setTimeout(resolve, 200))
    expect(result.current.results.students[0].reg_number).toBe('218001234')
  })

  it('serves a repeated query from cache without another request', async () => {
    const { result, rerender } = renderHook(({ q }) => useLiveSearch(q), {
      initialProps: { q: 'uwa' },
    })
    await waitFor(() => expect(search.suggest).toHaveBeenCalledTimes(1))

    rerender({ q: 'mugi' })
    await waitFor(() => expect(search.suggest).toHaveBeenCalledTimes(2))

    // Backspacing to something already typed should be instant.
    rerender({ q: 'uwa' })
    await waitFor(() => expect(result.current.results.students).toHaveLength(1))
    expect(search.suggest).toHaveBeenCalledTimes(2)
  })

  it('reports empty results when the request fails, without throwing', async () => {
    search.suggest.mockRejectedValue(new Error('boom'))
    const { result } = renderHook(() => useLiveSearch('uwa'))
    await waitFor(() => expect(result.current.searching).toBe(false))
    expect(result.current.results.students).toEqual([])
  })

  it('reset clears what is on screen', async () => {
    const { result } = renderHook(() => useLiveSearch('uwa'))
    await waitFor(() => expect(result.current.results.students).toHaveLength(1))

    act(() => result.current.reset())
    expect(result.current.results.students).toEqual([])
  })
})
