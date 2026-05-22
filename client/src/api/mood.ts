import { apiGet } from './client'

export interface MoodDataPoint {
  date: string
  score: number
  label: string
}

export interface MoodReport {
  month: string
  entries: MoodDataPoint[]
  avg_mood: number
  entry_count: number
}

export const getMoodReport = (month: string): Promise<MoodReport> =>
  apiGet(`/mood/${month}`)
