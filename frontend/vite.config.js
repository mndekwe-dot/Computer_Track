import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

/**
 * robots.txt and sitemap.xml, written at build time.
 *
 * Both need absolute URLs - a sitemap with relative `<loc>` entries is
 * rejected outright - and the origin is not known until the site is built for
 * a particular deployment. Shipping them as static files in `public/` would
 * mean either hard-coding one university's address or shipping a sitemap no
 * crawler will accept.
 *
 * The list of public pages is short and deliberate. Every portal route sits
 * behind a login, in front of a register of named students with their
 * photographs and their equipment. None of that belongs in a search index, so
 * none of it is listed here and all of it is disallowed.
 */
function seoFiles() {
  const publicPages = [
    { path: '/', priority: '1.0' },
    { path: '/register', priority: '0.8' },
  ]

  return {
    name: 'computer-track-seo-files',
    apply: 'build',
    generateBundle() {
      const site = (process.env.VITE_SITE_URL || '').replace(/\/$/, '')
      // With no configured origin, emit relative paths and no sitemap
      // reference rather than a sitemap full of "undefined/register".
      const absolute = (path) => (site ? `${site}${path}` : path)

      const robots = [
        '# The public half of this site is two pages. Everything else is a staff',
        '# portal sitting in front of a register of named students, their',
        '# photographs and their equipment, and none of it should appear in a',
        '# search result.',
        '#',
        '# Disallow is not a security control - the portals are behind a login,',
        '# which is what actually protects them. This keeps them out of indexes',
        '# and out of the crawl budget.',
        '',
        'User-agent: *',
        'Allow: /$',
        'Allow: /register',
        '',
        'Disallow: /guard/',
        'Disallow: /registry/',
        'Disallow: /admin/',
        'Disallow: /api/',
        '',
        site ? `Sitemap: ${site}/sitemap.xml` : '# Set VITE_SITE_URL to publish a sitemap link.',
        '',
      ].join('\n')

      const today = new Date().toISOString().slice(0, 10)
      const entries = publicPages.map((page) =>
        [
          '  <url>',
          `    <loc>${absolute(page.path)}</loc>`,
          `    <lastmod>${today}</lastmod>`,
          '    <changefreq>monthly</changefreq>',
          `    <priority>${page.priority}</priority>`,
          '  </url>',
        ].join('\n'),
      )

      const sitemap = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        ...entries,
        '</urlset>',
        '',
      ].join('\n')

      this.emitFile({ type: 'asset', fileName: 'robots.txt', source: robots })
      this.emitFile({ type: 'asset', fileName: 'sitemap.xml', source: sitemap })
    },
  }
}

export default defineConfig({
  plugins: [react(), seoFiles()],
  build: {
    rollupOptions: {
      output: {
        // Recharts is a third of the bundle and only the admin dashboard uses
        // it. It is already lazily imported; splitting the rest of the vendor
        // code out as well means a guard's phone re-downloads only the app on
        // a deploy, not React with it.
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined
          if (id.includes('recharts') || id.includes('d3-')) return 'charts'
          if (id.includes('react-router')) return 'router'
          if (id.includes('react-dom') || id.includes('/react/')) return 'react'
          return undefined
        },
      },
    },
  },
  server: {
    port: 5173,
    // Guards open the console on a phone or tablet at the gate, so the dev
    // server has to listen on the LAN address too.
    host: true,
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.js',
    // Timers are faked per-test, not globally - the debounce tests need
    // control, everything else wants real ones.
    restoreMocks: true,
    // Vitest's default forked-process pool fails to start workers on this
    // Windows setup ("Timeout waiting for worker to respond"). Threads are
    // fine here and start faster.
    pool: 'threads',
  },
})
