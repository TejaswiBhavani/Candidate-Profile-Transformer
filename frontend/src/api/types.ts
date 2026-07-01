export type JsonValue = string | number | boolean | null | JsonObject | JsonArray
export interface JsonObject {
  [key: string]: JsonValue
}
export type JsonArray = JsonValue[]

export interface SkillEntry {
  name: string
  confidence: number
  sources: string[]
}

export interface ExperienceEntry {
  company: string | null
  title: string | null
  start: string | null
  end: string | null
  summary: string | null
}

export interface ProvenanceEntry {
  field: string
  source: string
  method: string
}

export interface DiscoveredUrls {
  linkedin: string | null
  github: string | null
  portfolio: string | null
}

export interface GeminiInsights {
  recruiter_summary: string
  strengths: string[]
  recommended_roles: string[]
  missing_info: string[]
  concerns: string[]
  completeness_score: number
}

export interface ProfileOutput {
  candidate_id: string
  full_name: string | null
  emails: string[]
  phones: string[]
  location: string | null
  headline: string | null
  years_experience: number | null
  links: JsonObject | null
  education: JsonArray
  skills: SkillEntry[]
  experience: ExperienceEntry[]
  overall_confidence: number
  provenance: ProvenanceEntry[]
}

export interface PipelineResponse {
  ok: boolean
  warnings: string[]
  validation_errors: string[]
  canonical: JsonObject | null
  output: ProfileOutput | null
  candidate_outputs?: CandidateOutput[] | null
  discovered_urls: DiscoveredUrls | null
  enrichment_status: string
  gemini_insights: GeminiInsights | null
}

export interface CandidateOutput {
  source_id: string
  canonical: JsonObject | null
  output: ProfileOutput | null
  warnings: string[]
  validation_errors: string[]
}
