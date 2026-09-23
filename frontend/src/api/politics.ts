import axios from './axios'

export interface PoliticsRecitation {
  id: number
  user_id: number
  title: string
  category: string
  content: string
  image_path: string | null
  mastery_level: string
  review_count: number
  next_review_date: string | null
  last_review_date: string | null
  created_at: string
  updated_at: string | null
}

export interface RecitationReminder {
  id: number
  user_id: number
  reminder_type: string
  reminder_time: string
  frequency: string
  enabled: number
  created_at: string
  updated_at: string | null
}

export interface RecognizeResponse {
  content: string
  confidence: number
}

export interface UploadResponse {
  image_path: string
  image_url: string
}

export async function getRecitations(params?: {
  category?: string
  mastery_level?: string
}): Promise<PoliticsRecitation[]> {
  return await axios.get('/api/politics', { params })
}

export async function getRecitation(id: number): Promise<PoliticsRecitation> {
  return await axios.get(`/api/politics/${id}`)
}

export async function createRecitation(data: {
  title: string
  category?: string
  content: string
  image_path?: string
}): Promise<PoliticsRecitation> {
  return await axios.post('/api/politics', data)
}

export async function updateRecitation(id: number, data: Partial<{
  title: string
  category: string
  content: string
  image_path: string
  mastery_level: string
}>): Promise<PoliticsRecitation> {
  return await axios.put(`/api/politics/${id}`, data)
}

export async function deleteRecitation(id: number): Promise<void> {
  await axios.delete(`/api/politics/${id}`)
}

export async function reviewRecitation(id: number, result: string): Promise<PoliticsRecitation> {
  return await axios.post(`/api/politics/${id}/review`, { result })
}

export async function uploadPoliticsImage(file: File): Promise<UploadResponse> {
  const formData = new FormData()
  formData.append('file', file)
  return await axios.post('/api/politics/upload', formData)
}

export async function recognizePoliticsImage(imagePath: string): Promise<RecognizeResponse> {
  return await axios.post('/api/politics/recognize', { image_path: imagePath })
}

export async function getReminders(reminderType?: string): Promise<RecitationReminder[]> {
  return await axios.get('/api/politics/reminders', { params: { reminder_type: reminderType } })
}

export async function createReminder(data: {
  reminder_type: string
  reminder_time: string
  frequency: string
}): Promise<RecitationReminder> {
  return await axios.post('/api/politics/reminders', data)
}

export async function updateReminder(id: number, data: Partial<{
  reminder_time: string
  frequency: string
  enabled: number
}>): Promise<RecitationReminder> {
  return await axios.put(`/api/politics/reminders/${id}`, data)
}

export async function deleteReminder(id: number): Promise<void> {
  await axios.delete(`/api/politics/reminders/${id}`)
}
