import { useState } from 'react'
import './App.css'
import { runPipeline } from './api/client'
import type { PipelineResponse } from './api/types'
import { DropZone } from './components/DropZone'
import { PipelineAnimation } from './components/PipelineAnimation'
import { CandidateHeader } from './components/CandidateHeader'
import { SkillsSection } from './components/SkillsSection'
import { ExperienceSection } from './components/ExperienceSection'
import { EducationSection } from './components/EducationSection'
import { LinksSection } from './components/LinksSection'
import { InsightsSection } from './components/InsightsSection'
import { TechAccordion } from './components/TechAccordion'
import { WorkflowModal } from './components/WorkflowModal'
import { Lightning, Search, Tools, Briefcase, Graduation, Link, Robot, Warning } from './components/Icons'

function App() {
  const [files, setFiles] = useState<File[]>([])
  const [result, setResult] = useState<PipelineResponse | null>(null)
  const [selectedCandidateIndex, setSelectedCandidateIndex] = useState(0)
  const [isRunning, setIsRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showWorkflow, setShowWorkflow] = useState(false)

  const onAnalyze = async () => {
    if (files.length === 0) {
      setError('Please upload at least one candidate file.')
      return
    }
    setIsRunning(true)
    setError(null)
    setResult(null)
    setSelectedCandidateIndex(0)
    try {
      const data = await runPipeline(files)
      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed')
    } finally {
      setIsRunning(false)
    }
  }

  const onReset = () => {
    setFiles([])
    setResult(null)
    setError(null)
    setSelectedCandidateIndex(0)
  }

  const downloadJson = () => {
    const selectedCandidate = result?.candidate_outputs?.[selectedCandidateIndex]
    const payload = selectedCandidate?.output || result?.output
    if (!payload) return
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `candidate_profile_${payload.candidate_id || 'output'}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const showInput = !result
  const selectedCandidate = result?.candidate_outputs?.[selectedCandidateIndex]
  const profile = selectedCandidate?.output || result?.output
  const profileWarnings = selectedCandidate?.warnings || result?.warnings || []
  const profileCanonical = selectedCandidate?.canonical || result?.canonical
  const candidateOutputs = result?.candidate_outputs || []
  const hasCandidateBatch = candidateOutputs.length > 1

  return (
    <main className="app-shell">
      {/* Navigation Bar */}
      <nav className="navbar">
        <div className="nav-brand" onClick={onReset} style={{ cursor: 'pointer' }}>
          <span className="nav-logo" style={{ display: 'inline-flex', alignItems: 'center' }}>
            <Lightning size={24} />
          </span>
          <span className="nav-title">Candidate Profile Transformer</span>
        </div>
        <div className="nav-actions">
          <button className="btn-outline" onClick={() => setShowWorkflow(true)}>
            View Workflow
          </button>
          {result && (
            <>
              <button className="btn-outline" onClick={downloadJson}>
                Download JSON
              </button>
              <button className="btn-primary" onClick={onReset}>
                New Analysis
              </button>
            </>
          )}
        </div>
      </nav>

      {/* Processing Animation Overlay */}
      <PipelineAnimation isRunning={isRunning} />

      {/* Workflow Modal */}
      <WorkflowModal isOpen={showWorkflow} onClose={() => setShowWorkflow(false)} />

      {/* ========== INPUT SCREEN ========== */}
      {showInput && !isRunning && (
        <section className="input-screen">
          <div className="input-hero">
            <h1>Analyze a Candidate</h1>
            <p>Upload resumes, recruiter spreadsheets, ATS exports, or notes to build a unified candidate profile.</p>
          </div>

          <DropZone files={files} onChange={setFiles} />

          {error && <p className="error-text">{error}</p>}

          <button
            className="btn-analyze"
            onClick={onAnalyze}
            disabled={files.length === 0 || isRunning}
          >
            {isRunning ? 'Analyzing...' : (
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
                <Search size={16} /> Analyze Candidate
              </span>
            )}
          </button>
        </section>
      )}

      {/* ========== OUTPUT SCREEN ========== */}
      {profile && (
        <section className="output-screen">
          {hasCandidateBatch && (
            <div className="profile-card full-width">
              <h3 className="card-title" style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
                <Search size={20} /> CSV Candidates
              </h3>
              <div className="candidate-switcher">
                {candidateOutputs.map((candidate, index) => {
                  const candidateProfile = candidate.output
                  const isActive = index === selectedCandidateIndex
                  return (
                    <button
                      key={candidate.source_id || index}
                      type="button"
                      className={`candidate-switcher-card ${isActive ? 'active' : ''}`}
                      onClick={() => setSelectedCandidateIndex(index)}
                    >
                      <span className="candidate-switcher-name">
                        {candidateProfile?.full_name || candidate.source_id}
                      </span>
                      <span className="candidate-switcher-meta">
                        {candidateProfile?.headline || candidateProfile?.experience?.[0]?.title || 'Candidate'}
                      </span>
                      <span className="candidate-switcher-confidence">
                        {candidateProfile ? Math.round(candidateProfile.overall_confidence * 100) : 0}%
                      </span>
                    </button>
                  )
                })}
              </div>
            </div>
          )}

          {/* Candidate Header */}
          <CandidateHeader profile={profile} />

          {/* Content Grid */}
          <div className="profile-grid">
            {/* Skills */}
            <div className="profile-card">
              <h3 className="card-title" style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
                <Tools size={20} /> Skills
              </h3>
              <SkillsSection skills={profile.skills} />
            </div>

            {/* Experience */}
            <div className="profile-card">
              <h3 className="card-title" style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
                <Briefcase size={20} /> Experience
              </h3>
              <ExperienceSection experience={profile.experience} />
            </div>

            {/* Education */}
            <div className="profile-card">
              <h3 className="card-title" style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
                <Graduation size={20} /> Education
              </h3>
              <EducationSection education={profile.education} />
            </div>

            {/* Links */}
            <div className="profile-card">
              <h3 className="card-title" style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
                <Link size={20} /> Links
              </h3>
              <LinksSection
                urls={result.discovered_urls}
                enrichmentStatus={result.enrichment_status}
              />
            </div>
          </div>

          {/* Gemini Insights */}
          <div className="profile-card full-width">
            <h3 className="card-title" style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
              <Robot size={20} /> Recruiter AI Insights
            </h3>
            <InsightsSection insights={result.gemini_insights} />
          </div>

          {/* Warnings */}
          {result.warnings.length > 0 && (
            <div className="profile-card full-width warnings-card">
              <h3 className="card-title" style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
                <Warning size={20} /> Warnings
              </h3>
              <ul className="warnings-list">
                {result.warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Technical Details (Collapsed) */}
          <TechAccordion
            canonical={profileCanonical}
            output={profile as any}
            warnings={profileWarnings}
            provenance={profile.provenance || []}
          />
        </section>
      )}
    </main>
  )
}

export default App
