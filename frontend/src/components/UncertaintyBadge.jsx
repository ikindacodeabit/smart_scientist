import { useState } from 'react'

export default function UncertaintyBadge({ uncertainty }) {
  const [expanded, setExpanded] = useState(false)

  const conf        = uncertainty.overall_confidence
  const pillClass   = `confidence-pill confidence-pill--${conf}`
  const hasConflicts = uncertainty.has_conflicting_evidence && uncertainty.conflicts?.length > 0
  const hasGaps      = uncertainty.gaps?.length > 0

  return (
    <div className="uncertainty-badge">
      <button
        className="uncertainty-trigger"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
      >
        <span className={pillClass}>{conf.toUpperCase()}</span>
        <span className="uncertainty-summary-text">{uncertainty.summary}</span>
        <span className={`uncertainty-chevron${expanded ? ' uncertainty-chevron--open' : ''}`}>
          ▾
        </span>
      </button>

      {expanded && (
        <div className="uncertainty-details">
          <div className="uncertainty-detail-section">
            <h4>Evidence</h4>
            <p>{uncertainty.evidence_count} relevant papers used.</p>
          </div>

          {hasConflicts && (
            <div className="uncertainty-detail-section">
              <h4>Conflicts</h4>
              <ul>
                {uncertainty.conflicts.map((c, i) => (
                  <li key={i}>{c}</li>
                ))}
              </ul>
            </div>
          )}

          {uncertainty.evidence_age_flag && uncertainty.age_note && (
            <div className="uncertainty-detail-section">
              <h4>Evidence Age</h4>
              <p>{uncertainty.age_note}</p>
            </div>
          )}

          {hasGaps && (
            <div className="uncertainty-detail-section">
              <h4>Gaps</h4>
              <ul>
                {uncertainty.gaps.map((g, i) => (
                  <li key={i}>{g}</li>
                ))}
              </ul>
            </div>
          )}

          {uncertainty.low_confidence_flag && (
            <div className="uncertainty-detail-section">
              <h4>Hedging</h4>
              <p>
                Synthesis contains {uncertainty.hedge_count} hedging phrase
                {uncertainty.hedge_count !== 1 ? 's' : ''}, indicating limited certainty.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
