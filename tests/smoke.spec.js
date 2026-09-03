// @ts-check
import { test, expect } from '@playwright/test'
import { signIn, watchForErrors, expectNoRealErrors } from './helpers.js'

/**
 * Every screen, for the role that owns it, loading without throwing.
 *
 * This is the test that would have caught the settings page crashing into the
 * error boundary: it rendered, it screenshotted, and it was throwing the whole
 * time. Nothing in the unit suite goes near a real page.
 */

const SCREENS = [
  { user: null, path: '/', heading: /matched to the student/i },
  { user: null, path: '/register', heading: /computer registration/i },
  { user: null, path: '/guard/login', heading: /security gate/i },

  { user: 'guard1', path: '/guard/console', heading: /gate console/i },
  { user: 'guard1', path: '/guard/log', heading: /gate log/i },
  { user: 'guard1', path: '/guard/account', heading: /my account/i },

  { user: 'registrar', path: '/registry/approvals', heading: /approval/i },
  { user: 'registrar', path: '/registry/students', heading: /students/i },
  { user: 'registrar', path: '/registry/import', heading: /import/i },
  { user: 'registrar', path: '/registry/devices', heading: /computers/i },
  { user: 'registrar', path: '/registry/flags', heading: /holds/i },
  { user: 'registrar', path: '/registry/permits', heading: /permits/i },

  { user: 'admin', path: '/admin/dashboard', heading: /dashboard/i },
  { user: 'admin', path: '/admin/gates', heading: /gates/i },
  { user: 'admin', path: '/admin/staff', heading: /staff/i },
  { user: 'admin', path: '/admin/audit', heading: /audit/i },
]

for (const screen of SCREENS) {
  const who = screen.user ? `as ${screen.user}` : 'signed out'
  test(`${screen.path} loads ${who}`, async ({ page }) => {
    const errors = watchForErrors(page)
    if (screen.user) await signIn(page, screen.user)

    await page.goto(screen.path)
    await expect(page.getByRole('heading', { name: screen.heading }).first()).toBeVisible()
    // A screen that silently bounced elsewhere is not a screen that loaded.
    expect(new URL(page.url()).pathname).toBe(screen.path)
    expectNoRealErrors(errors)
  })
}

test('every page has exactly one h1 and a main landmark', async ({ page }) => {
  await signIn(page, 'admin')
  for (const path of ['/admin/dashboard', '/admin/students', '/admin/audit']) {
    await page.goto(path)
    await expect(page.locator('main')).toHaveCount(1)
    await expect(page.locator('h1')).toHaveCount(1)
  }
})

test('the skip link is the first thing a keyboard reaches', async ({ page }) => {
  await signIn(page, 'guard1')
  await page.goto('/guard/log')
  // Wait for the page to settle: tabbing before the shell has mounted lands
  // focus wherever the half-built document happens to put it.
  await expect(page.getByRole('heading', { name: /gate log/i })).toBeVisible()
  await page.evaluate(() => {
    if (document.activeElement instanceof HTMLElement) document.activeElement.blur()
  })
  await page.keyboard.press('Tab')

  const focused = page.locator('a.skip-link')
  await expect(focused).toBeFocused()
  // And it must actually become visible, not merely take focus off-screen,
  // which is what a skip link that forgets its :focus-visible rule does.
  await expect(focused).toBeInViewport()
})
