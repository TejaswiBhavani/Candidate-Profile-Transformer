import type { JsonObject } from '../api/types'

interface CanonicalProfileViewProps {
  canonical: JsonObject | null
}

export function CanonicalProfileView({ canonical }: CanonicalProfileViewProps) {
  return (
    <>
      {canonical ? (
        <pre className="json-box">{JSON.stringify(canonical, null, 2)}</pre>
      ) : (
        <p className="help-text">Run the pipeline to generate the canonical profile.</p>
      )}
    </>
  )
}
