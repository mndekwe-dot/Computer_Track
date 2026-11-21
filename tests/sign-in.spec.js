// @ts-check
import { test, expect } from '@playwright/test'
import { signIn, PASSWORD } from './helpers.js'

/**
 * One front door.
 *
 * Staff used to sign in at `/guard/login`, `/registry/login` or
 * `/admin/login`, each page announcing whose door it was. These tests hold the
 * replacement in place: a single `/login` that names no portal, credentials
 * deciding where the person lands, and the old addresses still resolving for
 * anyone who bookmarked one.
 *
 * Only one test here posts real credentials. Login is throttled to 20/min on
 * purpose, and a suite that spends that budget fails on 429s that read like
 * application faults. Everywhere else the destination is checked from an
 * already-signed-in session, which exercises the same routing decision.
 */

test.describe('staff sign-in', () => {
  for (const old of ['/guard/login', '/registry/login', '/admin/login']) {
    test(`${old} redirects to the one sign-in page`, async ({ page }) => {
      await page.goto(old)
      await expect(page).toHaveURL(/\/login$/)
      await expect(page.getByRole('heading', { name: /^sign in$/i })).toBeVisible()
    })
  }

  test('the sign-in page names no portal', async ({ page }) => {
    await page.goto('/login')
    const body = await page.locator('body').innerText()
    // The portal names are what a visitor should not be able to read before
    // proving anything. "Registration office" is excluded deliberately: it is
    // also the real office a student is told to visit.
    expect(body).not.toMatch(/security gate/i)
    expect(body).not.toMatch(/system administration/i)
    // And no portal addresses to try.
    const portalLinks = await page
      .locator('a[href^="/guard"], a[href^="/registry"], a[href^="/admin"]')
      .count()
    expect(portalLinks).toBe(0)
  })

  test('a guard signing in for real lands at the gate console', async ({ page }) => {
    await page.goto('/login')
    await page.getByLabel('Username').fill('guard1')
    await page.getByLabel('Password').fill(PASSWORD)
    await page.getByRole('button', { name: /sign in/i }).click()
    // A generous window on purpose. This is the only test that waits on a real
    // token round trip, and the development server handles one request at a
    // time while the rest of the suite runs in parallel against it.
    await expect(page).toHaveURL(/\/guard\/console$/, { timeout: 30_000 })
    await expect(page.getByRole('heading', { name: /gate console/i })).toBeVisible()
  })

  // The same routing decision, one per role, without spending login requests.
  for (const [username, home] of [
    ['registrar', '/registry/approvals'],
    ['admin', '/admin/dashboard'],
    ['guard1', '/guard/console'],
  ]) {
    test(`${username} opening the sign-in page goes straight to their own portal`, async ({
      page,
    }) => {
      await signIn(page, username)
      await page.goto('/login')
      await expect(page).toHaveURL(new RegExp(`${home}$`))
    })
  }

  test('a guard who types another portal address is sent to their own', async ({ page }) => {
    await signIn(page, 'guard1')
    await page.goto('/admin/dashboard')
    await expect(page).toHaveURL(/\/guard\/console$/)
  })

  test('the sidebar offers no way to switch portal', async ({ page }) => {
    // An administrator is the one account that may enter every portal, so if a
    // switcher survived anywhere it would be here.
    await signIn(page, 'admin')
    await page.goto('/admin/dashboard')
    await expect(page.getByText(/switch portal/i)).toHaveCount(0)
  })

  test('signing out returns to the one sign-in page', async ({ page }) => {
    await signIn(page, 'guard1')
    await page.goto('/guard/console')
    // Wait for the page itself before asking what is visible: the drawer check
    // below reads as "no drawer" if React has not rendered yet.
    await expect(page.getByRole('heading', { name: /gate console/i })).toBeVisible()
    // On a phone the navigation is a drawer, and Sign out lives at the bottom
    // of it. A guard works from a phone at the gate, so this is the path that
    // matters most, not an edge case.
    const menu = page.locator('button.nav-toggle')
    if (await menu.isVisible()) {
      await menu.click()
      await expect(page.locator('aside.sidebar')).toHaveAttribute('data-open', 'true')
    }
    await page.getByRole('button', { name: /sign out/i }).click()
    await expect(page).toHaveURL(/\/login$/)
  })
})
