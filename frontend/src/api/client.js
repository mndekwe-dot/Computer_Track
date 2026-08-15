const BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

const ACCESS_KEY = 'ct.access'
const REFRESH_KEY = 'ct.refresh'
const USER_KEY = 'ct.user'

export const tokens = {
  get access() {
    return localStorage.getItem(ACCESS_KEY)
  },
  get refresh() {
    return localStorage.getItem(REFRESH_KEY)
  },
  save({ access, refresh, user }) {
    if (access) localStorage.setItem(ACCESS_KEY, access)
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh)
    if (user) localStorage.setItem(USER_KEY, JSON.stringify(user))
  },
  get user() {
    try {
      return JSON.parse(localStorage.getItem(USER_KEY) || 'null')
    } catch {
      return null
    }
  },
  clear() {
    ;[ACCESS_KEY, REFRESH_KEY, USER_KEY].forEach((key) => localStorage.removeItem(key))
  },
}

export class ApiError extends Error {
  constructor(message, { status = 0, data = null, isNetwork = false } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.data = data
    this.isNetwork = isNetwork
  }

  /** Flatten DRF's {field: [msg]} shape into something a person can read. */
  get fieldErrors() {
    if (!this.data || typeof this.data !== 'object') return {}
    const out = {}
    for (const [key, value] of Object.entries(this.data)) {
      out[key] = Array.isArray(value) ? value.join(' ') : String(value)
    }
    return out
  }

  get readable() {
    if (this.isNetwork) return 'Cannot reach the server. Check the network connection.'
    const errors = this.fieldErrors
    const detail = errors.detail || errors.non_field_errors
    if (detail) return detail
    const first = Object.entries(errors)[0]
    if (first) return `${first[0].replace(/_/g, ' ')}: ${first[1]}`
    return this.message
  }
}

let refreshInFlight = null

async function refreshAccessToken() {
  // Several requests can 401 at once; they should share one refresh call.
  if (refreshInFlight) return refreshInFlight
  const refresh = tokens.refresh
  if (!refresh) return null

  refreshInFlight = (async () => {
    try {
      const response = await fetch(`${BASE_URL}/api/auth/refresh/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh }),
      })
      if (!response.ok) return null
      const data = await response.json()
      tokens.save({ access: data.access, refresh: data.refresh })
      return data.access
    } catch {
      return null
    } finally {
      refreshInFlight = null
    }
  })()

  return refreshInFlight
}

function buildUrl(path, params) {
  const url = new URL(`${BASE_URL}${path}`)
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      url.searchParams.set(key, value)
    }
  })
  return url.toString()
}

async function rawRequest(
  path,
  { method = 'GET', body, params, raw = false, retry = true, anonymous = false, signal } = {},
) {
  const headers = {}
  const access = tokens.access
  // The public student form must never send a token: a stale one would trigger
  // a refresh and could surface a login error on a page that has no login.
  if (access && !anonymous) headers.Authorization = `Bearer ${access}`

  const isFormData = body instanceof FormData
  if (body && !isFormData) headers['Content-Type'] = 'application/json'

  let response
  try {
    response = await fetch(buildUrl(path, params), {
      method,
      headers,
      body: isFormData ? body : body ? JSON.stringify(body) : undefined,
      signal,
    })
  } catch (error) {
    // A superseded live-search request is not a failure worth showing.
    if (error.name === 'AbortError') {
      const aborted = new ApiError('Request superseded', { status: 0 })
      aborted.isAborted = true
      throw aborted
    }
    throw new ApiError(error.message || 'Network request failed', { isNetwork: true })
  }

  if (response.status === 401 && retry && !anonymous && tokens.refresh) {
    const fresh = await refreshAccessToken()
    if (fresh) return rawRequest(path, { method, body, params, raw, retry: false, signal })
  }

  if (raw) {
    if (!response.ok) throw new ApiError('Request failed', { status: response.status })
    return response
  }

  if (response.status === 204) return null

  const text = await response.text()
  let data = null
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = text
    }
  }

  if (!response.ok) {
    throw new ApiError(`Request failed with ${response.status}`, {
      status: response.status,
      data,
    })
  }
  return data
}

export const api = {
  get: (path, params, options) => rawRequest(path, { params, ...options }),
  post: (path, body, params) => rawRequest(path, { method: 'POST', body, params }),
  /** Signed-out calls for the public student form. */
  publicPost: (path, body) => rawRequest(path, { method: 'POST', body, anonymous: true }),
  publicGet: (path) => rawRequest(path, { anonymous: true }),
  patch: (path, body) => rawRequest(path, { method: 'PATCH', body }),
  put: (path, body) => rawRequest(path, { method: 'PUT', body }),
  // DELETE carries a body here for password-confirmed actions such as turning
  // off two-factor.
  delete: (path, body) => rawRequest(path, { method: 'DELETE', body }),
  /** For binary responses such as QR PNGs and CSV exports. */
  blob: async (path, params) => {
    const response = await rawRequest(path, { params, raw: true })
    return response.blob()
  },
  baseUrl: BASE_URL,
}

/**
 * Absolute URL for a photo path returned by the API.
 *
 * These are signed and expiring rather than plain file paths, so they are
 * only good for about fifteen minutes and must not be cached in component
 * state across a long-lived session. Take them from the response each time.
 */
export function mediaUrl(path) {
  if (!path) return null
  if (path.startsWith('http')) return path
  return `${BASE_URL}${path}`
}
