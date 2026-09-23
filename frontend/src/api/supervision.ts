import axios from './axios'

export interface SupervisionCheckRequest {
  image_base64: string
  session_id: string
}

export interface SupervisionCheckResponse {
  status: string
  confidence: number
  face_count: number
  overlay_base64?: string | null
}

export interface SupervisionSessionStart {
  session_id: string
  started_at: string
}

export interface SupervisionSessionStats {
  session_id: string
  total_checks: number
  focused_count: number
  distracted_count: number
  absent_count: number
  unknown_count: number
  focus_rate: number
  duration_seconds: number
}

export interface SupervisionDailyStats {
  date: string
  total_focused_seconds: number
  total_checks: number
  focus_rate: number
}

export async function startSupervisionSession(): Promise<SupervisionSessionStart> {
  return await axios.post('/supervision/session/start')
}

export async function checkSupervision(data: SupervisionCheckRequest): Promise<SupervisionCheckResponse> {
  return await axios.post('/supervision/check', data)
}

export async function getSupervisionSessionStats(sessionId: string): Promise<SupervisionSessionStats> {
  return await axios.get(`/supervision/session/${sessionId}/stats`)
}

export async function getSupervisionDailyStats(date?: string): Promise<SupervisionDailyStats> {
  return await axios.get('/supervision/daily-stats', { params: date ? { target_date: date } : {} })
}
