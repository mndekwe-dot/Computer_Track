import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
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
    // Timers are faked per-test, not globally — the debounce tests need
    // control, everything else wants real ones.
    restoreMocks: true,
    // Vitest's default forked-process pool fails to start workers on this
    // Windows setup ("Timeout waiting for worker to respond"). Threads are
    // fine here and start faster.
    pool: 'threads',
  },
})
