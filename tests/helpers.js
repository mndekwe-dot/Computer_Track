// @ts-check
import { readFileSync } from 'node:fs'
import path from 'node:path'

import { expect } from '@playwright/test'

import { AUTH_DIR } from './global-setup.js'

export const API = process.env.API_URL || 'http://127.0.0.1:8000'
export const PASSWORD = 'passw0rd!'

/**
 * Put a signed-in session into the page before it loads.
 *
 * Driving the login form for every test would test the login form dozens of
 * times and the page under test once. There is a dedicated test for signing in
 * the real way; everything else starts already inside.
 */
// Read once per worker from what globalSetup wrote. No login traffic during
// the run at all, so the 20/min throttle never enters into it.
const sessions = new Map()

function sessionFor(username) {
  if (!sessions.has(username)) {
    sessions.set(
      username,
      JSON.parse(readFileSync(path.join(AUTH_DIR, `${username}.json`), 'utf8')),
    )
  }
  return sessions.get(username)
}

export async function signIn(page, username) {
  const { access, refresh, user } = sessionFor(username)
  await page.addInitScript(
    ([a, r, u]) => {
      localStorage.setItem('ct.access', a)
      localStorage.setItem('ct.refresh', r)
      localStorage.setItem('ct.user', u)
      // Without this the idle timer treats the session as stale and bounces
      // straight back to the login page.
      localStorage.setItem('ct.lastActivity', String(Date.now()))
    },
    [access, refresh, JSON.stringify(user)],
  )
}

/**
 * Collect console errors so a test can assert the page was not quietly
 * throwing. This is what caught the settings page calling its effect cleanup
 * on a promise: every screenshot looked fine, and the console did not.
 */
export function watchForErrors(page) {
  const errors = []
  page.on('pageerror', (error) => errors.push(error.message))
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text())
  })
  return errors
}

/** Fail on anything that is a real fault rather than an expected 4xx. */
export function expectNoRealErrors(errors) {
  const real = errors.filter(
    (text) => !/Failed to load resource: the server responded with a status of 4\d\d/.test(text),
  )
  expect(real, `console errors:\n${real.join('\n')}`).toEqual([])
}
