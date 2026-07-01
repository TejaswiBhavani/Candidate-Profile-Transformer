import type { SkillEntry } from '../api/types'
import { Tooltip } from './Tooltip'

interface SkillsSectionProps {
  skills: SkillEntry[]
}

function confidenceColor(c: number): string {
  if (c >= 0.8) return '#16a34a'
  if (c >= 0.5) return '#ca8a04'
  return '#dc2626'
}

export function SkillsSection({ skills }: SkillsSectionProps) {
  const skillsArray = Array.isArray(skills) ? skills : (skills ? [skills] : [])
  if (skillsArray.length === 0) {
    return <div className="section-empty">No skills detected</div>
  }

  return (
    <div className="skills-grid">
      {skillsArray.map((skill, idx) => {
        if (typeof skill === 'string') {
          return (
            <div key={idx} className="skill-chip">
              <span className="skill-name">{skill}</span>
              <span className="skill-confidence-wrap">
                <span
                  className="skill-conf"
                  style={{ background: confidenceColor(0.5) }}
                  title="50% confidence (parsed as string)"
                >
                  50%
                </span>
                <Tooltip text="This skill was parsed as plain text, so it gets a neutral 50% score until it is corroborated by additional sources or normalized to a canonical skill name." />
              </span>
            </div>
          )
        }
        
        return (
          <div key={idx} className="skill-chip">
            <span className="skill-name">{skill.name}</span>
            <span className="skill-confidence-wrap">
              <span
                className="skill-conf"
                style={{ background: confidenceColor(skill.confidence || 0) }}
                title={`${Math.round((skill.confidence || 0) * 100)}% confidence from ${(skill.sources || []).join(', ')}`}
              >
                {Math.round((skill.confidence || 0) * 100)}%
              </span>
              <Tooltip text="Skill confidence is based on corroboration: the same normalized skill appearing from more sources scores higher. Structured sources and canonical skill matches get a small boost; unrecognized spellings get a slight haircut." />
            </span>
          </div>
        )
      })}
    </div>
  )
}
