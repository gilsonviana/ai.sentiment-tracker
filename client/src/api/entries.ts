import { apiGet, apiPost } from './client'

export interface JournalEntryCreate {
  content: string
  entry_date?: string // YYYY-MM-DD
}

export interface JournalEntry {
  id: string
  content: string
  status: 'pending' | 'processed' | 'failed'
  created_at: string
  entry_date: string
}

export interface Analysis {
  entry_id: string
  vader_score: number
  roberta_score: number
  composite_score: number
  label: 'positive' | 'neutral' | 'negative'
  entities: string[]
  analysed_at: string
}

export const getEntries = (month?: string): Promise<JournalEntry[]> =>
  apiGet(`/entries${month ? `?month=${month}` : ''}`)

export const createEntry = (body: JournalEntryCreate): Promise<JournalEntry> =>
  apiPost('/entries', body)

export const getEntry = (id: string): Promise<JournalEntry> =>
  apiGet(`/entries/${id}`)

export const getAnalysis = (id: string): Promise<Analysis> =>
  apiGet(`/entries/${id}/analysis`)
