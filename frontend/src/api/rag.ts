import axios from './axios'

export interface RAGDocument {
  id: number
  user_id: number
  filename: string
  file_type: string
  file_size: number
  storage_path: string
  subject: string
  chunk_count: number
  indexed_at: string | null
  created_at: string | null
}

export interface RAGChatResult {
  answer: string
  source: string | null
  category?: string
  relevant_chunks: Array<{
    content: string
    metadata: {
      filename: string
      chunk_index?: number
      total_chunks?: number
      chunk_size?: number
      subject?: string
    }
    similarity: number
  }>
  from_knowledge_base: boolean
}

export interface KnowledgeStatus {
  document_count: number
  total_chunks: number
  index_size: number
  documents: RAGDocument[]
}

export async function uploadDocument(file: File, subject?: string, onProgress?: (progress: number) => void): Promise<{ success: boolean; message: string }> {
  const formData = new FormData()
  formData.append('file', file)
  if (subject) {
    formData.append('subject', subject)
  }
  return await axios.post('/rag/upload', formData, {
    timeout: 300000,
    onUploadProgress: (progressEvent) => {
      if (onProgress && progressEvent.total) {
        const percent = Math.round((progressEvent.loaded / progressEvent.total) * 100)
        onProgress(percent)
      }
    }
  })
}

export async function getDocuments(subject?: string): Promise<RAGDocument[]> {
  const data: { documents: RAGDocument[] } = await axios.get('/rag/documents', { params: { subject } })
  return data.documents
}

export async function getDocument(id: number): Promise<RAGDocument> {
  return await axios.get(`/rag/documents/${id}`)
}

export function getDocumentDownloadUrl(id: number): string {
  const token = localStorage.getItem('token')
  return `/api/rag/documents/${id}/download?token=${token || ''}`
}

export function getDocumentPreviewUrl(id: number): string {
  const token = localStorage.getItem('token')
  return `/api/rag/documents/${id}/download?token=${token || ''}&preview=true`
}

export async function deleteDocument(id: number): Promise<{ success: boolean; message: string }> {
  return await axios.delete(`/rag/documents/${id}`)
}

export async function indexDocument(id: number): Promise<{ success: boolean; message: string }> {
  return await axios.post(`/rag/documents/${id}/index`)
}

export async function cancelIndexDocument(id: number): Promise<{ success: boolean; message: string }> {
  return await axios.post(`/rag/documents/${id}/index/cancel`)
}

export async function getKnowledgeStatus(): Promise<KnowledgeStatus> {
  return await axios.get('/rag/knowledge/status')
}

export async function ragChat(
  question: string,
  top_k: number = 3,
  threshold: number = 0.3,
  subject?: string,
  onlyKnowledgeBase: boolean = false
): Promise<RAGChatResult> {
  return await axios.post('/rag/chat', {
    question,
    top_k,
    threshold,
    subject,
    only_knowledge_base: onlyKnowledgeBase
  })
}

export async function ragSearch(question: string, top_k: number = 3, threshold: number = 0.3): Promise<{ results: any[] }> {
  return await axios.post('/rag/search', null, {
    params: {
      question,
      top_k,
      threshold
    }
  })
}
