import {
  ClipboardList,
  DoorOpen,
  Flag,
  Boxes,
  MessageSquareText,
  ShieldAlert,
  SlidersHorizontal,
  GraduationCap,
  InboxIcon,
  LaptopMinimal,
  Upload,
  LayoutDashboard,
  ScanLine,
  ShieldCheck,
  Ticket,
  UserCog,
  Users,
} from 'lucide-react'

/**
 * The three portals are fully separate front doors: each has its own login URL,
 * its own navigation and its own accent colour, so a guard and a registrar
 * never see the same application.
 *
 * `roles` lists who may sign in there. Administrators are admitted everywhere
 * on top of this list - they need to be able to stand at a gate and reproduce
 * whatever a guard is seeing.
 */
export const PORTALS = {
  guard: {
    key: 'guard',
    base: '/guard',
    name: 'Security Gate',
    tagline: 'Computer checks at the gate',
    loginTitle: 'Security Gate Access',
    loginBlurb: 'For guards on duty at a campus entrance.',
    accent: '#1d4ed8',
    accentDark: '#1e40af',
    roles: ['GUARD'],
    home: '/guard/console',
    nav: [
      { to: '/guard/console', label: 'Gate Console', icon: ScanLine },
      { to: '/guard/log', label: 'Gate Log', icon: ClipboardList },
      { to: '/guard/account', label: 'My Account', icon: UserCog },
    ],
  },

  registry: {
    key: 'registry',
    base: '/registry',
    name: 'Registration Office',
    tagline: 'The computer register',
    loginTitle: 'Registration Office',
    loginBlurb: 'For staff who register computers and manage student records.',
    accent: '#0f766e',
    accentDark: '#115e59',
    roles: ['REGISTRAR'],
    home: '/registry/approvals',
    nav: [
      { to: '/registry/approvals', label: 'Pending Approvals', icon: InboxIcon },
      { to: '/registry/students', label: 'Students', icon: GraduationCap },
      { to: '/registry/import', label: 'Import Students', icon: Upload },
      { to: '/registry/devices', label: 'Computers', icon: LaptopMinimal },
      { to: '/registry/flags', label: 'Holds & Theft', icon: Flag },
      { to: '/registry/permits', label: 'Permits', icon: Ticket },
      { to: '/registry/gates', label: 'Gates', icon: DoorOpen },
      { to: '/registry/attempts', label: 'Registration Attempts', icon: ShieldAlert },
      { to: '/registry/equipment-types', label: 'Equipment Types', icon: Boxes },
      { to: '/registry/messages', label: 'Messages', icon: MessageSquareText },
      { to: '/registry/rules', label: 'Rules & Wording', icon: SlidersHorizontal },
      { to: '/registry/account', label: 'My Account', icon: UserCog },
    ],
  },

  admin: {
    key: 'admin',
    base: '/admin',
    name: 'Administration',
    tagline: 'Whole-campus oversight',
    loginTitle: 'System Administration',
    loginBlurb: 'For system administrators only.',
    accent: '#4a3aa7',
    accentDark: '#3c2f87',
    roles: ['ADMIN'],
    home: '/admin/dashboard',
    nav: [
      { to: '/admin/dashboard', label: 'Dashboard', icon: LayoutDashboard },
      { to: '/admin/approvals', label: 'Pending Approvals', icon: InboxIcon },
      { to: '/admin/log', label: 'Gate Log', icon: ClipboardList },
      { to: '/admin/students', label: 'Students', icon: GraduationCap },
      { to: '/admin/import', label: 'Import Students', icon: Upload },
      { to: '/admin/devices', label: 'Computers', icon: LaptopMinimal },
      { to: '/admin/flags', label: 'Holds & Theft', icon: Flag },
      { to: '/admin/permits', label: 'Permits', icon: Ticket },
      { to: '/admin/gates', label: 'Gates', icon: DoorOpen },
      { to: '/admin/attempts', label: 'Registration Attempts', icon: ShieldAlert },
      { to: '/admin/equipment-types', label: 'Equipment Types', icon: Boxes },
      { to: '/admin/messages', label: 'Messages', icon: MessageSquareText },
      { to: '/admin/rules', label: 'Rules & Wording', icon: SlidersHorizontal },
      { to: '/admin/staff', label: 'Staff Accounts', icon: Users },
      { to: '/admin/audit', label: 'Read Audit Log', icon: ShieldCheck },
      { to: '/admin/account', label: 'My Account', icon: UserCog },
    ],
  },
}

export const PORTAL_LIST = [PORTALS.guard, PORTALS.registry, PORTALS.admin]

/** Can this user work inside this portal? Admins may go anywhere. */
export function canEnter(user, portal) {
  if (!user || !portal) return false
  if (user.is_admin_role) return true
  return portal.roles.includes(user.role)
}

/** The portal a given user belongs in - where we send them after sign-in. */
export function homePortalFor(user) {
  if (!user) return PORTALS.guard
  if (user.is_admin_role) return PORTALS.admin
  return PORTAL_LIST.find((portal) => portal.roles.includes(user.role)) || PORTALS.guard
}
