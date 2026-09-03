import { Suspense, lazy } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth/AuthContext'
import { RequirePortal } from './auth/RequireAuth'
import { ErrorBoundary } from './components/ErrorBoundary'
import { IdleWarning } from './components/IdleWarning'
import { PortalShell } from './components/PortalShell'
import { PORTALS, homePortalFor } from './portals'

import { SkeletonCard, SkeletonStats } from './components/ui'
import Landing from './pages/Landing'
import PortalLogin from './pages/PortalLogin'
import PublicRegister from './pages/PublicRegister'
import Approvals from './pages/Approvals'
import AuditLog from './pages/AuditLog'
import GateConsole from './pages/GateConsole'
import ImportStudents from './pages/ImportStudents'
import Students from './pages/Students'
import Devices from './pages/Devices'
import DeviceDetail from './pages/DeviceDetail'
import ScanLog from './pages/ScanLog'
import Flags from './pages/Flags'
import Permits from './pages/Permits'
import Gates from './pages/Gates'
import Staff from './pages/Staff'
import Settings from './pages/Settings'

/*
 * The dashboard is the only screen that uses Recharts, and it is admin-only.
 * Loading it lazily keeps the charting library out of the bundle a guard
 * downloads on a phone at the gate.
 */
const Dashboard = lazy(() => import('./pages/Dashboard'))

function LazyDashboard() {
  return (
    <Suspense
      fallback={
        <div className="content">
          <SkeletonStats count={4} />
          <div className="two-col">
            <SkeletonCard lines={5} />
            <SkeletonCard lines={5} />
          </div>
        </div>
      }
    >
      <Dashboard />
    </Suspense>
  )
}

/**
 * Bare "/" shows the landing page, unless somebody is already signed in, in
 * which case there is no reason to make them choose a door they are already
 * through.
 */
function Root() {
  const { user, isAuthenticated, loading } = useAuth()
  if (loading) return <div className="page-loading">Checking your session…</div>
  if (isAuthenticated) return <Navigate to={homePortalFor(user).home} replace />
  return <Landing />
}

/** Anything unrecognised: back to the landing page rather than a dead end. */
function NotFound() {
  const { user, isAuthenticated, loading } = useAuth()
  if (loading) return <div className="page-loading">Checking your session…</div>
  return <Navigate to={isAuthenticated ? homePortalFor(user).home : '/'} replace />
}

function portalRoutes(portal, children) {
  return (
    <>
      <Route path={`${portal.base}/login`} element={<PortalLogin portal={portal} />} />
      <Route
        path={portal.base}
        element={
          <RequirePortal portal={portal}>
            <PortalShell portal={portal} />
          </RequirePortal>
        }
      >
        <Route index element={<Navigate to={portal.home} replace />} />
        {children}
      </Route>
    </>
  )
}

export default function App() {
  return (
    <ErrorBoundary>
      <IdleWarning />
      <Routes>
        <Route path="/" element={<Root />} />

        {/* Students. No login, no portal - a plain public page. */}
        <Route path="/register" element={<PublicRegister />} />

        {/* Security Gate - guards on duty */}
        {portalRoutes(
          PORTALS.guard,
          <>
            <Route path="console" element={<GateConsole />} />
            <Route path="log" element={<ScanLog />} />
            <Route path="account" element={<Settings />} />
          </>,
        )}

        {/* Registration Office - the register itself */}
        {portalRoutes(
          PORTALS.registry,
          <>
            <Route path="approvals" element={<Approvals />} />
            <Route path="students" element={<Students />} />
            <Route path="import" element={<ImportStudents />} />
            <Route path="devices" element={<Devices />} />
            <Route path="devices/:id" element={<DeviceDetail />} />
            <Route path="flags" element={<Flags />} />
            <Route path="permits" element={<Permits />} />
            {/* Gates are part of the register a registrar keeps, not an
                administrative setting: a new entrance opens and the office
                that maintains the register is the one that knows. The API
                already allowed this (CanManageRecords covers registrars);
                only the navigation was withholding it. */}
            <Route path="gates" element={<Gates />} />
            <Route path="account" element={<Settings />} />
          </>,
        )}

        {/* Administration - everything, plus staff accounts and the audit log */}
        {portalRoutes(
          PORTALS.admin,
          <>
            <Route path="dashboard" element={<LazyDashboard />} />
            <Route path="approvals" element={<Approvals />} />
            <Route path="log" element={<ScanLog />} />
            <Route path="students" element={<Students />} />
            <Route path="import" element={<ImportStudents />} />
            <Route path="devices" element={<Devices />} />
            <Route path="devices/:id" element={<DeviceDetail />} />
            <Route path="flags" element={<Flags />} />
            <Route path="permits" element={<Permits />} />
            <Route path="gates" element={<Gates />} />
            <Route path="staff" element={<Staff />} />
            <Route path="audit" element={<AuditLog />} />
            <Route path="account" element={<Settings />} />
          </>,
        )}

        <Route path="*" element={<NotFound />} />
      </Routes>
    </ErrorBoundary>
  )
}
