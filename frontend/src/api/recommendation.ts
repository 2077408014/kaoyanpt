import request from './axios'

export interface Recommendation {
  id: number
  user_id: number
  subject: string
  knowledge_point: string
  difficulty: string
  question_text: string
  answer: string
  analysis: string
  source: string
  completed: boolean
  result: string | null
  completion_time: string | null
  created_at: string
}

export interface WeakPoint {
  subject: string
  knowledge_point: string
  weak_level: number
  mistake_count: number
  updated_at: string
}

export interface RecommendationReport {
  total_recommendations: number
  completed_recommendations: number
  correct_recommendations: number
  accuracy_rate: number
  weak_points: WeakPoint[]
}

export interface RecommendationComplete {
  result: string
}

export async function analyzeWeakPoints(): Promise<WeakPoint[]> {
  return await request.get('/recommend/analysis')
}

export async function generateRecommendations(count: number = 5, subject?: string): Promise<Recommendation[]> {
  const params = new URLSearchParams()
  params.append('count', count.toString())
  if (subject) {
    params.append('subject', subject)
  }
  return await request.post(`/recommend/generate?${params.toString()}`)
}

export async function getRecommendations(completed?: boolean): Promise<Recommendation[]> {
  return await request.get('/recommend/list', { params: { completed } })
}

export async function completeRecommendation(id: number, result: string): Promise<Recommendation> {
  return await request.post(`/recommend/${id}/complete`, { result })
}

export async function deleteRecommendation(id: number): Promise<{ success: boolean; id: number }> {
  return await request.delete(`/recommend/${id}`)
}

export async function getRecommendationReport(): Promise<RecommendationReport> {
  return await request.get('/recommend/report')
}

export interface AgentInfo {
  name: string
  domain: string
  keywords: string[]
  enabled: boolean
  description?: string
}

export interface CollaborationStats {
  total_collaborations: number
  success_rate: number
  avg_response_time_ms: number
}

export interface CollaborationLog {
  id: number
  request_id: string
  user_id: number
  orchestrator_name: string
  query: string
  total_time_ms: number
  consulted_agent_count: number
  accepted_agent_count: number
  recommendation_count: number
  success: boolean
  error_message: string | null
  created_at: string
}

export async function getAgentStatus(): Promise<{ agents: AgentInfo[] }> {
  return await request.get('/recommend/agents')
}

export async function toggleAgent(agentName: string, enabled: boolean): Promise<{ success: boolean; message: string }> {
  return await request.post(`/recommend/agents/${agentName}/toggle`, { enabled })
}

export async function getCollaborationLogs(limit?: number, offset?: number): Promise<{ logs: CollaborationLog[]; stats: CollaborationStats }> {
  return await request.get('/recommend/logs', { params: { limit, offset } })
}