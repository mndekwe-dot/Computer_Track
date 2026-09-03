/**
 * Registering the service worker, and noticing when a new one is waiting.
 *
 * Only in a production build. Under the dev server the module graph is served
 * unbundled and rewritten on every save, and a worker caching that fights the
 * dev server in ways that waste an afternoon.
 */

let onUpdateAvailable = () => {}

export function onUpdate(callback) {
  onUpdateAvailable = callback
}

export function registerServiceWorker() {
  if (!('serviceWorker' in navigator)) return
  if (!import.meta.env.PROD) return

  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register('/sw.js')
      .then((registration) => {
        registration.addEventListener('updatefound', () => {
          const installing = registration.installing
          if (!installing) return
          installing.addEventListener('statechange', () => {
            // `controller` is null on the very first install. Announcing an
            // update then would tell a first-time visitor that a new version
            // is ready before they have used the old one.
            if (installing.state === 'installed' && navigator.serviceWorker.controller) {
              onUpdateAvailable(() => {
                installing.postMessage('skip-waiting')
              })
            }
          })
        })
      })
      .catch(() => {
        // A failed registration costs the offline shell and nothing else. The
        // application works exactly as it did before, so this is not worth
        // interrupting anybody over.
      })
  })

  let reloading = false
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    // Guard against the reload loop this causes if two workers hand over in
    // quick succession.
    if (reloading) return
    reloading = true
    window.location.reload()
  })
}
