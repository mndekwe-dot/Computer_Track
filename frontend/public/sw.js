/* eslint-env serviceworker */

/**
 * Offline app shell for the gate console.
 *
 * A gate sits at the edge of campus where the network drops, and the console
 * runs on a phone or a tablet. Scans already survived that - they queue in
 * localStorage and flush on reconnect - but the application itself did not: a
 * refresh, a locked screen, or anything that discarded the page left a guard
 * holding a blank white screen with a queue of people in front of them.
 *
 * This caches the shell so the application starts with no network at all.
 *
 * What it deliberately does NOT cache is every API response. The register is
 * a list of named students with their photographs, telephone numbers and
 * equipment, and a device that keeps a copy of it is a device that leaks the
 * whole register when it is stolen. Lookups the guard has actually performed
 * are held in the tab's own session storage instead, where they die with the
 * tab - see src/hooks/useLookupCache.js.
 */

const VERSION = 'ct-shell-v1'
const SHELL = `${VERSION}-shell`

// The entry point only. Everything else is hashed and picked up on first use,
// which avoids maintaining a list here that goes stale on every build.
const SHELL_URLS = ['/', '/index.html', '/favicon.svg', '/site.webmanifest']

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(SHELL)
      // `reload` so an install triggered by a new deploy does not populate
      // the new cache from the browser's copy of the old files.
      .then((cache) => cache.addAll(SHELL_URLS.map((url) => new Request(url, { cache: 'reload' }))))
      // Take over as soon as the new worker is ready rather than waiting for
      // every tab to close. A gate terminal is never closed.
      .then(() => self.skipWaiting())
      .catch(() => self.skipWaiting()),
  )
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((key) => !key.startsWith(VERSION)).map((key) => caches.delete(key))),
      )
      .then(() => self.clients.claim()),
  )
})

function isApiRequest(url) {
  return url.pathname.startsWith('/api/')
}

function isHashedAsset(url) {
  return url.pathname.startsWith('/assets/')
}

self.addEventListener('fetch', (event) => {
  const { request } = event
  if (request.method !== 'GET') return

  const url = new URL(request.url)

  // Never touch the API. Responses carry student records and signed photo
  // links that expire; a stale cached one would be both a privacy problem and
  // a wrong answer at a gate, which is worse than no answer.
  if (isApiRequest(url) || url.origin !== self.location.origin) return

  // A navigation is the case that matters: this is what turns a refresh with
  // no network into the application rather than a browser error page.
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const copy = response.clone()
          caches.open(SHELL).then((cache) => cache.put('/index.html', copy))
          return response
        })
        .catch(() =>
          caches
            .match('/index.html')
            .then((cached) => cached || caches.match('/'))
            .then((cached) => cached || offlineResponse()),
        ),
    )
    return
  }

  // Hashed filenames never change contents, so a hit is always correct and
  // there is no revalidation worth paying for.
  if (isHashedAsset(url)) {
    event.respondWith(
      caches.match(request).then(
        (cached) =>
          cached ||
          fetch(request).then((response) => {
            if (response.ok) {
              const copy = response.clone()
              caches.open(SHELL).then((cache) => cache.put(request, copy))
            }
            return response
          }),
      ),
    )
    return
  }

  // Everything else - the manifest, the icon - takes the network when it can
  // and the cache when it cannot.
  event.respondWith(
    fetch(request)
      .then((response) => {
        if (response.ok) {
          const copy = response.clone()
          caches.open(SHELL).then((cache) => cache.put(request, copy))
        }
        return response
      })
      .catch(() => caches.match(request).then((cached) => cached || offlineResponse())),
  )
})

function offlineResponse() {
  return new Response(
    '<!doctype html><meta charset="utf-8"><title>Offline</title>' +
      '<style>body{font-family:system-ui,sans-serif;max-width:32rem;margin:4rem auto;padding:0 1.5rem;line-height:1.6}</style>' +
      '<h1>No connection</h1>' +
      '<p>This page has not been opened on this device before, so there is no copy to show ' +
      'you offline. Any scans you already recorded are saved and will sync when the network ' +
      'returns.</p>',
    { status: 503, headers: { 'Content-Type': 'text/html; charset=utf-8' } },
  )
}

// The page asks for this after a deploy so a gate terminal that is never
// closed still picks up a new version.
self.addEventListener('message', (event) => {
  if (event.data === 'skip-waiting') self.skipWaiting()
})
