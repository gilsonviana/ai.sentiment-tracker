import { apiGet, apiPost } from './client'

export interface ReflectionResponse {
  narrative: string
  entry_count: number
  avg_mood: number
  window_start: string
  window_end: string
}

export interface StoredReflection extends ReflectionResponse {
  id: string
  generated_at: string
}

export const generateReflection = (
  start?: string,
  end?: string,
): Promise<ReflectionResponse> => {
  const params: Record<string, string> = {}
  if (start) params.start = start
  if (end) params.end = end
  return apiPost('/reflect', {}, params)
}

export const listReflections = (): Promise<StoredReflection[]> =>
  apiGet('/reflect')
