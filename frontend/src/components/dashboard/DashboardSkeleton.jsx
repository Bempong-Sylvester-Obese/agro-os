/** Shimmer skeleton primitives for dashboard loading states. */

export function Skeleton({ width = '100%', height = 14, radius = 6, style = {}, className = '' }) {
  return (
    <span
      className={`dash-skeleton ${className}`.trim()}
      style={{ width, height, borderRadius: radius, display: 'block', ...style }}
      aria-hidden="true"
    />
  )
}

export function SkeletonStatCards({ count = 4 }) {
  return (
    <div className={count === 3 ? 'pay-stats' : 'stat-row'}>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="stat-card">
          <Skeleton width="55%" height={10} radius={4} />
          <Skeleton width="70%" height={28} radius={8} style={{ marginTop: 12 }} />
          <Skeleton width="85%" height={10} radius={4} style={{ marginTop: 10 }} />
        </div>
      ))}
    </div>
  )
}

function SkeletonCardShell({ titleWidth = '40%', actionWidth = '18%', children }) {
  return (
    <div className="admin-card">
      <div className="admin-card-head">
        <Skeleton width={titleWidth} height={16} radius={6} />
        <Skeleton width={actionWidth} height={12} radius={4} />
      </div>
      {children}
    </div>
  )
}

export function SkeletonTableRows({ rows = 5, columns = 5, gridStyle }) {
  const colWidths = ['72%', '55%', '48%', '42%', '36%'].slice(0, columns)
  return (
    <>
      <div className="pt-head" style={gridStyle}>
        {colWidths.map((w, i) => (
          <Skeleton key={i} width={w} height={10} radius={4} />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, row) => (
        <div key={row} className="pt-row" style={gridStyle}>
          <div>
            <Skeleton width="68%" height={13} radius={5} />
            <Skeleton width="38%" height={10} radius={4} style={{ marginTop: 6 }} />
          </div>
          {colWidths.slice(1).map((w, i) => (
            <Skeleton key={i} width={w} height={12} radius={4} />
          ))}
        </div>
      ))}
    </>
  )
}

export function SkeletonToolbar({ withFilter = false }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20, gap: 12 }}>
      <div style={{ display: 'flex', gap: 10, flex: 1 }}>
        <Skeleton width="100%" height={38} radius={8} style={{ maxWidth: 380 }} />
        {withFilter && <Skeleton width={88} height={38} radius={7} />}
      </div>
      <Skeleton width={130} height={36} radius={8} />
    </div>
  )
}

export function OverviewSkeleton() {
  return (
    <>
      <SkeletonStatCards count={4} />
      <div className="admin-grid">
        <SkeletonCardShell titleWidth="38%">
          <SkeletonTableRows rows={5} columns={5} />
        </SkeletonCardShell>
        <SkeletonCardShell titleWidth="48%">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="score-item" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '14px 20px' }}>
              <div style={{ flex: 1 }}>
                <Skeleton width="62%" height={13} radius={5} />
                <Skeleton width="78%" height={10} radius={4} style={{ marginTop: 6 }} />
              </div>
              <Skeleton width={36} height={28} radius={8} />
            </div>
          ))}
        </SkeletonCardShell>
      </div>
      <div className="admin-card" style={{ marginTop: 20 }}>
        <div className="admin-card-head">
          <Skeleton width="42%" height={16} radius={6} />
          <Skeleton width="22%" height={12} radius={4} />
        </div>
        <div className="review-grid" style={{ padding: 20 }}>
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="review-card" style={{ padding: 16 }}>
              <Skeleton width="55%" height={14} radius={5} />
              <Skeleton width="90%" height={10} radius={4} style={{ marginTop: 10 }} />
              <Skeleton width="75%" height={10} radius={4} style={{ marginTop: 8 }} />
            </div>
          ))}
        </div>
      </div>
    </>
  )
}

export function TableSectionSkeleton({ statCount = 3, rows = 6, columns = 5, showToolbar = true, gridStyle }) {
  return (
    <>
      {showToolbar && (
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 20 }}>
          <Skeleton width={140} height={36} radius={8} />
        </div>
      )}
      <SkeletonStatCards count={statCount} />
      <SkeletonCardShell>
        <SkeletonTableRows rows={rows} columns={columns} gridStyle={gridStyle} />
      </SkeletonCardShell>
    </>
  )
}

export function MembersSkeleton() {
  return (
    <>
      <SkeletonToolbar withFilter />
      <SkeletonCardShell titleWidth="32%">
        <div style={{ padding: '10px 20px', borderBottom: '1px solid var(--border)' }}>
          <Skeleton width="28%" height={10} radius={4} />
        </div>
        <SkeletonTableRows rows={7} columns={6} gridStyle={{ gridTemplateColumns: '2fr 1fr 1fr 1fr 90px 80px' }} />
      </SkeletonCardShell>
    </>
  )
}

