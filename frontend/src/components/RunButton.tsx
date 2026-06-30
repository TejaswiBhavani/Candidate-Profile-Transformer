interface RunButtonProps {
  onClick: () => void
  disabled: boolean
  loading: boolean
}

export function RunButton({ onClick, disabled, loading }: RunButtonProps) {
  return (
    <button type="button" className="run-button" onClick={onClick} disabled={disabled}>
      {loading ? 'Running...' : 'Run Pipeline'}
    </button>
  )
}
