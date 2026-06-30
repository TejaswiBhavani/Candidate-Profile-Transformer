interface WarningPanelProps {
  warnings: string[]
  validationErrors: string[]
}

export function WarningPanel({ warnings, validationErrors }: WarningPanelProps) {
  if (warnings.length === 0 && validationErrors.length === 0) {
    return <p className="help-text">Pipeline executed successfully with no conflicts.</p>
  }

  return (
    <ul className="warning-list">
      {warnings.map((w) => (
        <li key={`w-${w}`}>{w}</li>
      ))}
      {validationErrors.map((e) => (
        <li key={`e-${e}`}>{e}</li>
      ))}
    </ul>
  )
}