export function ScoresSkeleton() {
  return (
    <>
      <div className="info-banner" style={{ marginBottom: 20 }}>
        <Skeleton width="92%" height={12} radius={4} />
        <Skeleton width="78%" height={12} radius={4} style={{ marginTop: 8 }} />
      </div>
      <div className="score-layout">
        <SkeletonCardShell titleWidth="50%">
          <SkeletonTableRows rows={6} columns={4} gridStyle={{ gridTemplateColumns: '2fr 1fr 90px 60px' }} />
        </SkeletonCardShell>
        <div className="admin-card">
          <div className="admin-card-head">
            <Skeleton width="45%" height={16} radius={6} />
          </div>
          <div style={{ padding: 24 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 24 }}>
              <Skeleton width={64} height={64} radius={12} />
              <div style={{ flex: 1 }}>
                <Skeleton width="55%" height={18} radius={6} />
                <Skeleton width="40%" height={11} radius={4} style={{ marginTop: 8 }} />
              </div>
              <Skeleton width={48} height={48} radius={10} />
            </div>
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} style={{ marginBottom: 16 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                  <Skeleton width="38%" height={11} radius={4} />
                  <Skeleton width="12%" height={11} radius={4} />
                </div>
                <Skeleton width="100%" height={8} radius={4} />
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  )
}

export function SettingsSkeleton() {
  return (
    <div style={{ maxWidth: 800 }}>
      <div className="admin-card">
        <div className="admin-card-head" style={{ borderBottom: '1px solid var(--border)', padding: '24px 28px' }}>
          <div>
            <Skeleton width={220} height={20} radius={6} />
            <Skeleton width={320} height={12} radius={4} style={{ marginTop: 10 }} />
          </div>
        </div>
        <div style={{ padding: 28, display: 'flex', flexDirection: 'column', gap: 20 }}>
          <div>
            <Skeleton width={120} height={14} radius={4} style={{ marginBottom: 14 }} />
            <div style={{ display: 'flex', gap: 16, marginBottom: 16 }}>
              <Skeleton height={42} radius={8} style={{ flex: 2 }} />
              <Skeleton height={42} radius={8} style={{ flex: 1 }} />
            </div>
            <Skeleton width="100%" height={80} radius={8} />
          </div>
          <Skeleton width="100%" height={1} radius={0} />
          <div>
            <Skeleton width={160} height={14} radius={4} style={{ marginBottom: 10 }} />
            <Skeleton width="90%" height={11} radius={4} style={{ marginBottom: 16 }} />
            <div style={{ display: 'flex', gap: 16 }}>
              <Skeleton height={42} radius={8} style={{ flex: 1 }} />
              <Skeleton height={42} radius={8} style={{ flex: 2 }} />
            </div>
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
            <Skeleton width={130} height={42} radius={8} />
          </div>
        </div>
      </div>
    </div>
  )
}

export function SMSLogsSkeleton() {
  return (
    <>
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="sms-row" style={{ padding: '16px 20px' }}>
          <Skeleton width="88%" height={13} radius={5} />
          <div style={{ display: 'flex', gap: 16, marginTop: 10 }}>
            <Skeleton width={56} height={10} radius={4} />
            <Skeleton width={72} height={10} radius={4} />
            <Skeleton width={48} height={20} radius={6} />
          </div>
        </div>
      ))}
    </>
  )
}

export function USSDLogsSkeleton() {
  return (
    <>
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="mt-row mt-row-4">
          <Skeleton width="78%" height={12} radius={4} />
          <Skeleton width="55%" height={12} radius={4} />
          <Skeleton width="90%" height={12} radius={4} />
          <Skeleton width="48%" height={12} radius={4} />
        </div>
      ))}
    </>
  )
}

export function SidebarCoopSkeleton() {
  return <Skeleton width={120} height={10} radius={4} style={{ marginTop: 4 }} />
}

export function DashboardGateSkeleton() {
  return (
    <div className="admin-shell">
      <div className="admin-side">
        <div className="admin-side-head">
          <Skeleton width={80} height={14} radius={6} />
          <SidebarCoopSkeleton />
        </div>
        <div className="admin-nav" style={{ padding: '8px 12px' }}>
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} width="88%" height={34} radius={8} style={{ margin: '6px 0' }} />
          ))}
        </div>
      </div>
      <div className="admin-main">
        <div className="admin-topbar">
          <Skeleton width={160} height={22} radius={6} />
        </div>
        <div className="admin-content">
          <OverviewSkeleton />
        </div>
      </div>
    </div>
  )
}
