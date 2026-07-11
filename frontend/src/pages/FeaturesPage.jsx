// src/pages/FeaturesPage.jsx
import Footer from '../components/Footer'
import CTASection from '../components/CTASection'
import { Users, Sprout, CreditCard, MessageSquare, Star, Smartphone, Activity, Shield, FileText } from 'lucide-react'

const FEATURES = [
  [<Users size={28} />, 'Member management',        'Full profiles, roles, dues status, and complete history for every farmer. Filter by region, status, or score.'],
  [<Sprout size={28} />, 'Production tracking',      'Log harvests, yields, and crop cycles per member. Build a multi-season data trail for every farm.'],
  [<CreditCard size={28} />, 'Payments & disbursements', 'Collect dues via MoMo, USSD, or card. Run disbursements with full audit trails and automated receipts.'],
  [<MessageSquare size={28} />, 'SMS broadcasts',           'Send targeted announcements to all members or filtered groups — by region, payment status, or custom list.'],
  [<Star size={28} />, 'AgroCredit Trust Score',   'AI-generated creditworthiness scores (0–100) from payment history, production output, and tenure. Updated monthly.'],
  [<Smartphone size={28} />, 'USSD access',              'Native Moolre USSD integration. Farmers with basic phones can pay dues, check balances, and get alerts.'],
  [<Activity size={28} />, 'Analytics dashboard',      'Real-time overview of dues collection, production trends, and member activity across all regions.'],
  [<Shield size={28} />, 'Role-based access',        'Cooperative leaders, field agents, and managers each see exactly what they need — nothing more.'],
  [<FileText size={28} />, 'Audit trails & receipts',  'Every transaction is logged with a timestamped receipt. Export to CSV for financial reporting.'],
]

export default function FeaturesPage({ setPage }) {
  return (
    <>
      <div className="sol-hero">
        <h1 className="sol-hero-h1 serif">Everything your<br />cooperative needs</h1>
        <p className="sol-hero-sub">
          Purpose-built for African farming cooperatives — every feature designed for real conditions on the ground.
        </p>
      </div>

      <section className="sec">
        <div className="sec-inner">
          <div className="feat-grid">
            {FEATURES.map(([icon, title, desc], i) => (
              <div key={title} className="feat-card">
                <div className="feat-num mono">{String(i + 1).padStart(2, '0')}</div>
                <div className="feat-icon">{icon}</div>
                <div className="feat-title serif">{title}</div>
                <div className="feat-desc">{desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <CTASection
        heading="Ready to see it in action?"
        subtext="Try the live dashboard or book a walkthrough with the AgroOS team."
        primaryLabel="Open dashboard"
        secondaryLabel="Book a demo"
        onPrimary={() => setPage('dashboard')}
        onSecondary={() => {}}
      />

      <Footer setPage={setPage} />
    </>
  )
}
