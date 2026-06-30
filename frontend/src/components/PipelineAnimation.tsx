import { useEffect, useState } from 'react'
import { SVGIcon } from './Icons'

const STAGES = [
  { icon: '📄', label: 'Uploading Files' },
  { icon: '🔍', label: 'Source Detection' },
  { icon: '⚙️', label: 'Data Extraction' },
  { icon: '🔗', label: 'URL Discovery' },
  { icon: '🌐', label: 'APIFY Enrichment' },
  { icon: '🔀', label: 'Canonical Merge' },
  { icon: '📊', label: 'Confidence Scoring' },
  { icon: '🤖', label: 'Gemini Insights' },
  { icon: '✅', label: 'Building Profile' },
]

interface PipelineAnimationProps {
  isRunning: boolean
}

export function PipelineAnimation({ isRunning }: PipelineAnimationProps) {
  const [activeStage, setActiveStage] = useState(0)

  useEffect(() => {
    if (!isRunning) {
      setActiveStage(0)
      return
    }

    const interval = setInterval(() => {
      setActiveStage((prev) => {
        if (prev >= STAGES.length - 1) return prev
        return prev + 1
      })
    }, 600)

    return () => clearInterval(interval)
  }, [isRunning])

  if (!isRunning) return null

  return (
    <div className="pipeline-anim-overlay">
      <div className="pipeline-anim-card">
        <h2 className="pipeline-anim-title">Analyzing Candidate</h2>
        <div className="pipeline-anim-stages">
          {STAGES.map((stage, idx) => (
            <div
              key={idx}
              className={`pipeline-anim-stage ${
                idx < activeStage ? 'done' : idx === activeStage ? 'active' : 'pending'
              }`}
            >
              <span className="stage-icon" style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
                <SVGIcon icon={stage.icon} size={18} />
              </span>
              <span className="stage-label">{stage.label}</span>
              {idx < activeStage && <span className="stage-check">✓</span>}
              {idx === activeStage && <span className="stage-spinner" />}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
