import type { JsonObject } from '../api/types'

interface ProjectionViewProps {
  output: JsonObject | null
}

export function ProjectionView({ output }: ProjectionViewProps) {
  return (
    <>
      {output ? (
        <pre className="json-box">{JSON.stringify(output, null, 2)}</pre>
      ) : (
        <p className="help-text">Run the pipeline to generate projected output.</p>
      )}
    </>
  )
}
