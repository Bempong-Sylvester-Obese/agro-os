import React from 'react'
import Footer from '../components/Footer'
import { useAppNavigate } from '../hooks/useAppNavigate'

const IR_NAV = [
  { id: 'overview', label: 'Overview' },
  { id: 'why-agroos', label: 'Why AgroOS' },
  { id: 'financials', label: 'Financials' },
  { id: 'news-events', label: 'News' },
  { id: 'governance', label: 'Governance' },
  { id: 'resources', label: 'Resources' },
  { id: 'contact', label: 'Contact' },
]

const THESIS_PILLARS = [
  {
    title: 'Market',
    body: 'African agricultural cooperatives manage members, dues, credit, and offtake with fragmented tools. A purpose-built operating system can become the system of record for that economy.',
  },
  {
    title: 'Product',
    body: 'AgroOS unifies membership, production, payments, loans, and market settlement in one cooperative workspace — with farmer access that works on feature phones.',
  },
  {
    title: 'Distribution',
    body: 'Moolre-powered MoMo rails and merchant-code USSD put collections, disbursements, and self-service in the field without requiring a smartphone app.',
  },
  {
    title: 'Credit infrastructure',
    body: 'Operational and repayment history creates trust signals cooperatives and lenders can use — turning day-to-day activity into underwritable data over time.',
  },
]

const FINANCIAL_GROUPS = [
  {
    title: 'Annual reports',
    rows: [
      { period: 'FY 2026', label: 'Annual report', status: 'Not yet published' },
      { period: 'FY 2025', label: 'Annual report', status: 'Not yet published' },
    ],
  },
  {
    title: 'Quarterly updates',
    rows: [
      { period: 'Q2 2026', label: 'Quarterly update', status: 'Not yet published' },
      { period: 'Q1 2026', label: 'Quarterly update', status: 'Not yet published' },
    ],
  },
  {
    title: 'Filings & disclosures',
    rows: [
      { period: '—', label: 'Regulatory filings', status: 'Not yet published' },
      { period: '—', label: 'Shareholder materials', status: 'Not yet published' },
    ],
  },
]

const RESOURCES = [
  {
    title: 'Investor overview',
    body: 'Company overview deck for qualified investors.',
    status: 'Coming soon',
  },
  {
    title: 'Investor FAQ',
    body: 'Answers on stage, market, product scope, and fundraising process.',
    status: 'Coming soon',
  },
  {
    title: 'Media kit',
    body: 'Brand assets and approved company descriptions for press and partners.',
    status: 'Coming soon',
  },
]

