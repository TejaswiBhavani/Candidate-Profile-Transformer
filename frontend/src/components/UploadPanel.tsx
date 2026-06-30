interface UploadPanelProps {
  files: File[]
  onChange: (files: File[]) => void
}

export function UploadPanel({ files, onChange }: UploadPanelProps) {
  return (
    <div className="field">
      <label htmlFor="source-files">Upload Files (.csv, .txt, .json, .pdf)</label>
      <input
        id="source-files"
        type="file"
        multiple
        accept=".csv,.txt,.json,.pdf,application/pdf,text/csv,text/plain,application/json"
        onChange={(e) => onChange(Array.from(e.target.files ?? []))}
      />
      <div className="help-text">Selected sources</div>
      <ul className="file-list">
        {files.length === 0 ? (
          <li><span className="help-text">No files selected. Please upload to begin.</span></li>
        ) : (
          files.map((f) => {
            const name = f.name.toLowerCase();
            let badgeClass = 'unstructured';
            let badgeText = 'Unstructured';
            
            if (name.endsWith('.csv')) {
              badgeClass = 'structured';
              badgeText = 'Structured';
            } else if (name.endsWith('.json')) {
              badgeClass = 'semi-structured';
              badgeText = 'Semi-structured';
            }

            return (
              <li key={f.name}>
                {f.name}
                <span className={`badge ${badgeClass}`}>
                  {badgeText}
                </span>
              </li>
            )
          })
        )}
      </ul>
    </div>
  )
}
