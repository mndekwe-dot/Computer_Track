import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { AuthProvider } from './auth/AuthContext'
// Self-hosted, so a gate kiosk on a slow or filtered connection still gets the
// typeface rather than silently falling back to whatever the OS ships.
import '@fontsource-variable/inter'
import './styles.css'
import { registerServiceWorker } from './offline/register'

// The gate console runs on a phone at the edge of campus. Without this, a
// refresh with no network is a blank page and a queue of people.
registerServiceWorker()

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)
