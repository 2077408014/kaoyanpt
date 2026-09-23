import request from './axios'

export interface Resource {
  id: number
  user_id: number
  filename: string
  file_type: string
  file_size: number
  storage_path: string
  indexed: boolean
  upload_date: string
}

export interface ResourceQA {
  answer: string
  source: string | null
}

export async function uploadResource(file: File): Promise<Resource> {
  const formData = new FormData()
  formData.append('file', file)
  return await request.post('/resources/upload', formData)
}

export async function getResources(): Promise<Resource[]> {
  return await request.get('/resources')
}

export async function getResource(id: number): Promise<Resource> {
  return await request.get(`/resources/${id}`)
}

export async function deleteResource(id: number): Promise<void> {
  await request.delete(`/resources/${id}`)
}

export async function searchResources(query: string): Promise<Resource[]> {
  return await request.post('/resources/search', null, { params: { query } })
}

export async function resourceQA(resourceId: number, question: string): Promise<ResourceQA> {
  return await request.post('/resources/qa', null, { params: { resource_id: resourceId, question } })
}