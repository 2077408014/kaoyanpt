import request from './axios'

export interface AIConfigItem {
  id: number
  name: string
  provider: string
  model: string
  created_at: string
}

export interface AIConfigDetail {
  id: number
  user_id: number
  name: string
  provider: string
  api_key: string
  base_url: string
  model: string
  created_at: string
}

export interface AIConfigCreateData {
  name: string
  provider: string
  api_key: string
  base_url: string
  model: string
}

export interface AIConfigUpdateData {
  name?: string
  provider?: string
  api_key?: string
  base_url?: string
  model?: string
}

export async function listAIConfigs(): Promise<AIConfigItem[]> {
  return await request.get('/ai-configs')
}

export async function getAIConfig(id: number): Promise<AIConfigDetail> {
  return await request.get(`/ai-configs/${id}`)
}

export async function createAIConfig(data: AIConfigCreateData): Promise<AIConfigDetail> {
  return await request.post('/ai-configs', data)
}

export async function updateAIConfig(id: number, data: AIConfigUpdateData): Promise<AIConfigDetail> {
  return await request.put(`/ai-configs/${id}`, data)
}

export async function deleteAIConfig(id: number): Promise<{ success: boolean; id: number }> {
  return await request.delete(`/ai-configs/${id}`)
}

export async function switchAIConfig(configId: number | null): Promise<{ success: boolean; active_ai_config_id: number | null }> {
  return await request.post('/ai-configs/switch', { config_id: configId })
}
