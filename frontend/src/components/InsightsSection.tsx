import { Robot, Pencil, Muscle, Target, Warning, Flag } from './Icons'

interface InsightsSectionProps {
  insights: {
    summary?: string
    recruiter_summary?: string
    strengths: string[]
    recommended_roles: string[]
    missing_information?: string[]
    missing_info?: string[]
    potential_concerns?: string[]
    concerns?: string[]
  } | null
}

export function InsightsSection({ insights }: InsightsSectionProps) {
  if (!insights) {
    return (
      <div className="insights-empty">
        <span className="insights-empty-icon" style={{ display: 'inline-flex', alignItems: 'center' }}>
          <Robot size={48} />
        </span>
        <p>AI insights unavailable — set GEMINI_API_KEY in .env to enable recruiter analysis.</p>
      </div>
    )
  }

  const summary = insights.summary || insights.recruiter_summary || ''
  const strengths = insights.strengths || []
  const recommendedRoles = insights.recommended_roles || []
  const missingInfo = insights.missing_information || insights.missing_info || []
  const concerns = insights.potential_concerns || insights.concerns || []

  return (
    <div className="insights-grid">
      <div className="insight-card summary-card">
        <h4 style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
          <Pencil size={16} /> Recruiter Summary
        </h4>
        <p>{summary || 'No summary generated.'}</p>
      </div>

      <div className="insight-card">
        <h4 style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
          <Muscle size={16} /> Strengths
        </h4>
        {strengths.length > 0 ? (
          <ul>
            {strengths.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        ) : (
          <p className="insight-empty-text">No strengths identified.</p>
        )}
      </div>

      <div className="insight-card">
        <h4 style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
          <Target size={16} /> Recommended Roles
        </h4>
        {recommendedRoles.length > 0 ? (
          <div className="role-chips">
            {recommendedRoles.map((r, i) => (
              <span key={i} className="role-chip">{r}</span>
            ))}
          </div>
        ) : (
          <p className="insight-empty-text">No specific roles recommended.</p>
        )}
      </div>

      <div className="insight-card">
        <h4 style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
          <Warning size={16} /> Missing Information
        </h4>
        {missingInfo.length > 0 ? (
          <ul>
            {missingInfo.map((m, i) => (
              <li key={i}>{m}</li>
            ))}
          </ul>
        ) : (
          <p className="insight-empty-text">No missing information noted.</p>
        )}
      </div>

      <div className="insight-card concern-card">
        <h4 style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
          <Flag size={16} /> Potential Concerns
        </h4>
        {concerns.length > 0 ? (
          <ul>
            {concerns.map((c, i) => (
              <li key={i}>{c}</li>
            ))}
          </ul>
        ) : (
          <p className="insight-empty-text">No potential concerns noted.</p>
        )}
      </div>
    </div>
  )
}
