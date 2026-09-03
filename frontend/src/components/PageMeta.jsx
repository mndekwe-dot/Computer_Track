import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

/**
 * Per-page title, description and crawler directives.
 *
 * A single-page application ships one `index.html`, so without this every
 * screen shares one title. That is worse than it sounds: the browser tab, the
 * history entry, the bookmark name and the first line a screen reader
 * announces after a route change all come from `document.title`. A guard with
 * six tabs open had six tabs called "Computer Track".
 *
 * It also decides what search engines may index, which for this application
 * is a short list. The landing page and the student form are public and
 * should be found. Every portal screen is behind a login, holds a register of
 * named students, and must never be indexed - `noindex` is the default here
 * for that reason, and a page has to ask to be listed.
 */

const SITE_URL = (import.meta.env.VITE_SITE_URL || window.location.origin).replace(/\/$/, '')

function setMeta(selector, attributes) {
  let element = document.head.querySelector(selector)
  if (!element) {
    element = document.createElement(attributes.tag || 'meta')
    Object.entries(attributes.identify || {}).forEach(([key, value]) =>
      element.setAttribute(key, value),
    )
    document.head.appendChild(element)
  }
  Object.entries(attributes.set || {}).forEach(([key, value]) => {
    if (value === null || value === undefined) element.removeAttribute(key)
    else element.setAttribute(key, value)
  })
  return element
}

export function PageMeta({
  title,
  description,
  // Off by default: see the note above. Only the two public pages pass this.
  index = false,
  noindex = false,
  image,
}) {
  const location = useLocation()
  const shouldIndex = index && !noindex

  useEffect(() => {
    const siteName = document.documentElement.dataset.siteName || 'Computer Track'
    const fullTitle = title ? `${title} · ${siteName}` : siteName
    document.title = fullTitle

    const canonical = `${SITE_URL}${location.pathname}`

    setMeta('meta[name="description"]', {
      identify: { name: 'description' },
      set: { content: description || '' },
    })
    setMeta('meta[name="robots"]', {
      identify: { name: 'robots' },
      // `noindex, follow` rather than `noindex, nofollow`: a crawler that
      // reaches a portal page should not list it, but there is no reason to
      // stop it following the link back to the public pages.
      set: {
        content: shouldIndex ? 'index, follow, max-image-preview:large' : 'noindex, follow',
      },
    })
    setMeta('link[rel="canonical"]', {
      tag: 'link',
      identify: { rel: 'canonical' },
      set: { href: canonical },
    })

    // Open Graph and Twitter, so a link pasted into a chat or an email shows
    // something meaningful rather than a bare URL. Only worth setting on the
    // pages people actually share, which are the ones that get indexed.
    const social = [
      ['meta[property="og:title"]', { property: 'og:title' }, fullTitle],
      ['meta[property="og:description"]', { property: 'og:description' }, description || ''],
      ['meta[property="og:url"]', { property: 'og:url' }, canonical],
      ['meta[property="og:type"]', { property: 'og:type' }, 'website'],
      ['meta[property="og:site_name"]', { property: 'og:site_name' }, siteName],
      ['meta[name="twitter:card"]', { name: 'twitter:card' }, 'summary_large_image'],
      ['meta[name="twitter:title"]', { name: 'twitter:title' }, fullTitle],
      ['meta[name="twitter:description"]', { name: 'twitter:description' }, description || ''],
    ]
    social.forEach(([selector, identify, content]) => {
      setMeta(selector, { identify, set: { content } })
    })

    if (image) {
      setMeta('meta[property="og:image"]', {
        identify: { property: 'og:image' },
        set: { content: image.startsWith('http') ? image : `${SITE_URL}${image}` },
      })
    }
  }, [title, description, shouldIndex, image, location.pathname])

  return null
}

/**
 * Announces a route change to a screen reader.
 *
 * Changing `document.title` is what a browser does on navigation and what
 * assistive technology listens for in a multi-page site. In a single-page
 * app nothing navigates, so the change goes unannounced and a keyboard user
 * is left on a page that has silently become a different page.
 */
export function RouteAnnouncer({ label }) {
  return (
    <div className="visually-hidden" role="status" aria-live="polite" aria-atomic="true">
      {label}
    </div>
  )
}
