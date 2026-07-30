### Task 6: Frontend — Org-aware signup flow

**Files:**
- Modify: `frontend/src/api/auth.js`
- Modify: `frontend/src/pages/AuthPage.jsx`

**Goal:** Add `organization_type` (cooperative | solo_farm) to the signup flow so users choose their org type during registration.

**Step 1: Update `signupAdmin` to pass organization_type**

In `frontend/src/api/auth.js`, the `signupAdmin` function (line 60-78) sends the POST body. Add `organization_type` to its params:

```javascript
export async function signupAdmin({
  email,
  password,
  cooperative_name,
  location,
  member_count,
  subscription_plan,
  onboarding_role,
  organization_type,
}) {
  return authFetch('/auth/signup', {
    email,
    password,
    cooperative_name,
    location: location || null,
    member_count: member_count ?? null,
    subscription_plan: subscription_plan || 'starter',
    onboarding_role: onboarding_role || null,
    organization_type: organization_type || 'cooperative',
  }, { retries: 0 })
}
```

**Step 2: Update `signup` wrapper to pass organizationType**

In the same file, the `signup` function (line 88-110) wraps `signupAdmin`. Add `organizationType` to its destructured params and pass it:

```javascript
export async function signup({
  email,
  password,
  cooperativeName,
  location,
  memberCount,
  subscriptionPlan,
  onboardingRole,
  organizationType,
}) {
  const data = await signupAdmin({
    email,
    password,
    cooperative_name: cooperativeName,
    location,
    member_count: memberCount ? parseInt(memberCount, 10) : null,
    subscription_plan: subscriptionPlan,
    onboarding_role: onboardingRole,
    organization_type: organizationType || 'cooperative',
  })
  return {
    ...data,
    user: userFromSignupResponse(data, email),
  }
}
```

**Step 3: Add org type selector to signup step 0 in AuthPage.jsx**

In `frontend/src/pages/AuthPage.jsx`:

Add a state variable after `subscriptionIntent` (line 148):
```javascript
const [organizationType, setOrganizationType] = useState('cooperative')
```

In step 0 of the signup form (the cooperative info step, around line 300-400 where the cooperative name field is), add a "Organization type" dropdown. After the cooperative name field:

```jsx
<div className="form-group">
  <label htmlFor="org-type">Organization type</label>
  <div style={{ position: 'relative' }}>
    <Building2 size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--muted)' }} />
    <select
      id="org-type"
      className="auth-input"
      value={organizationType}
      onChange={e => setOrganizationType(e.target.value)}
      style={{
        width: '100%',
        padding: '11px 12px 11px 38px',
        border: '1.5px solid var(--border)',
        borderRadius: 8,
        fontSize: 14,
        fontFamily: "'DM Sans', sans-serif",
        background: '#fff',
        color: 'var(--text)',
        outline: 'none',
        appearance: 'auto',
      }}
    >
      <option value="cooperative">Cooperative</option>
      <option value="solo_farm">Solo Farm</option>
    </select>
  </div>
</div>
```

In the `handleSignup` call (line 233-241), add `organizationType`:
```javascript
const data = await signup({
  email: signupEmail,
  password: signupPassword,
  cooperativeName,
  location: location || undefined,
  memberCount: memberCount || undefined,
  subscriptionPlan: subscriptionIntent?.plan || 'starter',
  onboardingRole: subscriptionIntent?.role || 'Cooperative administrator',
  organizationType,
})
```

**Step 4: Verify**
No formal tests for this — just verify the file parses: from the frontend dir, `node -e "require('./src/api/auth.js')"` or just check for syntax errors with a linter.
