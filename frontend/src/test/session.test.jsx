import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  idleMinutes,
  REASONS,
  reasonText,
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
    expect(left).toBeGreaterThan(idleMinutes() * 60 - 5)
    expect(left).toBeLessThanOrEqual(idleMinutes() * 60)
  })

  it('expires once the idle period has passed', () => {
    markActivity(Date.now() - (idleMinutes() + 1) * 60 * 1000)
    expect(isExpired()).toBe(true)
    expect(secondsRemaining()).toBeLessThan(0)
  })

  it('is still live just inside the window', () => {
    markActivity(Date.now() - (idleMinutes() - 1) * 60 * 1000)
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
    markActivity(Date.now() - (idleMinutes() - 1) * 60 * 1000)
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
    expect(reasonText(REASONS.IDLE)).toContain(String(idleMinutes()))
    expect(reasonText(REASONS.EXPIRED)).toBeTruthy()
    // A deliberate sign-out needs no explanation.
    expect(reasonText(REASONS.MANUAL)).toBe('')
  })

  it('never leaves an em dash in a message shown to a user', () => {
    [reasonText(REASONS.IDLE), reasonText(REASONS.EXPIRED)].forEach((text) => {
      expect(text).not.toMatch(/[—–]/)
    })
  })
})
