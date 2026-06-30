import { useEffect, useState } from 'react'
import { fetchWorkflow } from '../api/client'
import { SVGIcon } from './Icons'

interface WorkflowModalProps {
  isOpen: boolean
  onClose: () => void
}

interface Stage {
  id: string
  label: string
  icon: string
  description: string
}

export function WorkflowModal({ isOpen, onClose }: WorkflowModalProps) {
  const [stages, setStages] = useState<Stage[]>([])
  const [visibleCount, setVisibleCount] = useState(0)

  useEffect(() => {
    if (isOpen) {
      fetchWorkflow()
        .then((data) => setStages(data.stages))
        .catch(() => {
          // Fallback stages if API unreachable
          setStages([
            { id: 'upload', label: 'File Upload', icon: '📄', description: 'Resume PDFs, CSVs, JSON exports, and recruiter notes.' },
            { id: 'detection', label: 'Source Detection', icon: '🔍', description: 'Each file is classified by format type.' },
            { id: 'extraction', label: 'Data Extraction', icon: '⚙️', description: 'Deterministic extractors pull fields using regex and heuristics.' },
            { id: 'url_discovery', label: 'URL Discovery', icon: '🔗', description: 'LinkedIn, GitHub, and portfolio URLs are auto-detected.' },
            { id: 'enrichment', label: 'APIFY Enrichment', icon: '🌐', description: 'Profile URLs are scraped for additional data.' },
            { id: 'merge', label: 'Canonical Merge', icon: '🔀', description: 'All evidence is merged with conflict resolution.' },
            { id: 'confidence', label: 'Confidence Scoring', icon: '📊', description: 'Each field receives a corroboration-based score.' },
            { id: 'gemini', label: 'Gemini Insights', icon: '🤖', description: 'AI generates recruiter summaries and recommendations.' },
            { id: 'projection', label: 'Final Profile', icon: '✅', description: 'Profile is projected into the output schema.' },
          ])
        })
    }
  }, [isOpen])

  useEffect(() => {
    if (!isOpen) {
      setVisibleCount(0)
      return
    }
    if (stages.length === 0) return

    const timer = setInterval(() => {
      setVisibleCount((prev) => {
        if (prev >= stages.length) {
          clearInterval(timer)
          return prev
        }
        return prev + 1
      })
    }, 250)

    return () => clearInterval(timer)
  }, [isOpen, stages.length])

  if (!isOpen) return null

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content workflow-modal" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>×</button>
        <h2 className="modal-title">Pipeline Architecture</h2>
        <p className="modal-subtitle">How your candidate data flows through the engine</p>

        <div className="workflow-stages">
          {stages.map((stage, idx) => (
            <div
              key={stage.id}
              className={`wf-stage ${idx < visibleCount ? 'visible' : ''}`}
              style={{ transitionDelay: `${idx * 80}ms` }}
            >
              <div className="wf-icon" style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
                <SVGIcon icon={stage.icon} size={24} />
              </div>
              <div className="wf-info">
                <h4>{stage.label}</h4>
                <p>{stage.description}</p>
              </div>
              {idx < stages.length - 1 && <div className="wf-connector" />}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
