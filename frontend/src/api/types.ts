export type JsonValue = string | number | boolean | null | JsonObject | JsonArray
export interface JsonObject {
  [key: string]: JsonValue
}
export type JsonArray = JsonValue[]

export interface PipelineResponse {
  ok: boolean
  warnings: string[]
  validation_errors: string[]
  canonical: JsonObject | null
  output: JsonObject | null
}
