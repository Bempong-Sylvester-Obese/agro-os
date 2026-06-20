// src/components/CTASection.jsx
export default function CTASection({ heading, subtext, primaryLabel, secondaryLabel, onPrimary, onSecondary }) {
  return (
    <div className="cta-sec">
      <h2 className="cta-h2 serif" dangerouslySetInnerHTML={{ __html: heading }} />
      <p className="cta-sub">{subtext}</p>
      <div className="cta-btns">
        <button className="btn-lg" onClick={onPrimary}>{primaryLabel}</button>
        <button className="btn-out-lg" onClick={onSecondary}>{secondaryLabel}</button>
      </div>
    </div>
  )
}
