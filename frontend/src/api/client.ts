import type { PipelineResponse } from './types'

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8000'

export async function runPipeline(files: File[], configName: string = 'default'): Promise<PipelineResponse> {
  const formData = new FormData()
  files.forEach((file) => formData.append('files', file))
  formData.append('config_name', configName)

  const resp = await fetch(`${API_BASE}/run`, {
    method: 'POST',
    body: formData,
  })

  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`
    try {
      const body = await resp.json()
      detail = body.detail ?? detail
    } catch {
      // no-op
    }
    throw new Error(`Pipeline request failed: ${detail}`)
  }

  return (await resp.json()) as PipelineResponse
}

export async function fetchWorkflow(): Promise<{ stages: Array<{ id: string; label: string; icon: string; description: string }> }> {
  const resp = await fetch(`${API_BASE}/workflow`)
  return resp.json()
}
