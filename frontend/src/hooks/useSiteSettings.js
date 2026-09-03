import { useEffect, useState } from 'react'
import { publicApi } from '../api/endpoints'

/**
 * The names, numbers and switches the public pages need, from the server.
 *
 * The university's name, the registration office's telephone number, whether
 * online registration is open at all: none of those are facts about the
 * software, and every one of them was previously written into the frontend.
 * Changing the security control number meant a rebuild and a redeploy.
 *
 * Fetched once per page load and shared, because half a dozen components ask
 * for it and a request each would be six identical round trips on first
 * paint. The values change perhaps twice a year, so a reload picking up a
 * change is soon enough.
 */

const FALLBACK = {
  'branding.system_name': 'Computer Track',
  'branding.university_name': 'the university',
  'branding.office_name': 'the registration office',
  'branding.support_email': '',
  'branding.support_phone': '',
  'branding.security_phone': '',
  'registration.public_form_enabled': true,
  'registration.missing_report_enabled': true,
  'registration.require_photo': true,
  'registration.require_ownership_proof': false,
  'session.idle_minutes': 30,
  'session.idle_warning_seconds': 60,
}

let inFlight = null
let cached = null

function load() {
  if (cached) return Promise.resolve(cached)
  if (inFlight) return inFlight

  inFlight = publicApi
    .choices()
    .then((data) => {
      cached = {
        // Anything the server did not send keeps its fallback, so a new
        // setting added server-side cannot leave a page rendering "undefined".
        settings: { ...FALLBACK, ...(data.settings || {}) },
        deviceTypes: data.device_types || [],
      }
      return cached
    })
    .catch(() => {
      // A landing page that will not render because a settings request failed
      // is a worse outcome than one showing the built-in wording. This is
      // presentation, not policy: every rule that actually gates anything is
      // enforced on the server regardless of what the browser believes.
      cached = { settings: { ...FALLBACK }, deviceTypes: [], failed: true }
      return cached
    })
    .finally(() => {
      inFlight = null
    })

  return inFlight
}

export function useSiteSettings() {
  const [state, setState] = useState(
    cached || { settings: FALLBACK, deviceTypes: [], loading: true },
  )

  useEffect(() => {
    let alive = true
    load().then((result) => {
      if (alive) setState({ ...result, loading: false })
    })
    return () => {
      alive = false
    }
  }, [])

  return state
}

/** Test seam: drops the module-level cache between cases. */
export function resetSiteSettings() {
  cached = null
  inFlight = null
}
