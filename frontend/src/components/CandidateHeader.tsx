import { Envelope, Phone, MapPin } from './Icons'
import type { ProfileOutput } from '../api/types'

interface CandidateHeaderProps {
  profile: ProfileOutput
}

export function CandidateHeader({ profile }: CandidateHeaderProps) {
  const initials = (profile.full_name || '?')
    .split(' ')
    .map((w) => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)

  const confidenceColor =
    profile.overall_confidence >= 0.8 ? '#16a34a' :
    profile.overall_confidence >= 0.5 ? '#ca8a04' : '#dc2626'

  return (
    <div className="candidate-header">
      <div className="candidate-avatar">{initials}</div>
      <div className="candidate-info">
        <h1 className="candidate-name">{profile.full_name || 'Unknown Candidate'}</h1>
        {profile.headline && <p className="candidate-headline">{profile.headline}</p>}
        {profile.experience?.[0] && (
          <p className="candidate-role">
            {profile.experience[0].title}
            {profile.experience[0].company && ` at ${profile.experience[0].company}`}
          </p>
        )}
        <div className="candidate-meta">
          {profile.emails?.[0] && (
            <span className="meta-item">
              <span className="meta-icon" style={{ display: 'inline-flex', alignItems: 'center' }}>
                <Envelope size={14} />
              </span> {profile.emails[0]}
            </span>
          )}
          {profile.phones?.[0] && (
            <span className="meta-item">
              <span className="meta-icon" style={{ display: 'inline-flex', alignItems: 'center' }}>
                <Phone size={14} />
              </span> {profile.phones[0]}
            </span>
          )}
          {profile.location && (
            <span className="meta-item">
              <span className="meta-icon" style={{ display: 'inline-flex', alignItems: 'center' }}>
                <MapPin size={14} />
              </span> {profile.location}
            </span>
          )}
        </div>
      </div>
      <div className="candidate-confidence" style={{ borderColor: confidenceColor }}>
        <span className="confidence-value" style={{ color: confidenceColor }}>
          {Math.round(profile.overall_confidence * 100)}%
        </span>
        <span className="confidence-label">Confidence</span>
      </div>
    </div>
  )
}
