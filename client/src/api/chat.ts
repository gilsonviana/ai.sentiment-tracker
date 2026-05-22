import { apiPost } from './client'

export interface ChatResponse {
  answer: string
  sources_used: number
}

export const askQuestion = (question: string): Promise<ChatResponse> =>
  apiPost('/chat', { question })
