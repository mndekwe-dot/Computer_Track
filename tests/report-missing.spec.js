// @ts-check
import { test, expect } from '@playwright/test'
import { API, PASSWORD, signIn, watchForErrors, expectNoRealErrors } from './helpers.js'

/**
 * The public theft report, end to end and through the browser.
 *
 * This is the one unauthenticated write in the system that blocks something,
 * so the test that matters is not "the form submitted" but "the gate now
 * refuses it". The backend suite covers what the endpoint refuses; this covers
 * that a student on a phone can actually reach the outcome.
 */

/**
 * Create a student and a computer for this run rather than reusing seed data.
 *
 * The test blocks whatever it reports, so reusing a seeded device meant the
 * first project to finish left the second with a device already reported
 * missing, and a second run of the suite found none left. A test that mutates
 * shared state has to bring its own.
 */
async function createReportableDevice() {
  const login = await fetch(`${API}/api/auth/login/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'registrar', password: PASSWORD }),
  })
  const { access } = await login.json()
  const headers = { Authorization: `Bearer ${access}`, 'Content-Type': 'application/json' }

  const unique = `${Date.now()}${Math.floor(Math.random() * 1000)}`.slice(-9)
  const regNumber = `9${unique}`
  const email = `e2e.${unique}@student.example`

  const student = await fetch(`${API}/api/students/`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      reg_number: regNumber,
      first_name: 'Endto',
      last_name: 'End',
      email,
    }),
  })
  if (!student.ok) throw new Error(`could not create student: ${await student.text()}`)
  const owner = await student.json()

  const created = await fetch(`${API}/api/devices/`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      owner: owner.id,
      serial_number: `E2E${unique}`,
      brand: 'Testing',
      model_name: 'Fixture 1',
      device_type: 'LAPTOP',
      status: 'ACTIVE',
    }),
  })
  if (!created.ok) throw new Error(`could not create device: ${await created.text()}`)
  return { device: await created.json(), regNumber, email }
}

test('a student reports a theft and every gate stops the computer', async ({ page }) => {
  const errors = watchForErrors(page)
  const { device, regNumber, email } = await createReportableDevice()

  await page.goto('/register?tab=missing')
  await expect(page.getByRole('heading', { name: /computer registration/i })).toBeVisible()

  await page.getByLabel(/registration number/i).fill(regNumber)
  await page.getByLabel(/email or national id/i).fill(email)
  await page.getByLabel(/serial number/i).fill(device.serial_number)
  await page.getByLabel(/anything that would help/i).fill('Left in the lecture hall.')
  await page.getByRole('button', { name: /report it and block it/i }).click()

  await expect(page.getByRole('heading', { name: /every gate will now stop/i })).toBeVisible()
  expectNoRealErrors(errors)

  // The outcome that matters is at the gate, not on the confirmation screen.
  const guardLogin = await fetch(`${API}/api/auth/login/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'guard1', password: PASSWORD }),
  })
  const { access } = await guardLogin.json()
  const lookup = await (
    await fetch(`${API}/api/checkpoint/lookup/?q=${device.serial_number}`, {
      headers: { Authorization: `Bearer ${access}` },
    })
  ).json()

  expect(lookup.devices[0].is_blocked).toBe(true)
  expect(lookup.devices[0].status).toBe('STOLEN')
})

test('the tab is addressable, so it can be linked and bookmarked', async ({ page }) => {
  await page.goto('/register?tab=status')
  await expect(page.getByRole('tab', { name: /check my computers/i })).toHaveAttribute(
    'aria-selected',
    'true',
  )
})

test('the footer links a student to each thing they can do', async ({ page }) => {
  await page.goto('/')
  const footer = page.locator('.landing-footer')
  await expect(footer.getByRole('link', { name: /register a computer/i })).toHaveAttribute(
    'href',
    '/register',
  )
  await expect(footer.getByRole('link', { name: /check my computers/i })).toHaveAttribute(
    'href',
    '/register?tab=status',
  )
  // Three labelled groups rather than one undifferentiated pile of links.
  await expect(footer.getByRole('navigation')).toHaveCount(3)
})
