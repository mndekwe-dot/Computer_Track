import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * Delay a fast-changing value so it settles before anything acts on it.
 *
 * Without this, every list page fired one request per keystroke: typing a
 * nine-digit reg number meant nine round trips, of which eight were already
 * stale by the time they landed.
 */
export function useDebouncedValue(value, delay = 220) {
  const [settled, setSettled] = useState(value)

  useEffect(() => {
    const timer = setTimeout(() => setSettled(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])

  return settled
}

const EMPTY = { students: [], devices: [], truncated: false }

/**
 * Live typeahead against /api/search/suggest/.
 *
 * Three things keep it feeling instant and behaving correctly:
 *
 * - debounce, so a burst of keystrokes is one request;
 * - an AbortController, so a superseded request is cancelled rather than
 *    landing later and overwriting a newer result;
 * - a small in-memory cache, so backspacing to something already typed is
 *    immediate with no request at all.
 */
export function useLiveSearch(query, { minLength = 2, delay = 180, kinds } = {}) {
  const settled = useDebouncedValue(query, delay)
  const [results, setResults] = useState(EMPTY)
  const [searching, setSearching] = useState(false)
  const cache = useRef(new Map())
  const controller = useRef(null)

  const reset = useCallback(() => {
    controller.current?.abort()
    setResults(EMPTY)
    setSearching(false)
  }, [])

  useEffect(() => {
    const trimmed = (settled || '').trim()
    controller.current?.abort()

    if (trimmed.length < minLength) {
      setResults(EMPTY)
      setSearching(false)
      return undefined
    }

    const key = `${kinds || 'all'}:${trimmed.toUpperCase()}`
    const hit = cache.current.get(key)
    if (hit) {
      setResults(hit)
      setSearching(false)
      return undefined
    }

    const abort = new AbortController()
    controller.current = abort
    setSearching(true)

    // Imported lazily to keep this hook free of a circular import with the
    // endpoint module.
    import('../api/endpoints')
      .then(({ search }) => search.suggest(trimmed, kinds, abort.signal))
      .then((data) => {
        if (abort.signal.aborted) return
        cache.current.set(key, data)
        // A typeahead cache only needs the recent past.
        if (cache.current.size > 50) {
          cache.current.delete(cache.current.keys().next().value)
        }
        setResults(data)
      })
      .catch((error) => {
        if (!error?.isAborted) setResults(EMPTY)
      })
      .finally(() => {
        if (!abort.signal.aborted) setSearching(false)
      })

    return () => abort.abort()
  }, [settled, minLength, kinds])

  const isStale = (query || '').trim() !== (settled || '').trim()
  return { results, searching: searching || isStale, reset }
}
