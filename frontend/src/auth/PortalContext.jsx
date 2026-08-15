import { createContext, useContext } from 'react'

const PortalContext = createContext(null)

export function PortalProvider({ portal, children }) {
  return <PortalContext.Provider value={portal}>{children}</PortalContext.Provider>
}

/**
 * The portal the current screen lives in. Pages use it to build links that stay
 * inside their own portal - `/registry/devices/4` rather than a bare
 * `/devices/4` that would not resolve.
 */
export function usePortal() {
  const portal = useContext(PortalContext)
  if (!portal) throw new Error('usePortal must be used inside a PortalProvider')
  return portal
}
