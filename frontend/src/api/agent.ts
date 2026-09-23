import axios from './axios'

export interface AgentChatRequest {
  agent_name: string
  message: string
  subject?: string
}

export interface AgentMessage {
  id: number
  user_id: number
  agent_name: string
  message_type: string
  content: string
  source: string | null
  created_at: string | null
}

export interface AgentChatResponse {
  answer: string
  source: string | null
  suggestions?: string[]
  from_knowledge_base?: boolean
  relevant_chunks?: any[]
}

export async function agentChat(data: AgentChatRequest): Promise<AgentChatResponse> {
  return await axios.post('/agent/chat', data)
}

export async function getAgentHistory(agent_name: string, limit: number = 50): Promise<AgentMessage[]> {
  return await axios.get('/agent/history', { params: { agent_name, limit } })
}

export async function clearAgentHistory(agent_name: string): Promise<{ message: string }> {
  return await axios.delete('/agent/history', { params: { agent_name } })
}
