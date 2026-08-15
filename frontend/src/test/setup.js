import '@testing-library/jest-dom/vitest'
import { afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'

afterEach(() => {
  cleanup()
  localStorage.clear()
  vi.restoreAllMocks()
})

// jsdom has no navigator.onLine control and no fetch by default. The offline
// queue is built around both, so tests need to drive them.
if (!('onLine' in navigator)) {
  Object.defineProperty(navigator, 'onLine', { value: true, writable: true, configurable: true })
}

export function setOnline(online) {
  Object.defineProperty(navigator, 'onLine', {
    value: online,
    writable: true,
    configurable: true,
  })
  window.dispatchEvent(new Event(online ? 'online' : 'offline'))
}
