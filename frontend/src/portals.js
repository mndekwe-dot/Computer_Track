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
  LayoutDashboard,
  ScanLine,
  ShieldCheck,
  Ticket,
  Users,
} from 'lucide-react'

/**
 * The three portals stay fully separate once somebody is inside: separate
 * addresses, separate navigation, separate accent colour, so a guard and a
 * registrar never see the same application.
 *
 * What they no longer have is separate front doors. Staff sign in once at
 * `/login`, which names no portal, and `homePortalFor` decides where they
 * land. Three labelled login pages described the shape of the organisation to
 * anyone who had proved nothing, and asked staff to know which door was
 * theirs.
 *
 * `roles` lists who belongs here. Administrators are admitted everywhere on
 * top of this list: they need to be able to stand at a gate and reproduce
 * whatever a guard is seeing.
 */
export const PORTALS = {
  guard: {
    key: 'guard',
    base: '/guard',
    name: 'Security Gate',
    tagline: 'Computer checks at the gate',
    accent: '#1f3f7a',
    accentDark: '#162e5a',
    roles: ['GUARD'],
    home: '/guard/console',
    nav: [
      { to: '/guard/console', label: 'Gate console', icon: ScanLine },
      { to: '/guard/log', label: 'Gate log', icon: ClipboardList },
    ],
  },

  registry: {
    key: 'registry',
    base: '/registry',
    name: 'Registration Office',
    tagline: 'The computer register',
    accent: '#1d6a50',
    accentDark: '#15503c',
    roles: ['REGISTRAR'],
    home: '/registry/approvals',
    nav: [
      { group: 'Registrations', to: '/registry/approvals', label: 'Pending approvals', icon: InboxIcon },
      { group: 'Registrations', to: '/registry/attempts', label: 'Attempts', icon: ShieldAlert },
      { group: 'Records', to: '/registry/students', label: 'Students', icon: GraduationCap, also: ['/registry/import'] },
      { group: 'Records', to: '/registry/devices', label: 'Computers', icon: LaptopMinimal },
      { group: 'Records', to: '/registry/flags', label: 'Holds and theft', icon: Flag },
      { group: 'Records', to: '/registry/permits', label: 'Permits', icon: Ticket },
      { group: 'Setup', to: '/registry/gates', label: 'Gates', icon: DoorOpen },
      { group: 'Setup', to: '/registry/equipment-types', label: 'Equipment types', icon: Boxes },
      { group: 'Setup', to: '/registry/messages', label: 'Messages', icon: MessageSquareText },
      { group: 'Setup', to: '/registry/rules', label: 'Rules and wording', icon: SlidersHorizontal },
    ],
  },

  admin: {
    key: 'admin',
    base: '/admin',
    name: 'Administration',
    tagline: 'Whole-campus oversight',
    accent: '#5a3779',
    accentDark: '#45295d',
    roles: ['ADMIN'],
    home: '/admin/dashboard',
    nav: [
      { to: '/admin/dashboard', label: 'Dashboard', icon: LayoutDashboard },
      { to: '/admin/log', label: 'Gate log', icon: ClipboardList },
      { group: 'Registrations', to: '/admin/approvals', label: 'Pending approvals', icon: InboxIcon },
      { group: 'Registrations', to: '/admin/attempts', label: 'Attempts', icon: ShieldAlert },
      { group: 'Records', to: '/admin/students', label: 'Students', icon: GraduationCap, also: ['/admin/import'] },
      { group: 'Records', to: '/admin/devices', label: 'Computers', icon: LaptopMinimal },
      { group: 'Records', to: '/admin/flags', label: 'Holds and theft', icon: Flag },
      { group: 'Records', to: '/admin/permits', label: 'Permits', icon: Ticket },
      { group: 'Setup', to: '/admin/gates', label: 'Gates', icon: DoorOpen },
      { group: 'Setup', to: '/admin/equipment-types', label: 'Equipment types', icon: Boxes },
      { group: 'Setup', to: '/admin/messages', label: 'Messages', icon: MessageSquareText },
      { group: 'Setup', to: '/admin/rules', label: 'Rules and wording', icon: SlidersHorizontal },
      { group: 'Staff', to: '/admin/staff', label: 'Staff accounts', icon: Users },
      { group: 'Staff', to: '/admin/audit', label: 'Read audit log', icon: ShieldCheck },
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
