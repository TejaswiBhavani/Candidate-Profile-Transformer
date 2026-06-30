import type { SkillEntry } from '../api/types'

interface SkillsSectionProps {
  skills: SkillEntry[]
}

function confidenceColor(c: number): string {
  if (c >= 0.8) return '#16a34a'
  if (c >= 0.5) return '#ca8a04'
  return '#dc2626'
}

export function SkillsSection({ skills }: SkillsSectionProps) {
  if (!skills || skills.length === 0) {
    return <div className="section-empty">No skills detected</div>
  }

  return (
    <div className="skills-grid">
      {skills.map((skill, idx) => (
        <div key={idx} className="skill-chip">
          <span className="skill-name">{skill.name}</span>
          <span
            className="skill-conf"
            style={{ background: confidenceColor(skill.confidence) }}
            title={`${Math.round(skill.confidence * 100)}% confidence from ${skill.sources.join(', ')}`}
          >
            {Math.round(skill.confidence * 100)}%
          </span>
        </div>
      ))}
    </div>
  )
}
