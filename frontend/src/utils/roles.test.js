import { describe, expect, it } from 'vitest'
import {
  COOP_ROLES,
  ROLE_LABELS,
  ROLES,
  SOLO_ROLES,
  can,
  canAccessSection,
  defaultSectionFor,
  filterNavGroups,
  roleLabel,
  rolesForTrack,
} from './roles'

const coopNav = [
  { label: 'Operations', items: [{ key: 'overview' }, { key: 'members' }, { key: 'attendance' }, { key: 'production' }, { key: 'scores' }] },
  { label: 'Finance', items: [{ key: 'payments' }, { key: 'loans' }] },
  { label: 'Commerce', items: [{ key: 'intake' }, { key: 'aggregation' }, { key: 'buyers' }, { key: 'sales' }, { key: 'settlements' }] },
  { label: 'Communications', items: [{ key: 'sms' }, { key: 'ussd' }, { key: 'announcements' }] },
  { label: 'Governance', items: [{ key: 'activity' }] },
]

const soloNav = [
  { label: 'Operations', items: [{ key: 'overview' }, { key: 'workers' }, { key: 'tasks' }, { key: 'attendance' }, { key: 'payroll' }, { key: 'production' }] },
  { label: 'Communications', items: [{ key: 'sms' }, { key: 'ussd' }] },
  { label: 'Governance', items: [{ key: 'activity' }] },
]

const keys = (groups) => groups.flatMap((group) => group.items.map((item) => item.key))

describe('role catalogue', () => {
  it('labels every role and splits them by track with admin in both', () => {
    const all = Object.values(ROLES)
    expect(all).toHaveLength(8)
    all.forEach((role) => expect(ROLE_LABELS[role]).toBeTruthy())
    expect(COOP_ROLES).toContain('admin')
    expect(SOLO_ROLES).toContain('admin')
    expect(new Set([...COOP_ROLES, ...SOLO_ROLES]).size).toBe(8)
    expect(rolesForTrack('solo_farm')).toBe(SOLO_ROLES)
    expect(rolesForTrack('cooperative')).toBe(COOP_ROLES)
    expect(roleLabel('sales_officer')).toBe('Sales officer')
    expect(roleLabel('something_else')).toBe('something else')
  })
})

describe('section gating', () => {
  it('admin and unknown role (auth disabled) see the full nav', () => {
    expect(keys(filterNavGroups(coopNav, 'admin', 'cooperative'))).toEqual(keys(coopNav))
    expect(keys(filterNavGroups(coopNav, null, 'cooperative'))).toEqual(keys(coopNav))
  })

  it('hides commerce intake and settlements from a finance officer but keeps finance + buyers/sales', () => {
    const visible = keys(filterNavGroups(coopNav, 'finance_officer', 'cooperative'))
    expect(visible).toEqual(expect.arrayContaining(['payments', 'loans', 'buyers', 'sales', 'settlements', 'sms', 'announcements', 'activity']))
    expect(visible).not.toContain('intake')
    expect(visible).not.toContain('aggregation')
  })

  it('shows a field officer only intake/aggregation plus member context', () => {
    const groups = filterNavGroups(coopNav, 'field_officer', 'cooperative')
    expect(groups.map((group) => group.label)).toEqual(['Operations', 'Commerce'])
    expect(keys(groups)).toEqual(['overview', 'members', 'attendance', 'production', 'intake', 'aggregation'])
  })

  it('shows a sales officer buyers and sales only', () => {
    expect(keys(filterNavGroups(coopNav, 'sales_officer', 'cooperative'))).toEqual(['overview', 'buyers', 'sales'])
  })

  it('restricts a solo-farm supervisor to attendance and redirects there', () => {
    expect(keys(filterNavGroups(soloNav, 'supervisor', 'solo_farm'))).toEqual(['overview', 'attendance'])
    expect(canAccessSection('payroll', 'supervisor', 'solo_farm')).toBe(false)
    expect(canAccessSection('settings', 'supervisor', 'solo_farm')).toBe(true)
    expect(defaultSectionFor('supervisor', 'solo_farm')).toBe('attendance')
    expect(defaultSectionFor('finance_officer', 'cooperative')).toBe('overview')
  })

  it('farm manager cannot see the activity log but the owner can', () => {
    expect(canAccessSection('activity', 'farm_manager', 'solo_farm')).toBe(false)
    expect(canAccessSection('activity', 'farm_owner', 'solo_farm')).toBe(true)
  })

  it('rejects unknown sections', () => {
    expect(canAccessSection('nope', 'admin', 'cooperative')).toBe(false)
  })
})

describe('action gating', () => {
  it('mirrors backend require_roles for member management and SMS', () => {
    expect(can('manageMembers', 'admin')).toBe(true)
    expect(can('manageMembers', 'finance_officer')).toBe(false)
    expect(can('sendSms', 'finance_officer')).toBe(true)
    expect(can('manageIntake', 'operations_officer')).toBe(true)
    expect(can('manageIntake', 'finance_officer')).toBe(false)
    expect(can('disbursePayroll', 'farm_manager')).toBe(false)
    expect(can('disbursePayroll', 'farm_owner')).toBe(true)
    expect(can('manageMembers', null)).toBe(true)
    expect(can('unknownAction', 'admin')).toBe(false)
  })
})
