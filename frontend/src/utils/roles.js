/**
 * Staff role catalogue (#244). Mirrors `backend/app/auth/roles.py`; keep the
 * two in sync. The API is authoritative — these tables only decide what the
 * dashboard *shows*, so a role never sees a section whose actions would 403.
 */

export const ROLES = Object.freeze({
  ADMIN: 'admin',
  FINANCE_OFFICER: 'finance_officer',
  FIELD_OFFICER: 'field_officer',
  OPERATIONS_OFFICER: 'operations_officer',
  SALES_OFFICER: 'sales_officer',
  FARM_OWNER: 'farm_owner',
  FARM_MANAGER: 'farm_manager',
  SUPERVISOR: 'supervisor',
})

export const ROLE_LABELS = Object.freeze({
  admin: 'Administrator',
  finance_officer: 'Finance officer',
  field_officer: 'Field officer',
  operations_officer: 'Operations officer',
  sales_officer: 'Sales officer',
  farm_owner: 'Farm owner',
  farm_manager: 'Farm manager',
  supervisor: 'Supervisor',
})

export const ROLE_DESCRIPTIONS = Object.freeze({
  admin: 'Everything: team, billing, settings, members, finance, commerce, communications',
  finance_officer: 'Payments, loans, settlements, buyers and sales, SMS and announcements',
  field_officer: 'Produce intake and aggregation batches',
  operations_officer: 'Produce intake and aggregation batches',
  sales_officer: 'Buyers and buyer sales',
  farm_owner: 'Workers, tasks, attendance, payroll and farm production',
  farm_manager: 'Workers, tasks, attendance, payroll runs and farm production',
  supervisor: 'Attendance only',
})

/** Roles that may be granted inside each organisation track. */
export const COOP_ROLES = Object.freeze(['admin', 'finance_officer', 'field_officer', 'operations_officer', 'sales_officer'])
export const SOLO_ROLES = Object.freeze(['admin', 'farm_owner', 'farm_manager', 'supervisor'])

export function rolesForTrack(organizationType) {
  return organizationType === 'solo_farm' ? SOLO_ROLES : COOP_ROLES
}

export function roleLabel(role) {
  return ROLE_LABELS[role] || (role ? role.replaceAll('_', ' ') : 'Unknown role')
}

const ALL = null // sentinel: every authenticated staff role may open the section

/**
 * Dashboard sections → roles that may open them, per track. `null` = everyone.
 * Derived from the `require_roles(...)` gates on the corresponding routes:
 * a section is listed for a role when that role can perform the section's
 * primary actions (or when it is read-only for all staff).
 */
const COOP_SECTION_ROLES = Object.freeze({
  overview: ALL,
  members: ['admin', 'finance_officer', 'field_officer', 'operations_officer'],
  attendance: ['admin', 'finance_officer', 'field_officer', 'operations_officer'],
  production: ['admin', 'finance_officer', 'field_officer', 'operations_officer'],
  scores: ['admin', 'finance_officer'],
  payments: ['admin', 'finance_officer'],
  loans: ['admin', 'finance_officer'],
  intake: ['admin', 'field_officer', 'operations_officer'],
  aggregation: ['admin', 'field_officer', 'operations_officer'],
  buyers: ['admin', 'finance_officer', 'sales_officer'],
  sales: ['admin', 'finance_officer', 'sales_officer'],
  settlements: ['admin', 'finance_officer'],
  sms: ['admin', 'finance_officer'],
  ussd: ['admin', 'finance_officer'],
  announcements: ['admin', 'finance_officer'],
  activity: ['admin', 'finance_officer'],
  settings: ALL,
})

const SOLO_SECTION_ROLES = Object.freeze({
  overview: ALL,
  workers: ['admin', 'farm_owner', 'farm_manager'],
  tasks: ['admin', 'farm_owner', 'farm_manager'],
  attendance: ['admin', 'farm_owner', 'farm_manager', 'supervisor'],
  payroll: ['admin', 'farm_owner', 'farm_manager'],
  production: ['admin', 'farm_owner', 'farm_manager'],
  sms: ['admin', 'farm_owner', 'farm_manager'],
  ussd: ['admin', 'farm_owner', 'farm_manager'],
  activity: ['admin', 'farm_owner'],
  settings: ALL,
})

function sectionTable(organizationType) {
  return organizationType === 'solo_farm' ? SOLO_SECTION_ROLES : COOP_SECTION_ROLES
}

/**
 * Whether `role` may open `section`. An unknown role (null — e.g. auth disabled
 * in local development) is treated as admin so nothing is hidden.
 */
export function canAccessSection(section, role, organizationType) {
  const table = sectionTable(organizationType)
  if (!(section in table)) return false
  const allowed = table[section]
  if (allowed === ALL) return true
  if (!role) return true
  return allowed.includes(role)
}

/** Filter nav groups (`[{label, items: [{key, ...}]}]`) to what `role` may open. */
export function filterNavGroups(groups, role, organizationType) {
  return groups
    .map((group) => ({ ...group, items: group.items.filter((item) => canAccessSection(item.key, role, organizationType)) }))
    .filter((group) => group.items.length > 0)
}

/** First section the role may land on (used for redirects off forbidden sections). */
export function defaultSectionFor(role, organizationType) {
  if (organizationType === 'solo_farm' && role === 'supervisor') return 'attendance'
  return 'overview'
}

/** Roles that may mutate a given resource, mirroring backend `require_roles`. */
export const ACTION_ROLES = Object.freeze({
  manageMembers: ['admin'],
  recordMemberAttendance: ['admin'],
  recordProduction: ['admin'],
  managePayments: ['admin', 'finance_officer'],
  manageLoans: ['admin', 'finance_officer'],
  manageIntake: ['admin', 'field_officer', 'operations_officer'],
  manageAggregation: ['admin', 'field_officer', 'operations_officer'],
  manageBuyers: ['admin', 'finance_officer', 'sales_officer'],
  recordSales: ['admin', 'finance_officer', 'sales_officer'],
  settleSales: ['admin', 'finance_officer'],
  sendSms: ['admin', 'finance_officer'],
  publishAnnouncements: ['admin', 'finance_officer'],
  manageTeam: ['admin'],
  manageBilling: ['admin'],
  manageCooperative: ['admin'],
  manageWorkers: ['admin', 'farm_owner', 'farm_manager'],
  deleteWorkers: ['admin', 'farm_owner'],
  manageTasks: ['admin', 'farm_owner', 'farm_manager'],
  recordWorkerAttendance: ['admin', 'farm_owner', 'farm_manager', 'supervisor'],
  runPayroll: ['admin', 'farm_owner', 'farm_manager'],
  disbursePayroll: ['admin', 'farm_owner'],
})

/** Whether `role` may perform `action`. Unknown role (auth disabled) → allowed. */
export function can(action, role) {
  const allowed = ACTION_ROLES[action]
  if (!allowed) return false
  if (!role) return true
  return allowed.includes(role)
}
