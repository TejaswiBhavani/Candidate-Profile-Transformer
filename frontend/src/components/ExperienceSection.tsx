import type { ExperienceEntry } from '../api/types'

interface ExperienceSectionProps {
  experience: ExperienceEntry[]
}

export function ExperienceSection({ experience }: ExperienceSectionProps) {
  if (!experience || experience.length === 0) {
    return <div className="section-empty">No experience data available</div>
  }

  return (
    <div className="experience-timeline">
      {experience.map((exp, idx) => (
        <div key={idx} className="exp-entry">
          <div className="exp-dot" />
          <div className="exp-content">
            <h4 className="exp-title">{exp.title || 'Untitled Role'}</h4>
            <p className="exp-company">{exp.company || 'Unknown Company'}</p>
            {(exp.start || exp.end) && (
              <p className="exp-dates">
                {exp.start || '?'} — {exp.end || 'Present'}
              </p>
            )}
            {exp.summary && <p className="exp-summary">{exp.summary}</p>}
          </div>
        </div>
      ))}
    </div>
  )
}
