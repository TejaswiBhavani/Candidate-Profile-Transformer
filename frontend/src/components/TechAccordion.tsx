import { useState } from 'react'
import type { JsonObject, ProvenanceEntry } from '../api/types'

import { Gear } from './Icons'

interface TechAccordionProps {
  canonical: JsonObject | null
  output: JsonObject | null
  warnings: string[]
  provenance: ProvenanceEntry[]
}

export function TechAccordion({ canonical, output, warnings, provenance }: TechAccordionProps) {
  const [open, setOpen] = useState(false)

  return (
    <div className="tech-accordion">
      <button className="tech-toggle" onClick={() => setOpen(!open)}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
          <Gear size={16} /> View Technical Details
        </span>
        <span className={`tech-arrow ${open ? 'open' : ''}`}>▼</span>
      </button>
      {open && (
        <div className="tech-panels">
          {/* Provenance */}
          <div className="tech-panel">
            <h4>Provenance Trail</h4>
            {provenance.length > 0 ? (
              <table className="prov-table">
                <thead>
                  <tr><th>Field</th><th>Source</th><th>Method</th></tr>
                </thead>
                <tbody>
                  {provenance.map((p, i) => (
                    <tr key={i}>
                      <td>{p.field}</td>
                      <td>{p.source}</td>
                      <td><code>{p.method}</code></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="tech-empty">No provenance data</p>
            )}
          </div>

          {/* Warnings & Conflicts */}
          {warnings.length > 0 && (
            <div className="tech-panel">
              <h4>Warnings & Conflict Resolution</h4>
              <ul className="tech-warn-list">
                {warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Canonical JSON */}
          <div className="tech-panel">
            <h4>Canonical Profile (Internal)</h4>
            <pre className="tech-json">{JSON.stringify(canonical, null, 2)}</pre>
          </div>

          {/* Projected Output JSON */}
          <div className="tech-panel">
            <h4>Projected Output</h4>
            <pre className="tech-json">{JSON.stringify(output, null, 2)}</pre>
          </div>
        </div>
      )}
    </div>
  )
}
