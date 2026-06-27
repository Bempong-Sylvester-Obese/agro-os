// src/components/dashboard/Scores.jsx
import { SCORES } from '../../data/payments'

export default function Scores() {
  return (
    <>
      <div className="info-banner">
        <strong>About AgroCredit scores</strong> — AI-generated creditworthiness scores (0–100) built from each
        member's payment history, production output, cooperative tenure, and dues consistency. Updated monthly.
      </div>

      <div className="admin-card">
        <div className="admin-card-head">
          <span className="admin-card-title serif">Member trust scores</span>
        </div>
        <div className="sc-head">
          {['Member','Payment','Production','Tenure','Score'].map(h => (
            <span key={h} className="pt-lbl">{h}</span>
          ))}
        </div>
        {SCORES.map(([name, region, pay, prod, ten, score, tier]) => (
          <div key={name} className="sc-row">
            <div>
              <div className="pt-name">{name}</div>
              <div className="pt-id">{region}</div>
            </div>
            <span className="pt-m mono" style={{ fontSize: 11 }}>{pay}</span>
            <span className="pt-m mono" style={{ fontSize: 11 }}>{prod}</span>
            <span className="pt-m mono" style={{ fontSize: 11 }}>{ten}</span>
            <span className={`score-bdg ${tier}`}>{score}</span>
          </div>
        ))}
      </div>
    </>
  )
}
