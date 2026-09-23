import request from './axios'

export interface AIMessage {
  id: number
  user_id: number
  message_type: string
  content: string
  source: string | null
  created_at: string
}

export interface AIChatResponse {
  answer: string
  category: string
  suggestions: string[]
}

export interface AICommandResponse {
  action: string
  message: string
}

export async function chat(message: string): Promise<AIChatResponse> {
  return await request.post('/ai/chat', { message })
}

export async function command(cmd: string): Promise<AICommandResponse> {
  return await request.post('/ai/command', { command: cmd })
}

export async function getHistory(limit: number = 20): Promise<AIMessage[]> {
  return await request.get('/ai/history', { params: { limit } })
}

export async function clearHistory(): Promise<void> {
  await request.delete('/ai/history')
}

export interface RecommendQuestion {
  question: string
  answer: string
  analysis: string
}

export interface RecommendResponse {
  questions: RecommendQuestion[]
  raw_response?: string
}

export async function recommendQuestions(data: {
  question_text: string
  subject: string
  knowledge_point: string
}): Promise<RecommendResponse> {
  return await request.post('/ai/recommend', data)
}