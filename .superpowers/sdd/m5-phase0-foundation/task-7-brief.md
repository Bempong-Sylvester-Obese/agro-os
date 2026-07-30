### Task 7: Frontend — Org-aware dashboard navigation

**Files:**
- Modify: `frontend/src/constants/routes.js`
- Modify: `frontend/src/pages/DashboardPage.jsx`

**Step 1: Add `workers` to DASHBOARD_SECTIONS**

In `frontend/src/constants/routes.js`, add `'workers'` to the DASHBOARD_SECTIONS array (after `'members'`):

```javascript
export const DASHBOARD_SECTIONS = [
  'overview',
  'members',
  'workers',
  'payments',
  'loans',
  'production',
  'scores',
  'sms',
  'ussd',
  'activity',
  'settings',
]
```

**Step 2: Convert NAV_GROUPS to a function in DashboardPage.jsx**

Replace the existing `NAV_GROUPS` constant (lines 27-57) with:

```javascript
function getNavGroups(organizationType) {
  if (organizationType === 'solo_farm') {
    return [
      {
        label: 'Operations',
        items: [
          { key: 'overview', icon: <BarChart3 size={18} />, label: 'Overview' },
          { key: 'workers', icon: <Users size={18} />, label: 'Workers' },
          { key: 'production', icon: <Tractor size={18} />, label: 'Production' },
        ],
      },
      {
        label: 'Communications',
        items: [
          { key: 'sms', icon: <MessageSquare size={18} />, label: 'SMS broadcasts' },
          { key: 'ussd', icon: <Phone size={18} />, label: 'USSD activity' },
        ],
      },
      {
        label: 'Governance',
        items: [
          { key: 'activity', icon: <ClipboardList size={18} />, label: 'Activity log' },
        ],
      },
    ]
  }
  // Default cooperative nav
  return [
    {
      label: 'Operations',
      items: [
        { key: 'overview', icon: <BarChart3 size={18} />, label: 'Overview' },
        { key: 'members', icon: <Users size={18} />, label: 'Members' },
        { key: 'production', icon: <Tractor size={18} />, label: 'Production' },
        { key: 'scores', icon: <Star size={18} />, label: 'Agro-AI scores' },
      ],
    },
    {
      label: 'Finance',
      items: [
        { key: 'payments', icon: <CreditCard size={18} />, label: 'Payments' },
        { key: 'loans', icon: <Banknote size={18} />, label: 'Loans' },
      ],
    },
    {
      label: 'Communications',
      items: [
        { key: 'sms', icon: <MessageSquare size={18} />, label: 'SMS broadcasts' },
        { key: 'ussd', icon: <Phone size={18} />, label: 'USSD activity' },
      ],
    },
    {
      label: 'Governance',
      items: [
        { key: 'activity', icon: <ClipboardList size={18} />, label: 'Activity log' },
      ],
    },
  ]
}
```

Then replace `const NAV_ITEMS = NAV_GROUPS.flatMap(...)` with:
```javascript
const [organizationType, setOrganizationType] = useState('cooperative')
```
placed in the component body (after the other useState calls).

And add just before the return statement:
```javascript
const navGroups = getNavGroups(organizationType)
const NAV_ITEMS = navGroups.flatMap((group) => group.items)
```

**Step 3: Fetch organization_type from cooperative API**

In the `loadAll` function, after `setCooperative(resolvedCoop)` (line 128), add:
```javascript
if (resolvedCoop?.organization_type) {
  setOrganizationType(resolvedCoop.organization_type)
}
```

**Step 4: Add `workers` to TITLES**

```javascript
workers:  'Workers',
```

Place it after the `members` line.

**Step 5: Add section gating**

After the existing urlSection check (line 182-184), add:
```javascript
if (organizationType === 'solo_farm' && section === 'members') {
  return <Navigate to={dashboardPath('workers')} replace />
}
if (organizationType !== 'solo_farm' && section === 'workers') {
  return <Navigate to={dashboardPath('members')} replace />
}
```

**Step 6: Add Workers section rendering**

In the section rendering block (around line 309-316, after the Members section), add:
```jsx
{section === 'workers' && (
  <Workers cooperativeId={cooperativeId} />
)}
```

And import Workers at the top:
```javascript
import Workers from '../components/dashboard/Workers'
```
