import { useRef, useState } from 'react'
import { Document } from './Icons'

interface DropZoneProps {
  files: File[]
  onChange: (files: File[]) => void
}

const FILE_TYPE_LABELS: Record<string, { label: string; color: string }> = {
  '.csv': { label: 'Structured', color: '#0369a1' },
  '.json': { label: 'Semi-structured', color: '#166534' },
  '.pdf': { label: 'Unstructured', color: '#7e22ce' },
  '.txt': { label: 'Unstructured', color: '#7e22ce' },
}

function getFileExt(name: string) {
  return '.' + name.split('.').pop()?.toLowerCase()
}

export function DropZone({ files, onChange }: DropZoneProps) {
  const [dragOver, setDragOver] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const dropped = Array.from(e.dataTransfer.files)
    onChange([...files, ...dropped])
  }

  const handleSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      onChange([...files, ...Array.from(e.target.files)])
    }
  }

  const removeFile = (idx: number) => {
    onChange(files.filter((_, i) => i !== idx))
  }

  return (
    <div className="dropzone-wrapper">
      <div
         className={`dropzone ${dragOver ? 'dropzone--active' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".csv,.json,.pdf,.txt"
          onChange={handleSelect}
          style={{ display: 'none' }}
        />
        <div className="dropzone-icon" style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
          <Document size={48} />
        </div>
        <p className="dropzone-title">
          {files.length === 0
            ? 'Drop candidate files here'
            : `${files.length} file${files.length > 1 ? 's' : ''} selected`}
        </p>
        <p className="dropzone-subtitle">
          Resume PDF · Recruiter CSV · ATS JSON · Recruiter Notes
        </p>
      </div>

      {files.length > 0 && (
        <ul className="file-chips">
          {files.map((f, i) => {
            const ext = getFileExt(f.name)
            const meta = FILE_TYPE_LABELS[ext] || { label: 'File', color: '#64748b' }
            return (
              <li key={i} className="file-chip">
                <span className="file-chip-name">{f.name}</span>
                <span className="file-chip-badge" style={{ background: meta.color }}>
                  {meta.label}
                </span>
                <button className="file-chip-remove" onClick={(e) => { e.stopPropagation(); removeFile(i) }}>×</button>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