export default function InvestorRelationsPage() {
  const setPage = useAppNavigate()

  return (
    <>
      <div className="sol-hero">
        <div className="sol-hero-inner">
          <div className="sol-tag">AgroOS</div>
          <h1 className="sol-hero-h1 serif">Investor relations</h1>
          <p className="sol-hero-sub">
            Information for investors and partners following AgroOS as we build the operating system for African agricultural cooperatives.
          </p>
        </div>
      </div>

      <nav className="ir-subnav" aria-label="Investor relations sections">
        <div className="ir-subnav-inner">
          {IR_NAV.map(item => (
            <a key={item.id} href={`#${item.id}`} className="ir-subnav-link">
              {item.label}
            </a>
          ))}
        </div>
      </nav>

      <section className="sec" id="overview">
        <div className="sec-inner ir-content">
          <div className="ir-disclaimer" role="note">
            <strong>Privately held company.</strong>{' '}
            This page is an investor information hub. No securities are being offered here.
            Financial reports and governance materials will be published in this section as they become available.
          </div>

          <h2 className="sec-h2 serif">Company overview</h2>
          <p className="sec-sub">
            AgroOS is building modern cooperative management for African agriculture — membership,
            production, MoMo payments, credit workflows, and market settlement in one system.
            We are privately held and pre-institutional raise. This hub will host the materials
            investors expect as our disclosures mature.
          </p>
        </div>
      </section>

      <section className="sec bg-sage" id="why-agroos">
        <div className="sec-inner ir-content">
          <h2 className="sec-h2 serif">Why AgroOS</h2>
          <p className="sec-sub" style={{ marginBottom: 32 }}>
            Our investment thesis is qualitative at this stage. We do not publish financial projections or operating metrics on this page.
          </p>
          <div className="ir-pillar-grid">
            {THESIS_PILLARS.map(pillar => (
              <article key={pillar.title} className="ir-pillar">
                <h3 className="ir-pillar-title">{pillar.title}</h3>
                <p className="ir-pillar-body">{pillar.body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="sec" id="financials">
        <div className="sec-inner ir-content">
          <h2 className="sec-h2 serif">Financial information</h2>
          <p className="sec-sub" style={{ marginBottom: 32 }}>
            Reports, updates, and filings will appear here in reverse chronological order when published.
          </p>
          {FINANCIAL_GROUPS.map(group => (
            <div key={group.title} className="ir-archive-block">
              <h3 className="ir-archive-heading">{group.title}</h3>
              <table className="ir-archive">
                <thead>
                  <tr>
                    <th scope="col">Period</th>
                    <th scope="col">Document</th>
                    <th scope="col">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {group.rows.map(row => (
                    <tr key={`${group.title}-${row.period}-${row.label}`} className="ir-empty">
                      <td>{row.period}</td>
                      <td>{row.label}</td>
                      <td>{row.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      </section>

      <section className="sec bg-sage" id="news-events">
        <div className="sec-inner ir-content">
          <h2 className="sec-h2 serif">News and events</h2>
          <p className="sec-sub" style={{ marginBottom: 24 }}>
            Press releases, product milestones, and investor events will be listed here.
          </p>
          <ul className="ir-news-list">
            <li className="ir-news-item">
              <div className="ir-news-meta">2026</div>
              <div>
                <div className="ir-news-title">Moolre Startup Cup</div>
                <p className="ir-news-body">
                  AgroOS is building within the Moolre payments ecosystem for cooperative collections and disbursements in Ghana.
                </p>
              </div>
            </li>
            <li className="ir-news-item ir-empty">
              <div className="ir-news-meta">—</div>
              <div>
                <div className="ir-news-title">Additional releases</div>
                <p className="ir-news-body">No further press releases have been published yet.</p>
              </div>
            </li>
          </ul>
        </div>
      </section>

      <section className="sec" id="governance">
        <div className="sec-inner ir-content">
          <h2 className="sec-h2 serif">Governance</h2>
          <p className="sec-sub" style={{ marginBottom: 28 }}>
            We intend to publish board composition, committee materials, and formal policies as the company matures.
          </p>
          <div className="ir-gov-grid">
            <div className="ir-gov-card">
              <h3 className="ir-archive-heading">Leadership</h3>
              <p className="ir-pillar-body">Board composition — to be announced.</p>
              <p className="ir-pillar-body">Executive leadership profiles will be added here.</p>
            </div>
            <div className="ir-gov-card">
              <h3 className="ir-archive-heading">Principles</h3>
              <ul className="ir-gov-list">
                <li>Protect farmer and cooperative data with clear access controls</li>
                <li>Keep payment flows on licensed rails (Moolre)</li>
                <li>Publish compliance posture openly as we approach production</li>
                <li>Separate product claims from regulated financial activity</li>
              </ul>
            </div>
          </div>
          <p className="sec-sub" style={{ marginTop: 28 }}>
            Related:{' '}
            <a
              href="/compliance"
              className="ir-inline-link"
              onClick={(event) => {
                event.preventDefault()
                setPage('compliance')
              }}
            >
              Compliance policy
            </a>
          </p>
        </div>
      </section>

      <section className="sec bg-sage" id="resources">
        <div className="sec-inner ir-content">
          <h2 className="sec-h2 serif">Resources</h2>
          <p className="sec-sub" style={{ marginBottom: 28 }}>
            Downloadable materials for investors and media will be hosted in this section.
          </p>
          <div className="ir-resource-grid">
            {RESOURCES.map(resource => (
              <article key={resource.title} className="ir-resource">
                <h3 className="ir-pillar-title">{resource.title}</h3>
                <p className="ir-pillar-body">{resource.body}</p>
                <button type="button" className="ir-resource-btn" disabled>
                  {resource.status}
                </button>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="sec" id="contact">
        <div className="sec-inner ir-content">
          <h2 className="sec-h2 serif">Investor contact</h2>
          <p className="sec-sub" style={{ marginBottom: 28 }}>
            For investor inquiries, reach the AgroOS investor relations desk or request a briefing through our enterprise demo flow.
          </p>
          <div className="ir-contact">
            <div>
              <div className="ir-contact-label">Investor relations</div>
              <div className="ir-contact-name">AgroOS Investor Relations</div>
              <a className="ir-inline-link" href="mailto:investors@agroos.app">
                investors@agroos.app
              </a>
              <p className="ir-contact-note">
                Email alerts for filings and news will open when we begin publishing materials on this page.
              </p>
            </div>
            <div className="ir-contact-actions">
              <a
                href="/book-demo?plan=enterprise&topic=Enterprise+implementation"
                className="btn-lg"
                onClick={(event) => {
                  event.preventDefault()
                  setPage('bookDemo', { plan: 'enterprise', topic: 'Enterprise implementation' })
                }}
              >
                Request investor briefing
              </a>
              <a className="btn-out-lg" href="mailto:investors@agroos.app">
                Email IR
              </a>
            </div>
          </div>
        </div>
      </section>

      <Footer />
    </>
  )
}
