import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  IDLE_MINUTES,
  REASONS,
  REASON_TEXT,
  clearActivity,
  isExpired,
  lastActivity,
  markActivity,
  secondsRemaining,
  setSignedOutReason,
  takeSignedOutReason,
} from '../auth/session'

describe('session lifetime', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.useRealTimers()
  })

  it('treats a session with no recorded activity as fresh', () => {
    expect(lastActivity()).toBeNull()
    expect(isExpired()).toBe(false)
  })

  it('counts down from the last activity', () => {
    markActivity(Date.now())
    const left = secondsRemaining()
    expect(left).toBeGreaterThan(IDLE_MINUTES * 60 - 5)
    expect(left).toBeLessThanOrEqual(IDLE_MINUTES * 60)
  })

  it('expires once the idle period has passed', () => {
    markActivity(Date.now() - (IDLE_MINUTES + 1) * 60 * 1000)
    expect(isExpired()).toBe(true)
    expect(secondsRemaining()).toBeLessThan(0)
  })

  it('is still live just inside the window', () => {
    markActivity(Date.now() - (IDLE_MINUTES - 1) * 60 * 1000)
    expect(isExpired()).toBe(false)
  })

  it('uses wall-clock time, so a sleeping machine wakes up expired', () => {
    // A setTimeout would simply have been suspended while the lid was shut;
    // a stored timestamp cannot be.
    markActivity(Date.now())
    expect(isExpired()).toBe(false)

    const eightHoursLater = Date.now() + 8 * 60 * 60 * 1000
    expect(isExpired(eightHoursLater)).toBe(true)
  })

  it('activity pushes the deadline back', () => {
    markActivity(Date.now() - (IDLE_MINUTES - 1) * 60 * 1000)
    const before = secondsRemaining()
    markActivity(Date.now())
    expect(secondsRemaining()).toBeGreaterThan(before)
  })

  it('clearing activity resets it', () => {
    markActivity(Date.now())
    clearActivity()
    expect(lastActivity()).toBeNull()
  })

  it('ignores a corrupted timestamp rather than throwing', () => {
    localStorage.setItem('ct.lastActivity', 'not-a-number')
    expect(lastActivity()).toBeNull()
    expect(isExpired()).toBe(false)
  })

  it('remembers why the last sign-out happened, once', () => {
    setSignedOutReason(REASONS.IDLE)
    expect(takeSignedOutReason()).toBe(REASONS.IDLE)
    // Read once: the message must not reappear on a later visit.
    expect(takeSignedOutReason()).toBeNull()
  })

  it('has readable text for every reason a user would see', () => {
    expect(REASON_TEXT[REASONS.IDLE]).toContain(String(IDLE_MINUTES))
    expect(REASON_TEXT[REASONS.EXPIRED]).toBeTruthy()
    // A deliberate sign-out needs no explanation.
    expect(REASON_TEXT[REASONS.MANUAL]).toBeUndefined()
  })

  it('never leaves an em dash in a message shown to a user', () => {
    Object.values(REASON_TEXT).forEach((text) => {
      expect(text).not.toMatch(/[—–]/)
    })
  })
})
