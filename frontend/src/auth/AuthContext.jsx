import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import { tokens } from '../api/client'
import { clearLookupCache } from '../hooks/useLookupCache'
import { auth, publicApi } from '../api/endpoints'
import {
  ACTIVITY_EVENTS,
  REASONS,
  warnSeconds,
  clearActivity,
  configureSession,
  isExpired,
  markActivity,
  secondsRemaining,
  setSignedOutReason,
} from './session'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => tokens.user)
  const [loading, setLoading] = useState(Boolean(tokens.access))
  const [idleWarning, setIdleWarning] = useState(null)
  const userRef = useRef(user)
  userRef.current = user

  const endSession = useCallback((reason) => {
    tokens.clear()
    clearActivity()
    // A gate terminal is handed from one guard to the next. Whatever the last
    // shift looked up must not still be on the screen, or in storage, for the
    // next one.
    clearLookupCache()
    setSignedOutReason(reason)
    setIdleWarning(null)
    setUser(null)
  }, [])

  useEffect(() => {
    // How long a terminal may sit idle is policy the registration office
    // sets, not a build-time constant. Fetched once on boot; until it
    // arrives the built-in default applies, which is the safer direction to
    // be wrong in.
    publicApi
      .choices()
      .then((data) => {
        const settings = data?.settings || {}
        configureSession({
          idleMinutes: settings['session.idle_minutes'],
          warnSeconds: settings['session.idle_warning_seconds'],
        })
      })
      .catch(() => {
        // Keep the default. A settings request that fails must not leave a
        // shared terminal signed in indefinitely.
      })
  }, [])

  useEffect(() => {
    // Revalidate the stored session on boot: roles may have changed since the
    // guard last signed in, and a stale token should log them out cleanly.
    if (!tokens.access) {
      setLoading(false)
      return undefined
    }

    // A session left open overnight must not still be usable in the morning.
    if (isExpired()) {
      endSession(REASONS.IDLE)
      setLoading(false)
      return undefined
    }

    let cancelled = false
    auth
      .me()
      .then((profile) => {
        if (cancelled) return
        setUser(profile)
        tokens.save({ user: profile })
        markActivity()
      })
      .catch((error) => {
        if (cancelled) return
        if (!error.isNetwork) {
          endSession(REASONS.EXPIRED)
        }
      })
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [endSession])

  // Idle tracking. Only runs while somebody is actually signed in.
  useEffect(() => {
    if (!user) return undefined

    const onActivity = () => {
      // Moving the mouse during the warning is a deliberate "still here".
      markActivity()
      setIdleWarning(null)
    }
    ACTIVITY_EVENTS.forEach((event) =>
      window.addEventListener(event, onActivity, { passive: true }),
    )
    markActivity()

    // Polled rather than a single timeout, so a sleeping laptop wakes up
    // expired instead of resuming a timer that never fired.
    const tick = setInterval(() => {
      const left = secondsRemaining()
      if (left <= 0) {
        endSession(REASONS.IDLE)
      } else if (left <= warnSeconds()) {
        setIdleWarning(left)
      }
    }, 5000)

    return () => {
      ACTIVITY_EVENTS.forEach((event) => window.removeEventListener(event, onActivity))
      clearInterval(tick)
    }
  }, [user, endSession])

  // Signing out in one tab signs out the others on the same machine.
  useEffect(() => {
    const onStorage = (event) => {
      if (event.key === 'ct.access' && event.newValue === null && userRef.current) {
        setUser(null)
        setIdleWarning(null)
      }
    }
    window.addEventListener('storage', onStorage)
    return () => window.removeEventListener('storage', onStorage)
  }, [])

  const login = useCallback(async (username, password, otpToken) => {
    const data = await auth.login(username, password, otpToken)
    tokens.save({ access: data.access, refresh: data.refresh, user: data.user })
    markActivity()
    setSignedOutReason(null)
    setUser(data.user)
    return data.user
  }, [])

  const logout = useCallback(() => endSession(REASONS.MANUAL), [endSession])

  const staySignedIn = useCallback(() => {
    markActivity()
    setIdleWarning(null)
  }, [])

  const patchUser = useCallback((partial) => {
    setUser((current) => {
      const next = { ...current, ...partial }
      tokens.save({ user: next })
      return next
    })
  }, [])

  const value = useMemo(
    () => ({
      user,
      loading,
      login,
      logout,
      patchUser,
      idleWarning,
      staySignedIn,
      isAuthenticated: Boolean(user),
      canManageRecords: Boolean(user?.can_manage_records),
      isAdmin: Boolean(user?.is_admin_role),
    }),
    [user, loading, login, logout, patchUser, idleWarning, staySignedIn],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside an AuthProvider')
  return context
}
