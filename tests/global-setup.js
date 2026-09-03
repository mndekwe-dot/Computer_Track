// @ts-check
import { mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'

/**
 * Sign in once for the whole run, not once per test.
 *
 * Login is throttled to 20/min, deliberately, and that is not a number to
 * raise for the convenience of a test suite. But a parallel run signing in
 * per test blows through it in seconds and then fails with a 429 that reads
 * like a broken page. So the tokens are fetched once here and every worker
 * reads them off disk.
 */

const API = process.env.API_URL || 'http://127.0.0.1:8000'
const PASSWORD = 'passw0rd!'
const USERS = ['guard1', 'registrar', 'admin']

// Resolved from the project root rather than from import.meta, because the
// root package.json is commonjs and import.meta is not available there.
export const AUTH_DIR = path.join(process.cwd(), 'playwright', '.auth')

export default async function globalSetup() {
  await mkdir(AUTH_DIR, { recursive: true })

  for (const username of USERS) {
    const response = await fetch(`${API}/api/auth/login/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password: PASSWORD }),
    })
    if (!response.ok) {
      throw new Error(
        `Could not sign in as ${username} (${response.status}).\n` +
          `The end-to-end suite needs the API running on ${API} with seed_demo data:\n` +
          `  cd backend && .venv/Scripts/python manage.py runserver 8000`,
      )
    }
    const session = await response.json()
    await writeFile(path.join(AUTH_DIR, `${username}.json`), JSON.stringify(session), 'utf8')
  }
}
