// src/pages/CompliancePage.jsx
import Footer from '../components/Footer'

const REG_TABLE = [
  { area: 'Data protection', law: 'Data Protection Act, 2012 (Act 843) — Data Protection Commission', note: 'Farmer PII, credit scores, SMS logs' },
  { area: 'Payment services', law: 'Payment Systems and Services Act, 2019 (Act 987) — Bank of Ghana', note: 'AgroOS is not a PSP — it integrates with Moolre, a licensed provider' },
  { area: 'Anti-money laundering', law: 'Anti-Money Laundering Act, 2020 (Act 1044) — FIC', note: 'Applies once real dues, loans, and wallet balances are involved' },
  { area: 'Electronic transactions', law: 'Electronic Transactions Act, 2008 (Act 772)', note: 'Consent and record-keeping for USSD/electronic transactions' },
  { area: 'Telecom / SMS', law: 'Electronic Communications Act, 2008 (Act 775) — NCA', note: 'Sender ID registration, unsolicited messaging rules' },
  { area: 'Cooperative societies', law: 'Co-operatives Societies Act, 2020 (Act 1148)', note: 'Governs cooperative legal structure; AgroOS supports, not replaces, this' },
]

const STATUS_TABLE = [
  { item: 'Data privacy policy documented', status: 'done', label: 'Done' },
  { item: 'Payment webhook signature verification', status: 'done', label: 'Done' },
  { item: 'USSD webhook signature verification', status: 'open', label: 'Open — P0' },
  { item: 'Role-based access control (production)', status: 'partial', label: 'Designed, not enforced' },
  { item: 'Supabase row-level security', status: 'open', label: 'Not yet deployed' },
  { item: 'AML / transaction monitoring', status: 'open', label: 'Not started' },
  { item: 'Legal review of policy', status: 'open', label: 'Outstanding' },
]

function StatusDot({ status }) {
  const color = status === 'done' ? 'var(--g)' : status === 'partial' ? 'var(--gold)' : '#B3462B'
  return (
    <span
      style={{
        display: 'inline-block',
        width: 8,
        height: 8,
        borderRadius: '50%',
        background: color,
        marginRight: 8,
      }}
    />
  )
}

export default function CompliancePage() {
  return (
    <>
      <div className="sol-hero">
        <h1 className="sol-hero-h1 serif">Compliance policy</h1>
        <p className="sol-hero-sub">
          Where AgroOS sits relative to Ghana's data, payments, telecom, and
          cooperative regulations — and what's still outstanding before any
          production launch.
        </p>
      </div>

      <section className="sec">
        <div className="sec-inner" style={{ maxWidth: 820 }}>
          <div
            style={{
              background: 'var(--sage, #EEF3EA)',
              border: '1px solid rgba(0,0,0,.08)',
              borderRadius: 12,
              padding: '18px 22px',
              fontSize: 14,
              lineHeight: 1.7,
              marginBottom: 48,
            }}
          >
            <strong>Draft — hackathon scope (Moolre Startup Cup, July 2026).</strong>{' '}
            This page is a non-legal summary for cooperative administrators,
            partners, and evaluators. It is not legal advice. Before any
            production deployment or onboarding of real farmer data or
            funds, this policy requires review by qualified Ghanaian legal
            counsel and Moolre's compliance team.
          </div>

          <h2 className="sec-h2 serif" id="framework">Regulatory framework</h2>
          <p className="sec-sub" style={{ marginBottom: 24 }}>
            AgroOS touches farmer personal data, cooperative finances, SMS/USSD
            communication, and third-party payment rails — so more than one
            regulatory regime applies.
          </p>

          <div style={{ overflowX: 'auto', marginBottom: 56 }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
              <thead>
                <tr style={{ textAlign: 'left', borderBottom: '2px solid rgba(0,0,0,.1)' }}>
                  <th style={{ padding: '10px 12px' }}>Area</th>
                  <th style={{ padding: '10px 12px' }}>Law / body</th>
                  <th style={{ padding: '10px 12px' }}>Relevance</th>
                </tr>
              </thead>
              <tbody>
                {REG_TABLE.map((row) => (
                  <tr key={row.area} style={{ borderBottom: '1px solid rgba(0,0,0,.06)' }}>
                    <td style={{ padding: '10px 12px', fontWeight: 600 }}>{row.area}</td>
                    <td style={{ padding: '10px 12px', color: 'var(--muted)' }}>{row.law}</td>
                    <td style={{ padding: '10px 12px', color: 'var(--muted)' }}>{row.note}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <h2 className="sec-h2 serif" id="payments">Payment compliance</h2>
          <p className="sec-sub" style={{ marginBottom: 56 }}>
            AgroOS does not hold a Payment Service Provider or e-money
            license and isn't seeking one. All money movement is routed
            through <strong>Moolre</strong>, a licensed payment partner —
            AgroOS never custodies farmer or cooperative funds directly.
            Payment webhooks are HMAC-signature verified as the system of
            record for transaction state. AML/KYC is deferred to Moolre's
            existing flow rather than duplicated in AgroOS.
          </p>

          <h2 className="sec-h2 serif" id="telecom">Telecom & SMS</h2>
          <p className="sec-sub" style={{ marginBottom: 56 }}>
            All outbound SMS uses the Moolre-approved sender ID only.
            Financial or credit-related SMS requires explicit consent —
            cooperative membership alone is not sufficient.
          </p>

          <h2 className="sec-h2 serif" id="status">Current status</h2>
          <p className="sec-sub" style={{ marginBottom: 24 }}>
            Shown plainly, including what isn't done yet.
          </p>

          <div style={{ marginBottom: 56 }}>
            {STATUS_TABLE.map((row) => (
              <div
                key={row.item}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '12px 0',
                  borderBottom: '1px solid rgba(0,0,0,.06)',
                  fontSize: 14,
                }}
              >
                <span>{row.item}</span>
                <span style={{ display: 'flex', alignItems: 'center', color: 'var(--muted)' }}>
                  <StatusDot status={row.status} />
                  {row.label}
                </span>
              </div>
            ))}
          </div>

          <h2 className="sec-h2 serif" id="docs">Related documents</h2>
          <p className="sec-sub" style={{ marginBottom: 12 }}>
            <a
              href="https://github.com/Bempong-Sylvester-Obese/agro-os/blob/main/docs/data-privacy.md"
              target="_blank"
              rel="noreferrer"
              className="footer-link"
              style={{ display: 'inline' }}
            >
              Full data privacy policy →
            </a>
          </p>
          <p className="sec-sub">
            <a
              href="https://github.com/Bempong-Sylvester-Obese/agro-os/blob/main/SECURITY.md"
              target="_blank"
              rel="noreferrer"
              className="footer-link"
              style={{ display: 'inline' }}
            >
              Security policy →
            </a>
          </p>
        </div>
      </section>

      <Footer />
    </>
  )
}
