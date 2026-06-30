import type { JsonArray } from '../api/types'

interface EducationSectionProps {
  education: JsonArray
}

export function EducationSection({ education }: EducationSectionProps) {
  if (!education || education.length === 0) {
    return <div className="section-empty">No education data available</div>
  }

  return (
    <div className="education-list">
      {education.map((entry, idx) => {
        if (typeof entry === 'object' && entry !== null && !Array.isArray(entry)) {
          const e = entry as Record<string, unknown>
          const degree = String(e.degree || '')
          const field = String(e.field || '')
          const school = String(e.school || e.institution || '')
          const start = e.start ? String(e.start) : ''
          const end = e.end ? String(e.end) : ''
          const desc = e.description ? String(e.description) : ''

          let degreeText = degree
          if (field) {
            degreeText = degreeText ? `${degreeText} in ${field}` : field
          }
          if (!degreeText && desc) {
            degreeText = desc
          }

          let dateText = ''
          if (start || end) {
            dateText = `${start || '?'} — ${end || 'Present'}`
          } else if (e.year) {
            dateText = String(e.year)
          }

          return (
            <div key={idx} className="edu-entry" style={{ marginBottom: '12px' }}>
              <h4 className="edu-degree" style={{ margin: '0 0 4px 0', fontSize: '15px', fontWeight: 600 }}>
                {degreeText || 'Education Record'}
              </h4>
              {school && <p className="edu-school" style={{ margin: '0 0 2px 0', opacity: 0.85 }}>{school}</p>}
              {dateText && <p className="edu-year" style={{ margin: 0, fontSize: '12px', opacity: 0.7 }}>{dateText}</p>}
            </div>
          )
        }
        return (
          <div key={idx} className="edu-entry">
            <p>{String(entry)}</p>
          </div>
        )
      })}
    </div>
  )
}
