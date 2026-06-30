interface ConfigSelectorProps {
  value: string
  onChange: (value: string) => void
}

const PRESETS = ['default', 'minimal', 'public_profile', 'strict_required']

export function ConfigSelector({ value, onChange }: ConfigSelectorProps) {
  return (
    <div className="field">
      <label htmlFor="config-select">Config</label>
      <select id="config-select" value={value} onChange={(e) => onChange(e.target.value)}>
        {PRESETS.map((preset) => (
          <option key={preset} value={preset}>
            {preset}
          </option>
        ))}
      </select>
    </div>
  )
}
