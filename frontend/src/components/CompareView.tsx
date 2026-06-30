import { useMemo, useState } from 'react'
import { runPipeline } from '../api/client'
import type { JsonObject } from '../api/types'

interface CompareViewProps {
  files: File[]
  leftConfig: string
  rightConfig: string
}

const PRESETS = ['default', 'minimal', 'public_profile', 'strict_required']

function onlyInLeft(left: JsonObject | null, right: JsonObject | null): string[] {
  if (!left) {
    return []
  }
  const rightKeys = new Set(Object.keys(right ?? {}))
  return Object.keys(left).filter((k) => !rightKeys.has(k))
}

export function CompareView({ files, leftConfig, rightConfig }: CompareViewProps) {
  const [aConfig, setAConfig] = useState(leftConfig)
  const [bConfig, setBConfig] = useState(rightConfig)
  const [aOut, setAOut] = useState<JsonObject | null>(null)
  const [bOut, setBOut] = useState<JsonObject | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const leftOnly = useMemo(() => onlyInLeft(aOut, bOut), [aOut, bOut])
  const rightOnly = useMemo(() => onlyInLeft(bOut, aOut), [aOut, bOut])

  const onCompare = async () => {
    if (files.length === 0) {
      setError('Upload files first, then compare configs.')
      return
    }

    setLoading(true)
    setError(null)
    try {
      const [aResp, bResp] = await Promise.all([runPipeline(files, aConfig), runPipeline(files, bConfig)])
      setAOut(aResp.output)
      setBOut(bResp.output)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Compare failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <div className="compare-layout">
        <div className="field">
          <label htmlFor="compare-left">Config A</label>
          <select id="compare-left" value={aConfig} onChange={(e) => setAConfig(e.target.value)}>
            {PRESETS.map((preset) => (
              <option key={`a-${preset}`} value={preset}>
                {preset}
              </option>
            ))}
          </select>
        </div>

        <div className="field">
          <label htmlFor="compare-right">Config B</label>
          <select id="compare-right" value={bConfig} onChange={(e) => setBConfig(e.target.value)}>
            {PRESETS.map((preset) => (
              <option key={`b-${preset}`} value={preset}>
                {preset}
              </option>
            ))}
          </select>
        </div>

        <button type="button" className="run-button" onClick={onCompare} disabled={loading}>
          {loading ? 'Comparing...' : 'Compare'}
        </button>
      </div>

      {error ? <p className="error-text">{error}</p> : null}

      <div className="compare-grid">
        <div className="compare-side">
          <h3>Config A: {aConfig}</h3>
          <pre className="json-box">{aOut ? JSON.stringify(aOut, null, 2) : 'Select Config A and click Compare to view.'}</pre>
        </div>
        <div className="compare-side">
          <h3>Config B: {bConfig}</h3>
          <pre className="json-box">{bOut ? JSON.stringify(bOut, null, 2) : 'Select Config B and click Compare to view.'}</pre>
        </div>
      </div>

      {aOut && bOut ? (
        <div className="diff-note-container">
          <p className="diff-note">
            <span className="diff-label">Only in {aConfig}:</span> {leftOnly.length ? leftOnly.join(', ') : 'none'}
          </p>
          <p className="diff-note">
            <span className="diff-label">Only in {bConfig}:</span> {rightOnly.length ? rightOnly.join(', ') : 'none'}
          </p>
        </div>
      ) : null}
    </>
  )
}
