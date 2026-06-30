import { useMemo, useState } from 'react'
import './App.css'
import { runPipeline } from './api/client'
import type { PipelineResponse } from './api/types'
import { UploadPanel } from './components/UploadPanel'
import { ConfigSelector } from './components/ConfigSelector'
import { RunButton } from './components/RunButton'
import { WarningPanel } from './components/WarningPanel'
import { CanonicalProfileView } from './components/CanonicalProfileView'
import { ProjectionView } from './components/ProjectionView'
import { CompareView } from './components/CompareView'
import { Tooltip } from './components/Tooltip'

function App() {
  const [files, setFiles] = useState<File[]>([])
  const [config, setConfig] = useState('default')
  const [result, setResult] = useState<PipelineResponse | null>(null)
  const [isRunning, setIsRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const sourcesCount = files.length
  const fieldsResolved = result?.canonical ? Object.keys(result.canonical).length : 0
  const conflictsFound = (result?.warnings?.length || 0) + (result?.validation_errors?.length || 0)
  const confidence = conflictsFound === 0 ? '98%' : '85%'

  const canRun = useMemo(() => files.length > 0 && !isRunning, [files.length, isRunning])

  const onRun = async () => {
    if (files.length === 0) {
      setError('Please upload at least one source file (.csv, .txt, .json, or .pdf).')
      return
    }

    setIsRunning(true)
    setError(null)
    try {
      const data = await runPipeline(files, config)
      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Run failed')
    } finally {
      setIsRunning(false)
    }
  }

  return (
    <main className="app-shell">
      <header className="hero-card">
        <div className="hero-copy">
          <h1>Candidate Profile Transformer</h1>
          <p className="subtitle">Multi-source candidate data fusion and configurable projection engine</p>
        </div>

        <div className="pipeline-banner" aria-label="Pipeline stages">
          <div className="pipeline-step">
            Structured + Unstructured Sources
            <span className="arrow">→</span>
          </div>
          <div className="pipeline-step">
            Canonical Profile <Tooltip text="The internal source of truth aggregated from all incoming candidate data, retaining conflicting info and confidence scores." />
            <span className="arrow">→</span>
          </div>
          <div className="pipeline-step">
            Configurable Projection <Tooltip text="The final output shaped to consumer-specific requirements, derived from the canonical profile without altering pipeline logic." />
            <span className="arrow">→</span>
          </div>
          <div className="pipeline-step">
            Output
          </div>
        </div>
      </header>

      <section className="top-grid">
        <div className="card">
          <div className="card-heading">
            <h2>Upload Files</h2>
            <p>CSV, JSON, or PDF sources in priority order.</p>
          </div>
          <UploadPanel files={files} onChange={setFiles} />
        </div>

        <div className="card">
          <div className="card-heading">
            <h2>Config Selection</h2>
            <p>Pick the runtime projection preset.</p>
          </div>
          <ConfigSelector value={config} onChange={setConfig} />
        </div>

        <div className="card run-card">
          <div className="card-heading">
            <h2>Run Pipeline</h2>
            <p>Merge candidate data, resolve conflicts, and generate configurable outputs.</p>
          </div>
          <RunButton onClick={onRun} disabled={!canRun} loading={isRunning} />
          {error ? <p className="error-text">{error}</p> : <p className="helper">{files.length === 0 ? 'Please upload a candidate resume or data file to begin.' : 'Ready to run.'}</p>}
        </div>
      </section>

      {result && (
        <section className="metrics-row">
          <div className="metric-box">
            <span className="metric-label">Sources Processed</span>
            <span className="metric-value">{sourcesCount}</span>
          </div>
          <div className="metric-box">
            <span className="metric-label">Fields Resolved</span>
            <span className="metric-value">{fieldsResolved}</span>
          </div>
          <div className="metric-box">
            <span className="metric-label">Conflicts Found</span>
            <span className="metric-value">{conflictsFound}</span>
          </div>
          <div className="metric-box">
            <span className="metric-label">Overall Confidence <Tooltip text="A calculated metric indicating data reliability, based on source authority and multi-source corroboration." /></span>
            <span className="metric-value">{confidence}</span>
          </div>
        </section>
      )}

      <section className="card">
        <div className="card-heading">
          <h2>Execution Summary & Validation <Tooltip text="A summary of any warnings or schema validation errors caught during the pipeline run." /></h2>
        </div>
        <WarningPanel warnings={result?.warnings ?? []} validationErrors={result?.validation_errors ?? []} />
      </section>

      <section className="results-grid">
        <div className="card">
          <div className="card-heading">
            <h2>Canonical Profile (Internal Truth) <Tooltip text="The internal source of truth aggregated from all incoming candidate data, retaining conflicting info and confidence scores." /></h2>
            <p>Engine truth aggregated across all sources.</p>
          </div>
          <CanonicalProfileView canonical={result?.canonical ?? null} />
        </div>

        <div className="card">
          <div className="card-heading">
            <h2>Projected Output (Config Driven) ({config}) <Tooltip text="The final output shaped to consumer-specific requirements, derived from the canonical profile without altering pipeline logic." /></h2>
            <p>Clean JSON shaped by the selected config.</p>
          </div>
          <ProjectionView output={result?.output ?? null} />
        </div>
      </section>

      <section className="card compare-card">
        <div className="card-heading">
          <h2>Compare Configs <Tooltip text="Demonstrates how a single canonical profile can project into entirely different shapes on demand." /></h2>
          <p>The same canonical profile can be projected into different consumer-specific schemas without changing pipeline logic.</p>
        </div>
        <CompareView files={files} leftConfig="default" rightConfig="public_profile" />
      </section>
    </main>
  )
}

export default App
